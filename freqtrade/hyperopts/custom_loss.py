import numpy as np
import pandas as pd
from typing import Tuple
from datetime import datetime
from freqtrade.constants import Config
from freqtrade.data.metrics import calculate_max_drawdown, calculate_expectancy
from freqtrade.optimize.hyperopt import IHyperOptLoss

MAX_LOSS = 100000  # Define a fallback maximum loss value for non-ideal scenarios.
CHUNK_SIZE = 100  # Define the size of each chunk for calculating scores.
MAX_DRAWDOWN = 0.5  # Set the maximum acceptable drawdown ratio.
MIN_PERCENTILE = 20  # Define the percentile for the loss calculation.

def calculate_system_quality(trades: pd.DataFrame) -> float:
    """
    Calculate the system quality number (SQN) of a set of trades.

    The SQN is defined as the square root of the number of trades, multiplied by the
    mean of the profit ratio, divided by the standard deviation of the profit ratio.
    It is a measure of the system's performance and risk.

    Parameters:
    - trades (pd.DataFrame): The DataFrame containing trade results.

    Returns:
    - float: The calculated system quality number.
    """
    return (
        np.sqrt(len(trades))
        * trades["profit_ratio"].mean()
        / trades["profit_ratio"].std()
    )


class CustomLoss(IHyperOptLoss):
    """
    Custom loss function for hyperparameter optimization in trading strategies.

    This loss function considers multiple factors such as total profit, max drawdown,
    expectancy, and system quality number to evaluate the performance of a trading
    strategy. It aims to penalize strategies with poor performance or high risk.

    The final loss is calculated based on a negative percentile of scores derived from
    the trading results, encouraging strategies that consistently perform well across
    different segments of the data.
    """
    
    @staticmethod
    def hyperopt_loss_function(
        results: pd.DataFrame,
        config: Config,
        min_date: datetime,
        max_date: datetime,
        *args,
        **kwargs
    ) -> float:
        """
        Calculate the custom loss for a set of trading results.

        Parameters:
        - results (pd.DataFrame): DataFrame containing the results of backtesting.
        - config (Config): Configuration object containing settings like starting balance.
        - min_date (datetime): Start date for the period considered in the backtest.
        - max_date (datetime): End date for the period considered in the backtest.

        Returns:
        - float: The calculated loss. A lower (more negative) value indicates better performance.
        """
        if results.empty:
            return MAX_LOSS  # Return the maximum loss for empty result sets.

        starting_balance = config["dry_run_wallet"]
        max_drawdown_abs = calculate_max_drawdown(
            results,
            value_col="profit_abs",
            starting_balance=starting_balance,
            relative=True,
        )[0]
        total_profit_abs = results["profit_abs"].sum()
        backtest_days = (max_date - min_date).days or 1
        years = max(1, backtest_days // 365)

        # Penalize results with insufficient profit or excessive drawdown.
        if total_profit_abs < starting_balance * years or max_drawdown_abs / total_profit_abs > MAX_DRAWDOWN:
            return MAX_LOSS

        num_chunks = len(results) // CHUNK_SIZE
        truncated_results = results.iloc[:num_chunks * CHUNK_SIZE]

        scores = []

        # Evaluate the strategy performance in chunks to assess consistency and risk.
        for i in range(0, num_chunks * CHUNK_SIZE, CHUNK_SIZE):
            chunk = truncated_results.iloc[i : i + CHUNK_SIZE]
            total_profit_abs = chunk["profit_abs"].sum()
            max_drawdown_abs = calculate_max_drawdown(
                chunk,
                value_col="profit_abs",
                starting_balance=starting_balance,
                relative=True,
            )[0]
            exp, exp_ratio = calculate_expectancy(chunk)
            system_quality = calculate_system_quality(chunk)
            return_over_max_drawdown = total_profit_abs / max_drawdown_abs
            profit_ratio = total_profit_abs / starting_balance
            score = np.sqrt(
                exp_ratio * profit_ratio * system_quality * return_over_max_drawdown
            )
            scores.append(np.nan_to_num(score, nan=0.0, posinf=0.0, neginf=0.0))
            starting_balance += total_profit_abs

        # The loss is the negative value of the specified percentile of the scores, encouraging higher scores.
        return -np.percentile(scores, MIN_PERCENTILE) if scores else MAX_LOSS
