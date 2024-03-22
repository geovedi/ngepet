import glob
import math
import os
from datetime import datetime, timezone

import fire
import numpy as np
import pandas as pd
from scipy import stats


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


def calculate_expectancy(df):
    returns = df["close"].pct_change()

    winning_trades = returns.loc[returns > 0]
    losing_trades = returns.loc[returns <= 0]
    profit_sum = winning_trades.sum()
    loss_sum = abs(losing_trades.sum())
    nb_win_trades = len(winning_trades)
    nb_loss_trades = len(losing_trades)

    average_win = (profit_sum / nb_win_trades) if nb_win_trades > 0 else 0
    average_loss = (loss_sum / nb_loss_trades) if nb_loss_trades > 0 else 0

    winrate = nb_win_trades / len(returns)
    loserate = nb_loss_trades / len(returns)

    expectancy = (winrate * average_win) - (loserate * average_loss)

    risk_reward_ratio = average_win / average_loss
    expectancy_ratio = ((1 + risk_reward_ratio) * winrate) - 1

    return expectancy_ratio


def main(directory_path, stake_currency="BTC", max_pairs=20, timeframe="1d",
         since="2020-01-01"):
    scores = []

    for filename in glob.glob(
        f"{directory_path}/*{stake_currency}-{timeframe}.feather"
    ):
        pair = os.path.basename(filename).split("-")[0].replace("_", "/")
        df = pd.read_feather(filename)
        if df.iloc[0]["date"] > datetime.strptime(since, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        ):
            continue
        df = df.loc[df["date"] >= since]
        scores.append(
            {
                "pair": pair,
                "sortino": calculate_sortino(df),
                "expectancy_ratio": calculate_expectancy(df),
            }
        )

    score = pd.DataFrame(scores)
    # https://stackoverflow.com/a/23202269
    score = score[np.abs(stats.zscore(score["sortino"])) < 3]
    score = score[np.abs(stats.zscore(score["expectancy_ratio"])) < 3]

    print(
        score.sort_values(by="sortino", ascending=False)
        .reset_index(drop=True)
        .iloc[:max_pairs]
    )
    print()
    print(
        score.sort_values(by="expectancy_ratio", ascending=False)
        .reset_index(drop=True)
        .iloc[:max_pairs]
    )


if __name__ == "__main__":
    fire.Fire(main)
