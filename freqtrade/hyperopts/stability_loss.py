import numpy as np
from pandas import DataFrame
from freqtrade.optimize.hyperopt import IHyperOptLoss
from sklearn.metrics.pairwise import euclidean_distances
from datetime import datetime

MAX_LOSS = 100000

class StabilityLoss(IHyperOptLoss):

    @staticmethod
    def hyperopt_loss_function(results: DataFrame, trade_count: int,
                               min_date: datetime, max_date: datetime,
                               *args, **kwargs) -> float:
        resample_freq = '1D'
        slippage_per_trade_ratio = 0.0005

        results['profit_ratio_after_slippage'] = results['profit_ratio'] - slippage_per_trade_ratio
        t_index = date_range(start=min_date, end=max_date, freq=resample_freq, normalize=True)
        sum_daily = results.resample(resample_freq, on='close_date').agg(
            {"profit_ratio_after_slippage": 'sum'}
        ).reindex(t_index).fillna(0)

        returns = sum_daily['profit_ratio_after_slippage'].cumsum().to_numpy().reshape(-1, 1)
        trendline = np.linspace(returns[0], returns[-1], len(returns)).reshape(-1, 1)

        distance = euclidean_distances(returns, trendline).diagonal()
        similarity = 1 / (distance + 1)
        stability = np.mean(similarity)

        return MAX_LOSS if returns[-1] <= 0 else -stability

