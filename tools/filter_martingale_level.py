import fire
import re
import os
import pandas as pd
import numpy as np
from glob import glob


def main(input_dir, limit=3):
    for fn in glob(f'{input_dir}/*.csv'):
        df = process(fn, limit)
        os.rename(fn, f'{fn}.bak')
        df.to_csv(fn, header=True, index=False, sep=";")
        print(fn)


def process(fn, limit):
    df = pd.read_csv(fn, sep=";")
    sign = df["ProfitLoss"].apply(np.sign)
    x = sign.groupby((sign != sign.shift(1)).cumsum()).cumcount()
    return df[x >= limit]

if __name__ == '__main__':
    fire.Fire(main)
