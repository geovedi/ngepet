from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import fire
import rapidjson
from freqtrade.misc import deep_merge_dicts, safe_value_fallback2
from freqtrade.optimize.hyperopt_tools import HyperoptTools


def _params_pretty_print(params, space: str, header: str, non_optimized={}) -> None:
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
            # Buy / sell parameters

            result += f"{space}_params = {HyperoptTools._pprint_dict(space_params, no_params)}"

        result = result.replace("\n", "\n    ")
        return result


def get_strategy_config(params, strategy_name):
    final_params = deepcopy(params["params_not_optimized"])
    final_params = deep_merge_dicts(params["params_details"], final_params)
    final_params = {
        "strategy_name": strategy_name,
        "params": final_params,
        "ft_stratparam_v": 1,
        "export_time": datetime.now(timezone.utc),
    }
    return final_params


HEADER = """
from {strategy_name} import {strategy_name}

class {strategy_name}_{idx:03d}({strategy_name}):
"""


def write_file(params, idx, output_dir, strategy_name):
    output_dir_path = Path(output_dir)
    outfile = output_dir_path / f"{strategy_name}_{idx:03d}.py"

    params_text = [
        _params_pretty_print(params, "buy", "Buy hyperspace params:", {}),
        _params_pretty_print(params, "sell", "Sell hyperspace params:", {}),
        _params_pretty_print(params, "roi", "ROI table:", {}),
        _params_pretty_print(params, "stoploss", "Stoploss:", {}),
        _params_pretty_print(params, "trailing", "Trailing stop:", {}),
        _params_pretty_print(params, "max_open_trades", "Max Open Trades:", {}),
    ]
    params_text = filter(None, params_text)

    with outfile.open("w") as f:
        f.write(HEADER.format(idx=idx, strategy_name=strategy_name))
        f.write("\n".join(params_text))


def main(input_file, output_dir, strategy_name="Evolver"):
    for idx, line in enumerate(open(input_file, "r")):
        config = rapidjson.loads(line)
        params = get_strategy_config(config, strategy_name)
        write_file(params["params"], idx, output_dir, strategy_name)


if __name__ == "__main__":
    fire.Fire(main)
