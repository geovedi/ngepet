import os
import glob
import pandas as pd
import talib
import numpy as np

def calculate_counts(series):
    counts = np.zeros_like(series)
    current_count = 1

    for i in range(1, len(series)):
        if series.iloc[i] * series.iloc[i - 1] < 0:
            current_count = 1 if series.iloc[i] > 0 else -1
        else:
            current_count += 1

        counts[i] = current_count

    return counts

def main(directory_path, timeframe, timeperiod, min_val, max_val):
    combined_data = list()

    for filename in glob.glob(f"{directory_path}/*-{timeframe}.feather"):
        df = pd.read_feather(filename)
        df["date"] = pd.to_datetime(df["date"], unit="s")
        pair = os.path.basename(filename).split("-")[0]

        df["ROC"] = talib.ROC(df["close"], timeperiod=timeperiod)
        df["ROC_EMA"] = talib.EMA(df["ROC"], timeperiod=timeperiod)

        df[pair] = df["ROC"] - df["ROC_EMA"]
        df.set_index("date", inplace=True)
        combined_data.append(df[pair])

    combined_data = pd.concat(combined_data, axis=1)
    counts = combined_data.apply(calculate_counts)
    filtered_counts = counts[(counts.abs() >= min_val) & (counts.abs() <= max_val)]
    result = counts.iloc[-1].dropna().sort_values()

    print(result)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Find good pairs to trade based on Rate of Changes"
    )

    parser.add_argument("directory_path", type=str)
    parser.add_argument("--timeframe", type=str, default="1h")
    parser.add_argument("--timeperiod", type=int, default=14)
    parser.add_argument("--min_val", type=int, default=5)
    parser.add_argument("--max_val", type=int, default=10)

    args = parser.parse_args()

    main(args.directory_path, args.timeframe, args.timeperiod, args.min_val, args.max_val)
