import glob
import math
import os

import fire
import numpy as np
import pandas as pd


def calculate_sortino(df):
    total_profit = df["close"].pct_change()
    expected_returns_mean = total_profit.mean()
    df["downside_returns"] = 0.0
    df.loc[total_profit < 0, "downside_returns"] = total_profit
    total_downside = df["downside_returns"]
    down_stdev = math.sqrt((total_downside**2).sum() / len(total_downside))
    if down_stdev != 0:
        return expected_returns_mean / down_stdev * math.sqrt(365)
    else:
        return -100


def main(directory_path, stake_currency="BTC", timeframe="1d", since="2020-01-01"):
    sortino_ratio = {}

    for filename in glob.glob(
        f"{directory_path}/*{stake_currency}-{timeframe}.feather"
    ):
        pair = os.path.basename(filename).split("-")[0].replace("_", "/")
        df = pd.read_feather(filename)
        df = df.loc[df["date"] >= since]
        sortino_ratio[pair] = calculate_sortino(df)

    sortino_ratio = pd.Series(sortino_ratio)
    m = sortino_ratio.mean()

    print(sortino_ratio[(sortino_ratio > m)].sort_values(ascending=False))


if __name__ == "__main__":
    fire.Fire(main)
