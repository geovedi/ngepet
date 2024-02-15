import numpy as np
from pandas import DataFrame
from freqtrade.optimize.hyperopt import IHyperOptLoss
from sklearn.metrics.pairwise import euclidean_distances

MAX_LOSS = 100000

class StabilityLoss(IHyperOptLoss):

    @staticmethod
    def hyperopt_loss_function(results: DataFrame, trade_count: int,
                               *args, **kwargs) -> float:
        returns = results['profit_ratio'].cumsum().to_numpy().reshape(-1, 1)
        trendline = np.linspace(returns[0], returns[-1], trade_count).reshape(-1, 1)

        distance = euclidean_distances(returns, trendline).diagonal()

        similarity = 1 / (distance + 1)
        stability = np.mean(similarity)

        return MAX_LOSS if returns[-1] <= 0 else -stability
