import numpy as np
from pandas import DataFrame
from freqtrade.optimize.hyperopt import IHyperOptLoss

MAX_LOSS = 100000

class StabilityLoss(IHyperOptLoss):

    @staticmethod
    def hyperopt_loss_function(results: DataFrame, trade_count: int,
                               *args, **kwargs) -> float:
        returns = results['profit_abs'].cumsum()
        trendline = np.linspace(returns.iloc[0], returns.iloc[-1], trade_count)
        similarity = np.corrcoef(returns, trendline)[0, 1]
        stability = similarity ** 2

        return MAX_LOSS if returns.iloc[-1] <= 0 else -stability
