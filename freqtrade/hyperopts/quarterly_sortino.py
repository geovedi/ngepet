import math
from datetime import datetime

import numpy as np
from freqtrade.constants import Config
from freqtrade.data.metrics import calculate_sortino
from freqtrade.optimize.hyperopt import IHyperOptLoss
from pandas import DataFrame, DateOffset, date_range

MIN_ANNUAL_GROWTH_COEF = 2.0
MAX_LOSS = 100000
MIN_PERCENTILE = 10
SLIPPAGE_PER_TRADE_RATIO = 0.0005
DAYS_IN_YEAR = 365


class QuarterlySortinoLoss(IHyperOptLoss):
    @staticmethod
    def hyperopt_loss_function(
        results: DataFrame,
        trade_count: int,
        config: Config,
        min_date: datetime,
        max_date: datetime,
        *args,
        **kwargs
    ) -> float:
        if results.empty:
            return MAX_LOSS

        starting_balance = config["dry_run_wallet"]
        total_profit_abs = results["profit_abs"].sum()
        backtest_days = (max_date - min_date).days or 1
        years = max(1, backtest_days // DAYS_IN_YEAR)

        if total_profit_abs < starting_balance * years * MIN_ANNUAL_GROWTH_COEF:
            return MAX_LOSS

        results["profit_ratio_after_slippage"] = (
            results["profit_ratio"] - SLIPPAGE_PER_TRADE_RATIO
        )

        scores = []
        start_dates = date_range(start=min_date, end=max_date, freq="MS")

        for start_date in start_dates:
            end_date = start_date + DateOffset(months=3)
            if end_date > max_date:
                break

            chunk = results[
                (results.open_date >= start_date) & (results.close_date < end_date)
            ]

            if not chunk.empty:
                daily_profit = (
                    trades_in_period.resample("1D", on="close_date")
                    .agg({"profit_ratio_after_slippage": "sum"})
                    .reindex(
                        date_range(
                            start=period_start,
                            end=period_end,
                            freq="1D",
                            normalize=True,
                        ),
                        fill_value=0,
                    )
                )
                negative_returns = (
                    daily_profit[daily_profit < 0]["profit_ratio_after_slippage"] ** 2
                )
                downside_deviation = math.sqrt(
                    negative_returns.sum() / len(negative_returns)
                )

                # In finance, the Sortino ratio is typically annualized by multiplying
                # the ratio by the square root of the number of periods in a year.
                # For quarterly data, there are 4 quarters in a year, so the annualization
                # factor would be math.sqrt(4) or simply 2. This is because the Sortino ratio,
                # like the Sharpe ratio, involves volatility or risk measures that scale with
                # the square root of time due to the properties of Brownian motion
                # (underlying many financial models).

                if downside_deviation > 0:
                    average_returns = daily_profit["profit_ratio_after_slippage"].mean()
                    sortino_ratio = average_returns / downside_deviation * 2
                else:
                    sortino_ratio = -100.0

                scores.append(sortino_ratio)

        return -np.percentile(scores, MIN_PERCENTILE) if scores else MAX_LOSS
