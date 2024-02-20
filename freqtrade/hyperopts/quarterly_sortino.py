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
        years = max(1, backtest_days // 365)

        if total_profit_abs < starting_balance * years * MIN_ANNUAL_GROWTH_COEF:
            return MAX_LOSS

        scores = []

        # Generate start dates for each 3-month period within the given date range.
        start_dates = date_range(start=min_date, end=max_date, freq="MS")

        for start_date in start_dates:
            end_date = start_date + DateOffset(months=3)
            # Break the loop if the period exceeds the max_date.
            if end_date > max_date:
                break

            # Filter the results DataFrame for trades within the current period.
            chunk = results[
                (results.open_date >= start_date) & (results.close_date < end_date)
            ]

            if not chunk.empty:
                total_profit_abs = chunk["profit_abs"].sum()
                sortino_ratio = calculate_sortino(
                    chunk, start_date, end_date, starting_balance
                )
                scores.append(sortino_ratio)
                starting_balance += total_profit_abs

        return -np.percentile(scores, MIN_PERCENTILE) if scores else MAX_LOSS
