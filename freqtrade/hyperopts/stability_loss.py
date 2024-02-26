import numpy as np
from pandas import DataFrame, date_range
from freqtrade.optimize.hyperopt import IHyperOptLoss
from datetime import datetime

MAX_LOSS = 100000  # Define a fallback maximum loss value for non-ideal scenarios.
RESAMPLE_FREQ = '1D'
SLIPPAGE_PER_TRADE_RATIO = 0.0005

class StabilityLoss(IHyperOptLoss):
    """
    Custom loss function that evaluates the stability of a trading strategy by comparing
    the equity curve's similarity to a linear trendline. This is achieved by calculating
    the distance between the cumulative returns (after adjusting for slippage) and 
    a linear trendline spanning from the start to the end of the trading period.

    The aim is to favor strategies that produce stable and consistent returns over time,
    penalizing those that deviate significantly from a steady growth path.

    A higher similarity (lower distance) to the trendline results in a lower loss value,
    with the final loss being inversely related to the average similarity across the period.
    """

    @staticmethod
    def hyperopt_loss_function(results: DataFrame, trade_count: int,
                               min_date: datetime, max_date: datetime,
                               *args, **kwargs) -> float:
        """
        Calculates the loss based on the stability of the strategy's returns.

        Parameters:
        - results (DataFrame): DataFrame containing the results of the trades, including
          'profit_ratio' and 'close_date'.
        - trade_count (int): Total number of trades executed.
        - min_date (datetime): Start date of the trading period.
        - max_date (datetime): End date of the trading period.

        Returns:
        - float: Calculated loss, with a higher (less negative) value indicating a
                 strategy that deviates more from stable, linear growth.
        """
        # Adjust profit ratios for slippage and resample to daily sums.
        results['profit_ratio_after_slippage'] = results['profit_ratio'] - SLIPPAGE_PER_TRADE_RATIO
        t_index = date_range(start=min_date, end=max_date, freq=RESAMPLE_FREQ, normalize=True)
        sum_daily = results.resample(RESAMPLE_FREQ, on='close_date').agg(
            {"profit_ratio_after_slippage": 'sum'}
        ).reindex(t_index).fillna(0)

        # Calculate cumulative returns and generate a linear trendline for comparison.
        returns = sum_daily['profit_ratio_after_slippage'].cumsum()
        trendline = np.linspace(returns.iloc[0], returns.iloc[-1], len(returns))

        # Compute the distance between the returns and the trendline.
        distance = np.linalg.norm(trendline - returns)
        # Convert distance to similarity scores, with smaller distances indicating higher similarity.
        score = 1 / (distance + 1) * np.log(returns.iloc[-1])

        # Penalize strategies that result in a net loss over the period, otherwise return the negative stability.
        return MAX_LOSS if returns.iloc[-1] <= 0 else -score
