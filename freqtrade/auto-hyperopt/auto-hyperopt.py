import gc
import hashlib
import logging
import os
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import fire
import numpy as np
import pandas as pd
import rapidjson
from freqtrade.commands.optimize_commands import (start_backtesting,
                                                  start_hyperopt)
from freqtrade.loggers import setup_logging_pre
from freqtrade.misc import deep_merge_dicts, safe_value_fallback2
from freqtrade.optimize.hyperopt_tools import (HYPER_PARAMS_FILE_FORMAT,
                                               HyperoptTools,
                                               hyperopt_serializer)
from joblib import Parallel, delayed
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger("freqtrade")

DERIVED_STRATEGY_HEADER = """
from {strategy} import {strategy}

class {derived_strategy}_{idx:05d}({strategy}):
"""

BACKTEST_METRICS_COLUMNS = [
    "total_trades",
    "profit_mean",
    "profit_median",
    "profit_total",
    "cagr",
    "expectancy_ratio",
    "sortino",
    "sharpe",
    "calmar",
    "profit_factor",
    "max_relative_drawdown",
    "trades_per_day",
    "winrate",
]


class AutoHyperopt:
    def __init__(self, config):
        self.config = config
        self.user_data_dir = Path(self.config["user_data_dir"])
        self.hyperopt_results_path = self.user_data_dir / "hyperopt_results"
        self.backtest_results_path = self.user_data_dir / "backtest_results"
        self.strategy_path = self.user_data_dir / "strategies"

    def run(self):
        for pipeline in self.config.get("pipelines", []):
            self._run_pipeline(pipeline)

    def _run_pipeline(self, pipeline):
        pipeline_id = pipeline.get("id")
        pipeline_type = pipeline.get("type")
        method_name = f"_run_{pipeline_type}"
        method = getattr(self, method_name, None)
        if method:
            method(pipeline_id)
        else:
            logger.error(f"Unknown pipeline type: {pipeline_type}")

    def _gc_collect(self):
        collected = gc.collect()
        logger.info(f"Garbage collector: collected {collected} objects.")

    def _has_processed(self, target):
        seen = set([self.config["strategy"]])
        if not target.exists():
            return seen
        with open(target, "r") as file:
            for line in file:
                data = rapidjson.loads(line)
                seen.add(data["results_metrics"]["strategy_name"])
        return seen

    def _batched(self, iterable, n):
        it = iter(iterable)
        for batch in iter(lambda: tuple(islice(it, n)), ()):
            yield batch

    def _adjust_config(self, pipeline_id):
        config = deepcopy(self.config)
        for p in self.config["pipelines"]:
            if p["id"] != pipeline_id:
                continue
            for k, v in p.items():
                config[k] = v
        return config

    def _get_hyperopt_result_path(self, pipeline_id):
        dirpath = self.hyperopt_results_path / self.config["strategy"]
        os.makedirs(dirpath, exist_ok=True)
        return dirpath / f"{pipeline_id}.fthypt"

    def _get_strategy_path(self, pipeline_id):
        last_hyperopt_optimize_id = None
        for pipeline in self.config["pipelines"]:
            if (
                pipeline["type"] == "hyperopt_optimize"
                and pipeline["id"] != pipeline_id
            ):
                last_hyperopt_optimize_id = pipeline["id"]
            elif pipeline["type"] == "backtesting" and pipeline["id"] == pipeline_id:
                pipeline_id = last_hyperopt_optimize_id
                break

        dirpath = self.strategy_path / self.config["strategy"] / pipeline_id
        os.makedirs(dirpath, exist_ok=True)
        return dirpath

    def _count_lines(self, fname):
        try:
            with open(fname, "r") as f:
                return sum(1 for _ in f)
        except:
            return 0

    def _filter_hyperopt_output(self, target, use_latest=True):
        last_result_path = self.hyperopt_results_path / ".last_result.json"
        input_file = self.hyperopt_results_path / (
            rapidjson.load(open(last_result_path, "r"))["latest_hyperopt"]
            if use_latest
            else target
        )
        if not input_file.exists():
            logger.error(f'Input file "{input_file.name}" doesn\'t exist')
            return

        results = self._calculate_scores(input_file, use_latest)
        self._save_selected_strategies(input_file, target, results, use_latest)

    def _calculate_scores(self, input_file, use_latest):
        results = {}
        with input_file.open("r") as f:
            for idx, line in enumerate(f):
                data = rapidjson.loads(line)
                if data["loss"] > 0 or data["total_profit"] < 0:
                    continue
                series = pd.Series(
                    data["results_metrics"], index=BACKTEST_METRICS_COLUMNS
                )
                series["strategy_name"] = f"{idx:05d}"
                results[f"{idx:05d}"] = series

        df = pd.DataFrame(results).T
        df.set_index("strategy_name", inplace=True)
        # inverse drawdown
        df["max_relative_drawdown"] = df["max_relative_drawdown"].max() - df["max_relative_drawdown"]
        scaler = StandardScaler()
        scaled_metrics = scaler.fit_transform(df)
        weights = np.ones(scaled_metrics.shape[1])
        df["score"] = np.dot(scaled_metrics, weights)
        df = df[df["score"] > 0.0].sort_values(by="score", ascending=False)
        if not use_latest:
            df = df.iloc[: self.config["max_generated_strategies"]]
        return df["score"].to_dict()

    def _save_selected_strategies(self, input_file, target, results, use_latest):
        selected = set(results.keys())
        output_file = (
            target.open(mode="a")
            if use_latest
            else tempfile.NamedTemporaryFile(mode="w", delete=False)
        )
        with output_file as f:
            for idx, line in enumerate(input_file.open("r")):
                if f"{idx:05d}" in selected:
                    f.write(line)
        if not use_latest:
            shutil.copy(output_file.name, target)
            os.unlink(output_file.name)
        else:
            input_file.unlink()

    def _get_strategy_params(self, params, strategy):
        final_params = deepcopy(params["params_not_optimized"])
        final_params = deep_merge_dicts(params["params_details"], final_params)
        final_params = {
            "strategy_name": strategy,
            "params": final_params,
            "ft_stratparam_v": 1,
            "export_time": datetime.now(timezone.utc),
        }
        return final_params

    def _params_pretty_print(self, params, space, header, non_optimized={}):
        if space in params or space in non_optimized:
            space_params = HyperoptTools._space_params(params, space, 5)
            no_params = HyperoptTools._space_params(non_optimized, space, 5)
            appendix = ""
            if not space_params and not no_params:
                # No parameters - don't print
                return
            if not space_params:
                # Not optimized parameters - append string
                appendix = NON_OPT_PARAM_APPENDIX

            result = f"\n# {header}\n"
            if space == "stoploss":
                stoploss = safe_value_fallback2(space_params, no_params, space, space)
                result += f"stoploss = {stoploss}{appendix}"
            elif space == "max_open_trades":
                max_open_trades = safe_value_fallback2(
                    space_params, no_params, space, space
                )
                result += f"max_open_trades = {max_open_trades}{appendix}"
            elif space == "roi":
                result = result[:-1] + f"{appendix}\n"
                minimal_roi_result = rapidjson.dumps(
                    {str(k): v for k, v in (space_params or no_params).items()},
                    default=str,
                    indent=4,
                    number_mode=rapidjson.NM_NATIVE,
                )
                result += f"minimal_roi = {minimal_roi_result}"
            elif space == "trailing":
                for k, v in (space_params or no_params).items():
                    result += f"{k} = {v}{appendix}\n"

            else:
                result += f"{space}_params = {HyperoptTools._pprint_dict(space_params, no_params)}"

            result = result.replace("\n", "\n    ")
            return result + "\n"

    def _write_strategy_file(self, params, idx, target_dir, strategy):
        params_text = [
            self._params_pretty_print(
                params["params"], "buy", "Buy hyperspace params:", {}
            ),
            self._params_pretty_print(
                params["params"], "sell", "Sell hyperspace params:", {}
            ),
            self._params_pretty_print(params["params"], "roi", "ROI table:", {}),
            self._params_pretty_print(params["params"], "stoploss", "Stoploss:", {}),
            self._params_pretty_print(
                params["params"], "trailing", "Trailing stop:", {}
            ),
            self._params_pretty_print(
                params["params"], "max_open_trades", "Max Open Trades:", {}
            ),
        ]
        params_text = list(filter(None, params_text))
        derived_strategy = params["strategy_name"]
        outfile = target_dir / f"{derived_strategy}_{idx:05d}.py"
        with outfile.open("w") as f:
            f.write(
                DERIVED_STRATEGY_HEADER.format(
                    idx=idx, strategy=strategy, derived_strategy=derived_strategy
                )
            )
            f.write("\n".join(params_text) + "\n")

    def _touch(self, pipeline_id, create=False):
        lockfile = self.hyperopt_results_path / f".{pipeline_id}_DONE"
        if lockfile.exists():
            logger.info(f"Pipeline {pipeline_id} is skipped.")
            return True
        if create:
            lockfile.touch()
        return False

    def _export_strategy(self, pipeline_id, previous_id):
        for pipeline in self.config["pipelines"]:
            if pipeline["id"] == pipeline_id and pipeline["type"] == "backtesting":
                return

        target_dir = self._get_strategy_path(pipeline_id)
        base_strategy = self.strategy_path / f"{self.config['strategy']}.py"
        shutil.copy(base_strategy, target_dir)

        # Jim's strategies specific
        # for rule_file in self.strategy_path.glob("*.rules"):
        #     shutil.copy(rule_file, target_dir)

        input_file = self._get_hyperopt_result_path(previous_id)

        for idx, line in enumerate(open(input_file, "r")):
            data = rapidjson.loads(line)
            params = self._get_strategy_params(
                data, data["results_metrics"]["strategy_name"]
            )
            self._write_strategy_file(params, idx, target_dir, self.config["strategy"])

    def _run_hyperopt_generate(self, pipeline_id):
        if self._touch(pipeline_id):
            return
        logger.info(
            f"Auto-Hyperopt: Generating strategies - Pipeline ID: {pipeline_id}"
        )
        config = self._adjust_config(pipeline_id)
        output = self._get_hyperopt_result_path(pipeline_id)
        while self._count_lines(output) < self.config["max_generated_candidates"]:
            try:
                start_hyperopt(config)
            except KeyboardInterrupt:
                sys.exit()
            self._filter_hyperopt_output(output)
        self._filter_hyperopt_output(output, use_latest=False)
        self._touch(pipeline_id, create=True)
        self._gc_collect()

    def _run_hyperopt_optimize(self, pipeline_id):
        if self._touch(pipeline_id):
            return

        logger.info(
            f"Auto-Hyperopt: Optimizing strategies - Pipeline ID: {pipeline_id}"
        )
        config = self._adjust_config(pipeline_id)
        self._export_strategy(pipeline_id, config["previous_id"])
        output = self._get_hyperopt_result_path(pipeline_id)
        strategy_path = self._get_strategy_path(pipeline_id)
        seen = self._has_processed(output)

        for strat in sorted(strategy_path.glob("*.py")):
            if strat.stem in seen:
                continue
            try:
                config.update(
                    {
                        "strategy": strat.stem,
                        "strategy_path": strategy_path,
                    }
                )
                logger.info(config)
                start_hyperopt(config)
            except KeyboardInterrupt:
                sys.exit()
            self._filter_hyperopt_output(output)
            self._gc_collect()

        self._filter_hyperopt_output(output, use_latest=True)
        self._touch(pipeline_id, create=True)
        self._gc_collect()

    def _run_backtesting(self, pipeline_id):
        if self._touch(pipeline_id):
            return

        logger.info(
            f"Auto-Hyperopt: Backtesting strategies - Pipeline ID: {pipeline_id}"
        )
        config = self._adjust_config(pipeline_id)
        self._export_strategy(pipeline_id, config["previous_id"])
        strategy_path = self._get_strategy_path(pipeline_id)
        strategies = [
            strat.stem
            for strat in sorted(strategy_path.glob("*.py"))
            if strat.stem != config["strategy"]
        ]
        backtest_results_path = self.backtest_results_path / pipeline_id
        os.makedirs(backtest_results_path, exist_ok=True)

        def bt_wrapper(strat_list):
            fname = (
                hashlib.sha1(" ".join(strat_list).encode()).hexdigest().lower()
                + ".json"
            )
            output_file = backtest_results_path / fname
            config.update(
                {
                    "strategy": None,
                    "strategy_list": strat_list,
                    # "recursive_strategy_search": True,
                    "strategy_path": strategy_path,
                    "exportfilename": output_file,
                }
            )
            try:
                start_backtesting(config)
            except KeyboardInterrupt:
                sys.exit()
            self._gc_collect()

        Parallel(n_jobs=-1)(
            delayed(bt_wrapper)(list(batch))
            for batch in self._batched(strategies, self.config["max_parallel_backtest"])
        )
        self._touch(pipeline_id, create=True)


def main(config_file="config.json"):
    gc.set_threshold(50_000, 500, 1000)
    setup_logging_pre()
    with open(config_file, "r") as f:
        config = rapidjson.load(f)
    try:
        AutoHyperopt(config).run()
    except KeyboardInterrupt:
        sys.exit()


if __name__ == "__main__":
    fire.Fire(main)
