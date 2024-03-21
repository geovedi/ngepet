import gc
import hashlib
import logging
import os
import re
import shutil
import sys
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from itertools import islice
from pathlib import Path

import fire
import numpy as np
import pandas as pd
import rapidjson
import yaml
from freqtrade.commands import Arguments
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

BACKTEST_ARGS = """
backtesting 
    --userdir {userdir}
    --config {config}
    --strategy {strategy}
    --timeframe {timeframe}
    --timeframe-detail {timeframe_detail}
    --timerange {timerange}
    --max-open-trades {max_open_trades}
    --dry-run-wallet {dry_run_wallet}
"""

HYPEROPT_ARGS_BASE = """
hyperopt
    --userdir {userdir}
    --config {config}
    --strategy {strategy}
    --timeframe {timeframe}
    --timerange {timerange}
    --max-open-trades {max_open_trades}
    --dry-run-wallet {dry_run_wallet}
    --hyperopt-loss {hyperopt_loss}
    --min-trades {min_trades}
    --job-workers {job_workers}
    --epochs {epochs}
    --spaces {spaces}
    --print-all
    --disable-param-export
"""

DERIVED_STRATEGY_HEADER = """
from {strategy} import {strategy}

class {derived_strategy}_{idx:03d}({strategy}):
"""

