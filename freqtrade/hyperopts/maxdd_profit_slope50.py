import numpy as np
from pandas import DataFrame
from freqtrade.optimize.hyperopt import IHyperOptLoss
from freqtrade.data.metrics import calculate_max_drawdown


class MaxDrawdownProfitSlope50Loss(IHyperOptLoss):
    """
    Implements a custom loss function for freqtrade hyperparameter optimization that
    balances total return with risk management by considering the maximum drawdown,
    profit slope, and total profit. It rewards strategies with a positive profit slope
    and penalizes higher drawdowns, aiming to find a parameter set that maximizes
    profit while controlling for risk.
    """

    @staticmethod
    def hyperopt_loss_function(
        results: DataFrame, trade_count: int, config: dict, *args, **kwargs
    ) -> float:
        # Early exit with a high loss score if there are fewer than 50 trades,
        # the strategy is unprofitable, or win ratio is low.
        if trade_count < 50 or results["profit_abs"].sum() < 0:
            return 9999.0

        # Calculate total profit and create a cumulative sum of profits over
        # individual trades.
        profit_total = results["profit_abs"].sum()
        profit_cumsum = results["profit_abs"].cumsum()

        # Generate a linear space to represent the expected linear profit growth
        # for comparison.
        trendline = np.linspace(profit_cumsum.iloc[0], profit_total, trade_count)

        # Compute the slope of the line of best fit to the cumulative profit
        # data points. This slope represents the rate of profit growth over time.
        slope = np.polyfit(trendline, profit_cumsum, 1)[0]

        # Calculate the maximum drawdown, which is a measure of the largest drop
        # from peak to trough in account value.
        try:
            max_drawdown = calculate_max_drawdown(results, value_col="profit_abs")[0]
        except ValueError:
            # Assign a small non-zero value if there's no drawdown to avoid
            # division by zero in score calculation.
            max_drawdown = 1e-5

        # Calculate the win ratio, which is the proportion of winning trades
        # out of total trades.
        win_ratio = (
            results[results["profit_abs"] > 0].shape[0] / trade_count
            if trade_count > 0
            else 0.0
        )
        if win_ratio < 0.1:
            return 9999.0

        # Compute the final score by combining slope, total profit, and maximum
        # drawdown into a single metric. A logarithmic function is applied to
        # trade_count to progressively reward strategies that perform well over
        # more trades. Multiplying by -1 as hyperopt seeks to minimize the loss
        # function, hence a lower score is better.
        return (
            -1.0
            * np.log(trade_count)
            * np.round(slope * (profit_total / max_drawdown), 5)
        )
