import glob
import os
import re
import fire
import pandas as pd
import talib.abstract as ta
import rapidjson
from freqtrade.data.btanalysis import load_backtest_data


def autorename_columns(df):
    tokenizer = lambda x: re.split(r"\W+", x)
    tokens = list(map(tokenizer, df.columns))
    common_tokens = set.intersection(*map(set, tokens))
    unique_tokens = [
        list(filter(lambda x: x not in common_tokens, sublist)) for sublist in tokens
    ]
    new_columns = list(map("-".join, unique_tokens))
    return df.rename(columns=dict(zip(df.columns, new_columns)))


def main(
    capital=5000.0,
    resample_mode="W",
    rsi_period=5,
    ema_period=5,
    user_dir="/home/ubuntu/freqtrade/user_data",
):
    df_list = list()
    for fname in glob.glob(f"{user_dir}/backtest_results/*.json"):
        if fname.endswith(".meta.json"):
            continue

        df = load_backtest_data(fname)
        strategy_name = os.path.basename(fname).split("_")[0]
        df = df[["close_date", "profit_abs"]].rename(
            columns={"close_date": "date", "profit_abs": strategy_name}
        )
        df.set_index("date", inplace=True)
        df_list.append(df)

    df = pd.concat(df_list).resample(resample_mode).sum().cumsum()
    df.drop(df.tail(1).index, inplace=True)
    df = autorename_columns(df)
    df = df[sorted(df.columns)]
    print("\nReturns:")
    print(df.tail(10))

    df_rsi = df.apply(lambda x: ta.RSI(x, timeperiod=rsi_period))
    print("\nReturns (RSI):")
    print(df_rsi.tail(10))

    df_rsi_ema = df_rsi.apply(lambda x: ta.EMA(x, timeperiod=ema_period))
    print("\nReturns (RSI-EMA):")
    print(df_rsi_ema.tail(10))

    z = (df_rsi - df_rsi_ema).clip(0)
    print("\nWeights:")
    print(z.tail(10))

    allocations = capital * z.div(z.abs().sum(axis=1), axis=0)

    print("\nSuggested capital allocations:")
    print(
        rapidjson.dumps(allocations.iloc[-1].round(2).sort_index().to_dict(), indent=2)
    )
    print()


if __name__ == "__main__":
    fire.Fire(main)
