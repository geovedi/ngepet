import argparse
import os
import subprocess
import glob
import re
import yaml
import shutil


def to_base36(num):
    if num < 0:
        raise ValueError("Number must be non-negative")

    if num == 0:
        return "0"

    base36_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    result = ""

    while num > 0:
        num, remainder = divmod(num, 36)
        result = base36_chars[remainder] + result

    return result


def clear_previous_results(config):
    for file in glob.glob(
        f"{config['result_dir']}/strategy_{config['strategy_name']}_*"
    ):
        os.remove(file)

    strategy_param_file = config["strategy_param_file"]

    if os.path.exists(strategy_param_file):
        os.remove(strategy_param_file)


def run_freqtrade_command(command_args, config):
    cmd = command_args + [
        "--userdir", config["user_dir"],
        "--config", config["base_config_file"],
        "--config", config["strategy_config_file"],
    ]

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        import sys

        sys.exit()


def run_hyperopt(config, is_first_run=True, strategy_path=None):
    clear_previous_results(config)

    spaces = ["trades", "trailing"]
    if is_first_run:
        spaces = ["buy", "sell", "roi", "stoploss", "trades"]

    epochs = "100"
    if is_first_run:
        epochs = str(config["epoch_count"])

    cmd = build_command(config, epochs, spaces, is_first_run, strategy_path)
    run_freqtrade_command(cmd, config)


def build_command(config, epochs, spaces, is_first_run, strategy_path):
    cmd = [
        "freqtrade", "hyperopt",
        "--hyperopt-loss", config["hyperopt_loss"],
        "--strategy", config["strategy_name"],
        "--fee", str(config["fee"]),
        "--timerange", config["time_range"],
        "--timeframe", config["time_frame"],
        "--print-all",
        "--min-trades", "1",
        "--epochs", epochs,
        "--spaces", *spaces,
    ]

    if not is_first_run:
        cmd.extend(["--timeframe-detail", config["time_frame_detail"]])

    if strategy_path:
        cmd.extend(["--strategy-path", strategy_path])

    return cmd


def process_hyperopt_results(fname, config):
    csvfile = generate_csv_filename(fname, config)
    generate_csv_file(fname, csvfile, config)

    if is_csv_empty(csvfile):
        return 0

    return process_csv_file(csvfile, fname, config)


def generate_csv_filename(fname, config):
    return (
        f"{config['result_dir']}/{os.path.basename(fname).replace('.fthypt', '.csv')}"
    )


def generate_csv_file(fname, csvfile, config):
    run_freqtrade_command(
        [
            "freqtrade", "hyperopt-list",
            "--hyperopt-filename", os.path.basename(fname),
            "--min-total-profit", str(config["min_total_profit"]),
            "--min-objective", str(config["min_objective"]),
            "--export-csv", csvfile,
        ],
        config,
    )


def is_csv_empty(csvfile):
    return not os.path.exists(csvfile) or os.path.getsize(csvfile) == 0


def process_csv_file(csvfile, fname, config):
    strategy_count = 0
    with open(csvfile, "r") as file:
        next(file)  # Skip the header row
        for line in file:
            strategy_count = process_csv_line(line, fname, config, strategy_count)
            if strategy_count >= config["max_strategies"]:
                break
    return strategy_count


def process_csv_line(line, fname, config, strategy_count):
    index = line.split(",")[1].strip()
    short_code = to_base36(int(re.sub("[^\d]", "", fname)))
    output_dirname = f"{config['strategy_name']}.{short_code}.{int(index):03d}"
    output_dir = f"{config['user_dir']}/strategies/{output_dirname}"
    print(f"Preparing new configuration: {output_dirname}")

    run_freqtrade_command(
        [
            "freqtrade", "hyperopt-show",
            "--hyperopt-filename", os.path.basename(fname),
            "--index", index,
        ],
        config,
    )

    create_strategy_directory(output_dir)
    copy_strategy_files(config, output_dir)

    return strategy_count + 1


def create_strategy_directory(output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)


def copy_strategy_files(config, output_dir):
    copy_file(config["strategy_param_file"], output_dir)
    copy_file(
        os.path.join(config["user_dir"], "strategies", f"{config['strategy_name']}.py"),
        output_dir,
    )


def copy_file(input_file, output_dir):
    if os.path.exists(input_file):
        shutil.copy(input_file, os.path.join(output_dir, os.path.basename(input_file)))


def main():
    parser = argparse.ArgumentParser(description="Freqtrade Strategy Automation Script")
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        required=True,
        help="Path to the YAML configuration file",
    )
    parser.add_argument(
        "--skip-generate",
        action="store_true",
        help="Skip the candidate generation step",
    )
    parser.add_argument(
        "--skip-fine-tune",
        action="store_true",
        help="Skip the fine-tuning step",
    )
    parser.add_argument(
        "--skip-backtest",
        action="store_true",
        help="Skip the backtesting step",
    )
    args = parser.parse_args()

    with open(args.config, "r") as file:
        config = yaml.safe_load(file)

    strategy_dirs = glob.glob(
        f"{config['user_dir']}/strategies/{config['strategy_name']}.*.*"
    )
    strategy_count = len(strategy_dirs)

    if not args.skip_generate:
        while strategy_count < config["max_strategies"]:
            # Generate candidates
            run_hyperopt(config)
            for fname in glob.glob(
                f"{config['result_dir']}/*_{config['strategy_name']}_*.fthypt"
            ):
                if os.path.exists(fname):
                    strategy_count += process_hyperopt_results(fname, config)
                if strategy_count >= config["max_strategies"]:
                    break

    for strat_dir in strategy_dirs:
        if os.path.isdir(strat_dir):
            if not args.skip_fine_tune:
                # Fine-tune candidate
                run_hyperopt(config, is_first_run=False, strategy_path=strat_dir)

            if not args.skip_backtest:
                # Backtesting candidate
                run_freqtrade_command(
                    [
                        "freqtrade", "backtesting",
                        "--strategy", config["strategy_name"],
                        "--strategy-path", strat_dir,
                        "--fee", str(config["fee"]),
                        "--timerange", config["time_range"],
                        "--timeframe", config["time_frame"],
                        "--timeframe-detail", config["time_frame_detail"],
                    ],
                    config,
                )


if __name__ == "__main__":
    main()
