# This code is designed to analyze the performance of various trading strategies.
# It loads Freqtrade backtest results from a specified file, ranks these strategies
# based on a custom score derived from standardized performance metrics, and
# calculates capital allocations to the top strategies using a historical returns-based
# portfolio optimization approach.
#
# Additional riskfolio library is required.
# To install using `conda`: `conda install -c conda-forge riskfolio-lib`

import fire
import numpy as np
import pandas as pd
import rapidjson
import riskfolio as rp
from sklearn.preprocessing import StandardScaler

BACKTEST_METRICS_COLUMNS = [
    "strategy_name",
    "total_trades",
    "profit_mean",
    "profit_median",
    "profit_total",
    "cagr",
    "expectancy_ratio",
    "sortino",
    "sharpe",
    "calmar",
    "profit_factor",
    "max_relative_drawdown",
    "trades_per_day",
    "winrate",
]


def load_backtest_data(input_file_or_dir):
    from pathlib import Path

    fp = Path(input_file_or_dir)

    def load_json(fp):
        with fp.open("r") as fi:
            return rapidjson.load(fi)

    if fp.is_file():
        return load_json(fp)

    elif fp.is_dir():
        strategies = {}
        for fn in fp.glob("*.json"):
            if fn.name.endswith(".meta.json") or fn.name == ".last_result.json":
                continue
            print(f"loading {fn.name}")
            for key, value in load_json(fn)["strategy"].items():
                strategies[key] = value
        return {"strategy": strategies}


def preprocess_data(data):
    df = pd.DataFrame(
        [
            pd.Series(strategy_data, index=BACKTEST_METRICS_COLUMNS)
            for strategy_data in data["strategy"].values()
        ]
    )
    df.set_index("strategy_name", inplace=True)
    df["max_relative_drawdown"] = (
        df["max_relative_drawdown"].max() - df["max_relative_drawdown"]
    )

    scaler = StandardScaler()
    scaled_metrics = scaler.fit_transform(df)
    weights = np.ones(scaled_metrics.shape[1])
    df["score"] = np.dot(scaled_metrics, weights)
    return df.sort_values(by="score", ascending=False)


def calculate_allocations(
    df, backtest_data, num_strategies=10, days=90, capital=10_000, denominator=100
):
    top_strategies = df.iloc[:num_strategies]
    print(top_strategies)
    daily_profits = {
        strat: pd.DataFrame(
            backtest_data["strategy"][strat]["daily_profit"], columns=["date", "profit"]
        ).set_index("date")["profit"]
        for strat in top_strategies.index
    }

    returns = pd.concat(daily_profits, axis=1).cumsum().pct_change().fillna(0)
    portfolio = rp.HCPortfolio(returns=returns.tail(days))
    weights = portfolio.optimization(
        model="HRP",
        codependence="pearson",
        rm="MV",
        rf=0,
        linkage="single",
        max_k=int(np.sqrt(len(returns.columns))),
        leaf_order=True,
    )
    allocation = denominator * (weights * capital // denominator)
    return allocation


def main(
    input_file_or_dir, num_strategies=10, days=90, capital=10_000, denominator=100
):
    backtest_data = load_backtest_data(input_file_or_dir)
    processed_data = preprocess_data(backtest_data)
    allocation = calculate_allocations(
        processed_data, backtest_data, num_strategies, days, capital, denominator
    )
    print(allocation)


if __name__ == "__main__":
    fire.Fire(main)
