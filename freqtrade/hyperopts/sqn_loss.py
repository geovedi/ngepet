import numpy as np
from pandas import DataFrame
from freqtrade.optimize.hyperopt import IHyperOptLoss

class SQNLoss(IHyperOptLoss):

    @staticmethod
    def hyperopt_loss_function(results: DataFrame, trade_count: int,
                               *args, **kwargs) -> float:
        mean = results['profit_abs'].mean()
        std = results['profit_abs'].std()
        sqn = (mean / std) * np.sqrt(trade_count)
        return 9999.0 if mean <= 0 else -sqn
