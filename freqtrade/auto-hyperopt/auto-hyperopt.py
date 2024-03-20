import gc
import os
import re
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import fire
import rapidjson
import yaml
from freqtrade.commands import Arguments
from freqtrade.commands.optimize_commands import start_backtesting, start_hyperopt
from freqtrade.misc import deep_merge_dicts, safe_value_fallback2
from freqtrade.optimize.hyperopt_tools import (
    HYPER_PARAMS_FILE_FORMAT,
    HyperoptTools,
    hyperopt_serializer,
)
from joblib import Parallel, delayed

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

class {strategy}_{idx:03d}({strategy}):
"""


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


def filter_hyperopt_output(config, target):
    dirpath = Path(config["userdir"]) / "hyperopt_results"
    latest_hyperopt = (
        dirpath / rapidjson.load(dirpath / ".last_result.json")["latest_hyperopt"]
    )

    with target.open("a") as f:
        for line in Path(latest_hyperopt).open("r"):
            data = rapidjson.loads(line)
            if data["loss"] > 0 or data["total_profit"] < 0:
                continue
            f.write(
                rapidjson.dumps,
                data,
                default=hyperopt_serializer,
                number_mode=HYPER_PARAMS_FILE_FORMAT,
            )
            f.write("\n")

    os.remove(latest_hyperopt)


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
    outfile = target_dir / f"{strategy}_{idx:03d}.py"

    params_text = [
        params_pretty_print(params, "buy", "Buy hyperspace params:"),
        params_pretty_print(params, "sell", "Sell hyperspace params:"),
        params_pretty_print(params, "roi", "ROI table:"),
        params_pretty_print(params, "stoploss", "Stoploss:"),
        params_pretty_print(params, "trailing", "Trailing stop:"),
        params_pretty_print(params, "max_open_trades", "Max Open Trades:"),
    ]
    params_text = filter(None, params_text)

    with outfile.open("w") as f:
        f.write(DERIVED_STRATEGY_HEADER.format(idx=idx, strategy=strategy))
        f.write("\n".join(params_text))
        f.write("\n")


def export_strategy(config, source, target):
    strategy_path = Path(config["userdir"]) / "strategies" / config["strategy"]
    target_dir = dirpath / target

    if not target_dir.exists():
        os.makedirs(target_dir)

    strategy = Path(config["userdir"]) / "strategies" / f"{config['strategy']}.py"
    shutil.copy(strategy, target_dir)

    input_file = get_hyperopt_filepath(config, source)
    for idx, line in enumerate(open(input_file, "r")):
        data = rapidjson.loads(line)
        params = get_strategy_params(data)
        write_strategy_file(params, idx, target_dir, config["strategy"])


def adjust_config(config, step):
    for key, value in config[step].items():
        if key == "spaces":
            config["spaces"] = " ".join(value)
        else:
            config[key] = value
    return config


def run_generate(config):
    config = adjust_config(config, "generate")
    args = get_args(HYPEROPT_ARGS_BASE.format(**config).split())

    output = get_hyperopt_filepath(config, "generate")
    strategy_count = count_lines(output)
    while strategy_count < config["min_generated_strategies"]:
        start_hyperopt(args)
        filter_hyperopt_output(config, output)
        strategy_count = count_lines(output)


def run_finetune(config):
    for n in range(10):
        step = f"finetune_{n}"
        if not step in config:
            continue
        config = adjust_config(config, step)
        args = get_args(HYPEROPT_ARGS_BASE.format(**config).split())
        export_strategy(
            config,
            "generate" if step == 0 else f"finetune_{n - 1}",
            step,
        )
        strategy_path = (
            Path(config["userdir"]) / "strategies" / config["strategy"] / step
        )
        for strat in strategy_path.glob(".py"):
            if strat.stem == config["strategy"]:
                continue
            args["strategy"] = strat.stem
            args["strategy_path"] = strategy_path
            args["recursive_strategy_search"] = True
            start_hyperopt(args)
            output = get_hyperopt_filepath(config, step)
            filter_hyperopt_output(config, output)


def main(autoconfig, generate=False, finetune=False, backtest=False):
    with open(autoconfig, "r") as f:
        autoconfig = yaml.safe_load(f)

    gc.set_threshold(0)

    if generate:
        run_generate(autoconfig)

    if finetune:
        run_finetune(autoconfig)

    if backtest:
        run_backtest(autoconfig)


if __name__ == "__main__":
    fire.Fire(main)
