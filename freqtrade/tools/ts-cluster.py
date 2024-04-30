import itertools
import fire
import pandas as pd
import numpy as np
from pathlib import Path

import warnings
warnings.simplefilter("ignore", UserWarning)

from tslearn.clustering import TimeSeriesKMeans
from tslearn.preprocessing import TimeSeriesScalerMeanVariance



def load_data(pair_list, timeframe):
    dfs = {}

    for pair in pair_list:
        p = pair.replace("/", "_")
        fp = Path("user_data/data/binance") / f"{p}-{timeframe}.feather"
        df = pd.read_feather(fp)
        df["date"] = pd.to_datetime(df["date"], unit="s")
        df = df.set_index(df["date"])
        dfs[pair] = df["close"]

    return pd.concat(dfs, axis=1)


def main(pair_file, timeframe="4h", n_clusters=10, seed=1337):
    pair_list = open(pair_file, "r").read().strip().split()

    df = load_data(pair_list, timeframe)
    df = df.dropna()

    X = TimeSeriesScalerMeanVariance().fit_transform(df.T)

    km = TimeSeriesKMeans(n_clusters=n_clusters, verbose=True, random_state=seed)
    clusters = km.fit_predict(X)

    for key, group in itertools.groupby(
        sorted(zip(clusters, df.columns)), lambda x: x[0]
    ):
        sorted_group = sorted([(pair_list.index(x[1]), x[1]) for x in group])
        print(key, ", ".join(f"({a} {b})" for (a, b) in sorted_group))


if __name__ == "__main__":
    fire.Fire(main)
