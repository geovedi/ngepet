import numpy as np
from pandas import DataFrame
from freqtrade.optimize.hyperopt import IHyperOptLoss

class SQNLoss(IHyperOptLoss):
    """
    Custom loss function class that evaluates the performance of a trading strategy
    using the System Quality Number (SQN) metric. SQN is a measure of a system’s efficiency
    and risk-adjusted profitability, calculated as the mean of the profit ratio divided by
    its standard deviation, scaled by the square root of the number of trades.

    This loss function aims to prioritize trading strategies that demonstrate not only
    profitability but also consistency and low volatility in returns.

    The higher the SQN value, the better the trading system. However, since the hyperopt
    process seeks to minimize the loss function, the negative of the SQN value is returned.
    """

    @staticmethod
    def hyperopt_loss_function(results: DataFrame, *args, **kwargs) -> float:
        """
        Calculates the loss for a given set of trading results based on the SQN metric.

        Parameters:
        - results (DataFrame): The DataFrame containing the results of trades, specifically
          the 'profit_ratio' column.

        Returns:
        - float: The calculated loss value, which is the negative of the SQN metric. A lower
                 (more negative) value indicates a better-performing strategy.
        """

        profit = results['profit_ratio']  # Extract the profit ratio from the results.

        # Define the chunk size for grouping trades, ensuring all chunks are of equal size.
        chunk_size = 100
        num_chunks = len(profit) // chunk_size  # Calculate the number of complete chunks.
        truncated_profit = profit[:num_chunks * chunk_size]  # Truncate to fit complete chunks.

        # Reshape the profit data into a matrix where each row represents a chunk.
        reshaped = truncated_profit.values.reshape(-1, chunk_size)
        
        # Calculate the mean and standard deviation for each chunk.
        mean = np.mean(reshaped, axis=1)
        std = np.std(reshaped, axis=1)
        
        # Replace any standard deviations of zero with NaN to avoid division by zero.
        std[std == 0] = np.nan

        # Calculate the SQN value for each chunk and filter out any NaN values.
        sqn_values = (mean / std) * np.sqrt(chunk_size)
        sqn_values = sqn_values[~np.isnan(sqn_values)]

        # If there are no valid SQN values, return zero as the loss.
        if len(sqn_values) == 0:
            return 0.0

        # Calculate the mean SQN across all chunks and return its negative as the loss.
        sqn = np.mean(sqn_values)
        return -sqn
