import numpy as np
from pandas import DataFrame
from freqtrade.optimize.hyperopt import IHyperOptLoss

MAX_LOSS = 100000  # Define a maximum loss value to penalize poorly performing strategies.

class SlopeLoss(IHyperOptLoss):
    """
    A custom loss function class that evaluates the performance of a trading strategy
    by calculating the slope of the equity curve's linear regression line.

    This loss function aims to favor strategies with a consistently upward-trending equity curve,
    indicating steady profits over time. Strategies resulting in a downward-trending equity curve,
    suggesting consistent losses, are penalized with a high loss value.

    The final loss is the negative slope of the equity curve. A steeper positive slope (indicating
    strong, consistent performance) results in a lower (more negative) loss value, which is preferred
    during hyperparameter optimization.
    """

    @staticmethod
    def hyperopt_loss_function(results: DataFrame, trade_count: int,
                               *args, **kwargs) -> float:
        """
        Calculates the loss for a given set of trading results based on the slope
        of the equity curve.

        Parameters:
        - results (DataFrame): The DataFrame containing the profit or loss of each trade.
        - trade_count (int): The total number of trades in the results DataFrame.

        Returns:
        - float: The calculated loss value. A lower (more negative) value indicates a
                 strategy that is more likely to produce consistent profits over time.
        """

        # Calculate the cumulative profit over all trades to generate the equity curve.
        returns = results['profit_abs'].cumsum()
        
        # Generate a trendline with equal number of points as there are trades, spanning
        # from the first to the last point of the cumulative return.
        trendline = np.linspace(returns.iloc[0], returns.iloc[-1], trade_count)
        
        # Calculate the slope of the equity curve using linear regression.
        # np.polyfit returns coefficients of the polynomial, where the first element
        # is the slope and the second is the intercept.
        slope = np.polyfit(range(len(returns)), returns, 1)[0]
        
        # Penalize strategies that result in a net loss over all trades.
        if returns.iloc[-1] < 0:
            return MAX_LOSS
        
        # Return the negative slope as the loss. Strategies with upward equity curves
        # will have negative slopes (when inverted), which are lower (better) loss values.
        return -1.0 * slope
