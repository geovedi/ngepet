import argparse
import os
import subprocess
import glob
import re
import yaml


def to_base36(num):
    if num == 0:
        return "0"

    base36 = [str(i) for i in range(10)] + [chr(i) for i in range(65, 91)]
    result = ""

    while num > 0:
        num, remainder = divmod(num, 36)
        result = base36[remainder] + result

    return result


def clear_previous_results(config):
    for file in glob.glob(
            f"{config['result_dir']}/strategy_{config['strategy_name']}_*"):
        os.remove(file)

    strategy_param_file = config['strategy_param_file']

    if os.path.exists(strategy_param_file):
        os.remove(strategy_param_file)


def run_freqtrade_command(command_args, config):
    cmd = command_args + [
        "--userdir", config['user_dir'], 
        "--config", config['base_config_file'], 
        "--config", config['strategy_config_file']
    ]
    subprocess.run(cmd)


def run_hyperopt(config, is_first_run=True):
    clear_previous_results(config)
    spaces = ["buy", "sell", "roi", "stoploss", "trades"
              ] if is_first_run else ["trades", "trailing"]
    run_freqtrade_command([
        "freqtrade", "hyperopt",
        "--hyperopt-loss", config['hyperopt_loss'],
        "--strategy", config['strategy_name'], 
        "--fee", str(config['fee']), 
        "--timerange", config['time_range'], 
        "--timeframe", config['time_frame'], 
        "--print-all", 
        "--min-trades", "1", 
        "--epochs", str(config['epoch_count'])
    ] + ["--spaces"] + spaces, config)


def process_hyperopt_results(fname, config):
    csvfile = (
        f"{config['result_dir']}/"
        f"{os.path.basename(fname).replace('.fthypt', '.csv')}"
    )

    # Generate CSV file
    run_freqtrade_command([
        "freqtrade", "hyperopt-list", 
        "--hyperopt-filename", os.path.basename(fname), 
        "--min-total-profit", config['min_total_profit'], 
        "--min-objective", config['min_objective'], 
        "--export-csv", csvfile
    ], config)

    if not os.path.exists(csvfile) or os.path.getsize(csvfile) == 0:
        return 0

    strategy_count = 0
    with open(csvfile, 'r') as file:
        next(file)  # Skip the header row
        for line in file:
            index = line.split(',')[1].strip()
            short_code = to_base36(int(re.sub("[^\d]", "", fname)))
            output_dir = (
                f"{config['user_dir']}/strategies/"
                f"{config['strategy_name']}.{short_code}.{index}"
            )
            print(f"{config['strategy_name']}.{short_code}.{index}")

            run_freqtrade_command([
                "freqtrade", "hyperopt-show", "--hyperopt-filename",
                os.path.basename(fname), "--index", index
            ], config)

            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            strategy_param_file = config['strategy_param_file']
            if os.path.exists(strategy_param_file):
                os.rename(
                    strategy_param_file,
                    os.path.join(output_dir,
                                 os.path.basename(strategy_param_file)))

            strategy_py_file = os.path.join(config['user_dir'], "strategies",
                                            f"{config['strategy_name']}.py")
            if os.path.exists(strategy_py_file):
                subprocess.run(["cp", strategy_py_file, output_dir])

            strategy_count += 1
            if strategy_count >= config['max_strategies']:
                break

    return strategy_count


def main():
    parser = argparse.ArgumentParser(
        description='Freqtrade Strategy Automation Script')
    parser.add_argument('--config',
                        '-c',
                        type=str,
                        required=True,
                        help='Path to the YAML configuration file')
    args = parser.parse_args()

    with open(args.config, 'r') as file:
        config = yaml.safe_load(file)

    strategy_count = 0
    while strategy_count < config['max_strategies']:
        run_hyperopt(config)
        for fname in glob.glob(
                f"{config['result_dir']}/*_{config['strategy_name']}_*.fthypt"
        ):
            if os.path.exists(fname):
                strategy_count += process_hyperopt_results(fname, config)
            if strategy_count >= config['max_strategies']:
                break

    for strat_dir in glob.glob(
            f"{config['user_dir']}/strategies/{config['strategy_name']}.*.*"):
        if os.path.isdir(strat_dir):
            run_hyperopt(config, is_first_run=False)
            run_freqtrade_command([
                "freqtrade", "backtesting", 
                "--strategy", config['strategy_name'], 
                "--strategy-path", strat_dir, 
                "--fee", str(config['fee']), 
                "--timerange", config['time_range'], 
                "--timeframe", config['time_frame'], 
                "--timeframe-detail", config['time_frame_detail']
            ], config)


if __name__ == "__main__":
    main()
