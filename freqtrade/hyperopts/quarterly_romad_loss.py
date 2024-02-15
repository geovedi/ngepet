import numpy as np
from datetime import datetime
from pandas import DataFrame, DateOffset, date_range
from freqtrade.optimize.hyperopt import IHyperOptLoss
from freqtrade.data.metrics import calculate_max_drawdown

MAX_LOSS = 100000  # Define a maximum loss value to be used as a fallback.
MIN_PERCENTILE = 20  # Define the minimum percentile for loss calculation.


class BaseReturnOverMaxDrawdownLoss(IHyperOptLoss):
    """
    Base class for calculating loss based on return over maximum drawdown.

    This class provides the common functionality to calculate the loss for hyperparameter
    optimization processes, focusing on the return over maximum drawdown ratio for 3-month
    periods within a specified date range. It is designed to be subclassed by more specific
    loss calculation strategies.

    Methods:
        calculate_loss(scores): Abstract method to calculate the final loss from scores.
        hyperopt_loss_function(results, min_date, max_date, *args, **kwargs): Calculates
        the scores based on return over maximum drawdown and delegates to calculate_loss
        for the final loss calculation.
    """

    @staticmethod
    def calculate_loss(scores):
        """Placeholder for the loss calculation method. Should be overridden by subclasses."""
        raise NotImplementedError("This method should be overridden by subclasses")

    @classmethod
    def hyperopt_loss_function(
        cls, results: DataFrame, min_date: datetime, max_date: datetime, *args, **kwargs
    ) -> float:
        """Calculates scores for each 3-month period and returns the aggregated loss."""
        scores = []

        # Generate start dates for each 3-month period within the given date range.
        start_dates = date_range(start=min_date, end=max_date, freq="MS")

        for start_date in start_dates:
            end_date = start_date + DateOffset(months=3)
            # Break the loop if the period exceeds the max_date.
            if end_date > max_date:
                break

            # Filter the results DataFrame for trades within the current period.
            chunk = results[
                (results.open_date >= start_date) & (results.close_date < end_date)
            ]

            # Calculate score if the chunk is not empty.
            if not chunk.empty:
                total_profit = chunk["profit_abs"].sum()
                try:
                    # Calculate max drawdown and append the score.
                    max_drawdown = calculate_max_drawdown(
                        chunk, value_col="profit_abs"
                    )[0]
                    scores.append(
                        total_profit / max_drawdown if max_drawdown else total_profit
                    )
                except Exception:
                    scores.append(total_profit)

        # Use the subclass's calculate_loss method to determine the final loss.
        return cls.calculate_loss(scores) if scores else MAX_LOSS


class MedianReturnOverMaxDrawdownLoss(BaseReturnOverMaxDrawdownLoss):
    """
    Subclass for calculating hyperopt loss based on the median return over max drawdown.

    This class overrides the calculate_loss method to calculate the loss as the negative
    median of all calculated return over max drawdown ratios. It aims to optimize the
    median performance of the trading strategy.
    """

    @staticmethod
    def calculate_loss(scores):
        """Returns the negative median of scores as the loss."""
        return -np.median(scores)


class MinPercentileReturnOverMaxDrawdownLoss(BaseReturnOverMaxDrawdownLoss):
    """
    Subclass for calculating hyperopt loss based on the minimum percentile of return 
    over max drawdown.

    This class overrides the calculate_loss method to focus on improving the worst-case
    performance scenarios by optimizing for a specified percentile (MIN_PERCENTILE) of
    the return over max drawdown ratios.
    """

    @staticmethod
    def calculate_loss(scores):
        """Returns the negative value of the specified percentile of scores as the loss."""
        return -np.percentile(scores, MIN_PERCENTILE)
