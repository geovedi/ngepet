import numpy as np
from pandas import DataFrame
from freqtrade.optimize.hyperopt import IHyperOptLoss
from freqtrade.data.metrics import calculate_max_drawdown

class MaxDrawdownProfitSlope50Loss(IHyperOptLoss):
    """
    This class implements a custom loss function which takes into account the maximum drawdown,
    the slope of cumulative profit, and total profit. It's designed for the freqtrade framework
    to be used in hyperparameter optimization. The slope is compared with the trendline of expected
    linear growth from the initial cumulative profit to the total profit over the number of trades.
    """

    @staticmethod
    def hyperopt_loss_function(results: DataFrame, trade_count: int, config: dict, *args, **kwargs) -> float:
        # Check if basic conditions are not met and return a high loss score
        if trade_count < 50 or results['profit_abs'].sum() < 0:
            return 9999.0

        # Calculate the total profit and cumulative profit over trades
        profit_total = results['profit_abs'].sum()
        profit_cumsum = results['profit_abs'].cumsum()

        # Create a trendline representing the expected profit growth
        trendline = np.linspace(profit_cumsum.iloc[0], profit_total, trade_count)
        
        # Calculate the slope of the profit growth; the first element of the output is the slope
        slope = np.polyfit(trendline, profit_cumsum, 1)[0]

        # Calculate maximum drawdown, with a fallback value in case of no losing trades
        try:
            max_drawdown = calculate_max_drawdown(results, value_col='profit_abs')[0]
        except ValueError:
            max_drawdown = 1e-5  # A small number instead of zero to prevent division by zero

        # Calculate win ratio only if it's needed for the condition check
        win_ratio = results[results['profit_abs'] > 0].shape[0] / trade_count if trade_count > 0 else 0.0
        if win_ratio < 0.1:
            return 9999.0

        # Return the negative product of the slope and the ratio of total profit to maximum drawdown
        # This makes the score lower (better) for higher slope and profit-to-drawdown ratio
        return -1.0 * np.round(slope * (profit_total / max_drawdown), 5)
