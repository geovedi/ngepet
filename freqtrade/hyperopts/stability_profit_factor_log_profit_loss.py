import numpy as np
from pandas import DataFrame
from freqtrade.optimize.hyperopt import IHyperOptLoss
from freqtrade.constants import Config

class StabilityProfitFactorLogProfitLoss(IHyperOptLoss):

    @staticmethod
    def hyperopt_loss_function(results: DataFrame, trade_count: int, config: Config,
                               *args, **kwargs) -> float:
        starting_balance = config["dry_run_wallet"]
        cumulative_profit = results['profit_abs'].cumsum()
        net_profit = cumulative_profit.iloc[-1]

        trendline = np.linspace(0.0, net_profit, trade_count)
        stability = np.square(np.corrcoef(cumulative_profit, trendline)[0, 1])

        winning_profit = results[results['profit_abs'] > 0]['profit_abs'].sum()
        losing_profit = results[results['profit_abs'] < 0]['profit_abs'].sum()
        profit_factor = winning_profit / abs(losing_profit) if losing_profit else 0.0

        score = stability * profit_factor * np.log(abs(net_profit) + 1e5)
        score = -np.abs(score) if net_profit > 0 else np.abs(score)
        adjustment_factor = 2 if net_profit < 0 else 0.5
        score *= adjustment_factor if net_profit < starting_balance else 1

        return score
