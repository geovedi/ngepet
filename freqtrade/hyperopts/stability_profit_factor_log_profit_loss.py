import numpy as np
from pandas import DataFrame
from freqtrade.optimize.hyperopt import IHyperOptLoss

class StabilityProfitFactorLogProfitLoss(IHyperOptLoss):

    @staticmethod
    def hyperopt_loss_function(results: DataFrame, trade_count: int,
                               *args, **kwargs) -> float:
        returns = results['profit_abs'].cumsum()
        trendline = np.linspace(returns.iloc[0], returns.iloc[-1], trade_count)
        similarity = np.corrcoef(returns, trendline)[0, 1]
        stability = similarity ** 2

        winning_profit = results.loc[results['profit_abs'] > 0, 'profit_abs'].sum()
        losing_profit = results.loc[results['profit_abs'] < 0, 'profit_abs'].sum()
        profit_factor = winning_profit / abs(losing_profit) if losing_profit else 0.0

        score = stability * profit_factor * np.log(abs(returns.iloc[-1]) + 1e5)
        return np.abs(score) if returns.iloc[-1] <= 0 else -score
