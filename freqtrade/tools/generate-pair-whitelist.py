from pathlib import Path
import numpy as np
import pandas as pd
import fire
import rapidjson


def main(stake_currency, input_config, output_config, data_dir="user_data/data/binance"):
    sharpe = {}
    for fn in Path(data_dir).glob(f"*_{stake_currency}-1d.feather"):
        df = pd.read_feather(fn)
        df.set_index("date", inplace=True)
        sharpe[fn.stem] = df["close"].pct_change().rolling(365).apply(lambda x: x.mean() / x.std() * np.sqrt(365))

    df = pd.DataFrame(sharpe)

    pairs = df[df.columns[(df.describe().T["count"] > 365 * 2) & (df.describe().T["50%"] > 0)]].describe().T.index.to_list()
    pairs = list(map(lambda x: f'{x.split("_")[0]}/{stake_currency}', pairs))

    config = rapidjson.load(open(input_config))
    config["exchange"]["pair_whitelist"] = sorted(pairs)

    with open(output_config, "w") as f:
        f.write(rapidjson.dumps(config, indent=2) + "\n")


if __name__ == '__main__':
    fire.Fire(main)
