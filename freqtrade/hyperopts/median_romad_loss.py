import numpy as np
from datetime import datetime
from pandas import DataFrame, DateOffset, date_range
from freqtrade.optimize.hyperopt import IHyperOptLoss
from freqtrade.data.metrics import calculate_max_drawdown

MAX_LOSS = 100000


class MedianReturnOverMaxDrawdownLoss(IHyperOptLoss):
    @staticmethod
    def hyperopt_loss_function(
        results: DataFrame, min_date: datetime, max_date: datetime, *args, **kwargs
    ) -> float:
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
                total_profit = chunk["profit_abs"].sum()
                try:
                    max_drawdown = calculate_max_drawdown(
                        chunk, value_col="profit_abs"
                    )[0]
                    scores.append(total_profit / max_drawdown)
                except Exception:
                    scores.append(total_profit)

        return -np.median(scores) if scores else MAX_LOSS