BACKTEST_METRICS_COLUMNS = [
    "strategy_name",
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


def get_args(args):
    return Arguments(args).get_parsed_arg()


def count_lines(fname):
    try:
        with open(fname, "r") as f:
            return sum(1 for line in f)
    except:
        return 0


def get_hyperopt_filepath(config, step):
    dirpath = Path(config["userdir"]) / "hyperopt_results"
    return dirpath / f"{config['strategy']}_{step}.fthypt"


def filter_hyperopt_output(config, target, use_latest=True):
    dirpath = Path(config["userdir"]) / "hyperopt_results"
    if use_latest:
        last_result_path = dirpath / ".last_result.json"
        with last_result_path.open("r") as file:
            input_file = dirpath / rapidjson.load(file)["latest_hyperopt"]
    else:
        input_file = target  # for filtering the output

    if not input_file.exists():
        print(f'input_file "{input_file.name}" doesn\'t exist')
        return

    # Scoring
    results = {}
    with input_file.open("r") as f:
        for idx, line in enumerate(f):
            data = rapidjson.loads(line)
            if data["loss"] > 0 or data["total_profit"] < 0:
                continue
            series = pd.Series(data["results_metrics"], index=BACKTEST_METRICS_COLUMNS)
            series["strategy_name"] = f"{idx:05d}"
            results[f"{idx:05d}"] = series
    df = pd.DataFrame(results).T
    df.set_index("strategy_name", inplace=True)

    # Scale metrics and calculate scores
    scaler = StandardScaler()
    scaled_metrics = scaler.fit_transform(df)
    weights = np.ones(scaled_metrics.shape[1])
    df["score"] = np.dot(scaled_metrics, weights)

    df = df[df["score"] > 0.0].sort_values(by="score", ascending=False)
    if not use_latest:
        df = df.iloc[: config["max_generated_strategies"]]
    selected = set(df.index.to_list())

    output_file = (
        target.open(mode="a")
        if use_latest
        else tempfile.NamedTemporaryFile(mode="w", delete=False)
    )
    with output_file as f:
        for idx, line in enumerate(input_file.open("r")):
            if not f"{idx:05d}" in selected:
                continue
            data = rapidjson.loads(line)
            f.write(
                rapidjson.dumps(
                    data,
                    default=hyperopt_serializer,
                    number_mode=HYPER_PARAMS_FILE_FORMAT,
                )
                + "\n"
            )

    if use_latest:
        input_file.unlink()
    else:
        shutil.copy(output_file.name, target)
    gc_collect()


def get_strategy_params(params, strategy):
    final_params = deepcopy(params["params_not_optimized"])
    final_params = deep_merge_dicts(params["params_details"], final_params)
    final_params = {
        "strategy_name": strategy,
        "params": final_params,
        "ft_stratparam_v": 1,
        "export_time": datetime.now(timezone.utc),
    }
    return final_params


def params_pretty_print(params, space, header, non_optimized={}):
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
        return result


def write_strategy_file(params, idx, target_dir, strategy):
    params_text = [
        params_pretty_print(params["params"], "buy", "Buy hyperspace params:", {}),
        params_pretty_print(params["params"], "sell", "Sell hyperspace params:", {}),
        params_pretty_print(params["params"], "roi", "ROI table:", {}),
        params_pretty_print(params["params"], "stoploss", "Stoploss:", {}),
        params_pretty_print(params["params"], "trailing", "Trailing stop:", {}),
        params_pretty_print(
            params["params"], "max_open_trades", "Max Open Trades:", {}
        ),
    ]
    params_text = list(filter(None, params_text))
    derived_strategy = params["strategy_name"]
    outfile = target_dir / f"{derived_strategy}_{idx:03d}.py"
    with outfile.open("w") as f:
        f.write(
            DERIVED_STRATEGY_HEADER.format(
                idx=idx,
                strategy=strategy,
                derived_strategy=derived_strategy,
            )
        )
        f.write("\n".join(params_text))
        f.write("\n")


def export_strategy(config, source, target):
    strategy_path = Path(config["userdir"]) / "strategies" / config["strategy"]
    target_dir = strategy_path / target

    if not target_dir.exists():
        os.makedirs(target_dir)

    strategy = Path(config["userdir"]) / "strategies" / f"{config['strategy']}.py"
    shutil.copy(strategy, target_dir)

    input_file = get_hyperopt_filepath(config, source)
    for idx, line in enumerate(open(input_file, "r")):
        data = rapidjson.loads(line)
        strat_name = data["results_metrics"]["strategy_name"]
        params = get_strategy_params(data, strat_name)
        write_strategy_file(params, idx, target_dir, config["strategy"])


def has_processed(config, target):
    seen = set()
    if not target.exists():
        return seen
    for line in open(target, "r"):
        data = rapidjson.loads(line)
        seen.add(data["results_metrics"]["strategy_name"])
    return seen


def adjust_config(config, step):
    for key, value in config[step].items():
        if key == "spaces":
            config["spaces"] = " ".join(value)
        else:
            config[key] = value
    return config


def batched(iterable, n):
    if n < 1:
        raise ValueError("n must be at least one")
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch


def gc_collect():
    collected = gc.collect()  # or gc.collect(2)
    logger.info("Garbage collector: collected %d objects." % (collected))


def delete_tickerdata(config):
    dirpath = Path(config["userdir"]) / "hyperopt_results"
    f = dirpath / "hyperopt_tickerdata.pkl"
    if f.exists():
        f.unlink()


def run_generate(config):
    logger.info(f"Auto-Hyperopt: Generating strategies")
    config = adjust_config(config, "generate")
    args = get_args(HYPEROPT_ARGS_BASE.format(**config).split())

    output = get_hyperopt_filepath(config, "generate")
    strategy_count = count_lines(output)
    while strategy_count < config["max_generated_strategies"]:
        delete_tickerdata(config) # HACK
        start_hyperopt(args)
        filter_hyperopt_output(config, output)
        filter_hyperopt_output(config, output, use_latest=False)
        strategy_count = count_lines(output)


def run_finetune(config):
    steps = sorted([k for k in config.keys() if k.startswith("finetune_")])
    for n, step in enumerate(steps):
        logger.info(f"Auto-Hyperopt: Finetuning strategies. Step: {step}")
        config = adjust_config(config, step)
        args = get_args(HYPEROPT_ARGS_BASE.format(**config).split())
        export_strategy(
            config,
            "generate" if n == 0 else f"{steps[n-1]}",
            step,
        )
        strategy_path = (
            Path(config["userdir"]) / "strategies" / config["strategy"] / step
        )
        output = get_hyperopt_filepath(config, step)
        seen = has_processed(config, output)
        for strat in sorted(strategy_path.glob("*.py")):
            if strat.stem == config["strategy"] or strat.stem in seen:
                continue
            logger.info(f"Auto-Hyperopt Finetuning strategy: {strat.stem}. Step: {step}")
            args["strategy"] = strat.stem
            args["strategy_path"] = strategy_path
            args["recursive_strategy_search"] = True
            delete_tickerdata(config) # HACK
            start_hyperopt(args)
            filter_hyperopt_output(config, output)
        filter_hyperopt_output(config, output, use_latest=False)


def run_backtest(config):
    logger.info(f"Auto-Hyperopt: Backtesting strategies")
    steps = sorted([k for k in config.keys() if k.startswith("finetune_")])
    last_step = steps[-1]
    export_strategy(config, last_step, "backtest")
    strategy_path = (
        Path(config["userdir"]) / "strategies" / config["strategy"] / "backtest"
    )
    strategies = [strat.stem for strat in sorted(strategy_path.glob(".py"))]

    config = adjust_config(config, step)
    args = get_args(HYPEROPT_ARGS_BASE.format(**config).split())
    args["strategy"] = None
    args["strategy_path"] = strategy_path
    args["recursive_strategy_search"] = True
    args["strategy_list"] = strategies

    def bt_wrapper(strat_list):
        # HACK
        digest = hashlib.sha1()
        digest.update(" ".join(strat_list).encode())
        fname = digest.hexdigest().lower() + ".json"
        output_file = Path(config["userdir"]) / "backtest_results" / fname
        args["strategy_list"] = strat_list
        args["exportfilename"] = output_file
        start_backtesting(args)
        gc_collect()

    start_backtesting(args)
    _ = Parallel(n_jobs=-1)(
        delayed(bt_wrapper)(f)
        for f in batched(strategies, config["max_parallel_backtest"])
    )


def main(config, generate=False, finetune=False, backtest=False):
    setup_logging_pre()
    with open(config, "r") as f:
        config = yaml.safe_load(f)

    gc.set_threshold(50_000, 500, 1000)

    if generate:
        run_generate(config)

    if finetune:
        run_finetune(config)

    if backtest:
        run_backtest(config)


if __name__ == "__main__":
    fire.Fire(main)
