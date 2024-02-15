import numpy as np
import pandas as pd
from scipy.stats import norm
from freqtrade.optimize.hyperopt import IHyperOptLoss
from freqtrade.constants import Config
from freqtrade.data.metrics import calculate_max_drawdown

# Predefined constants to control the behavior of the loss function.
ITERATIONS = 500  # Number of Monte Carlo simulations to run.
QUANTILE = 0.1  # Quantile used to determine the Monte Carlo simulation outcome.
CHUNK_SIZE = 100  # Size of chunks for SQN calculation.
MAX_DRAWDOWN = 0.3  # Maximum allowed drawdown ratio.
MIN_SQN = 2.0  # Minimum acceptable System Quality Number (SQN).
MAX_LOSS = 100000  # Maximum loss value to use as a penalty.

np.random.seed(1337)  # Seed for reproducibility of Monte Carlo simulations.

class MontecarloSQNLoss(IHyperOptLoss):
    """
    Custom loss function that combines Monte Carlo simulations, System Quality Number (SQN),
    and maximum drawdown to evaluate the performance and risk of trading strategies.

    The loss function penalizes strategies with high drawdown, low SQN, and poor
    Monte Carlo simulation outcomes, encouraging strategies that are both profitable
    and robust.
    """
    
    @staticmethod
    def hyperopt_loss_function(
        results: pd.DataFrame, config: Config, *args, **kwargs
    ) -> float:
        """
        Calculates the loss for a given set of trading results.

        Parameters:
        - results (pd.DataFrame): Trading results dataframe.
        - config (Config): Configuration object containing settings like starting balance.

        Returns:
        - float: Calculated loss. Lower (more negative) values indicate better performance.
        """
        # Calculate metrics used to evaluate strategy performance.
        mc_profit_ratio = MontecarloSQNLoss._calculate_mc_profit_ratio(results, config)
        sqn = MontecarloSQNLoss._calculate_sqn(results)
        dd = MontecarloSQNLoss._calculate_drawdown(results, config)
        profit_total = results["profit_abs"].sum()

        # Apply penalties based on performance criteria.
        if (
            profit_total <= 0
            or mc_profit_ratio <= 0
            or dd >= MAX_DRAWDOWN
            or sqn <= MIN_SQN
        ):
            return MAX_LOSS

        return -mc_profit_ratio  # Negate the profit ratio as we seek to minimize the loss.

    @staticmethod
    def _calculate_drawdown(results: pd.DataFrame, config: Config) -> float:
        """
        Calculates the maximum drawdown ratio from the trading results.

        Parameters:
        - results (pd.DataFrame): Trading results.
        - config (Config): Configuration object with starting balance.

        Returns:
        - float: The maximum drawdown ratio.
        """
        starting_balance = config["dry_run_wallet"]
        try:
            max_drawdown_relative = abs(
                calculate_max_drawdown(
                    results,
                    value_col="profit_abs",
                    starting_balance=starting_balance,
                    relative=True,
                )[5]  # Index 5 corresponds to the maximum drawdown value.
            )
        except Exception as e:
            import logging
            logging.error(e)  # Log error if drawdown calculation fails.
            max_drawdown_relative = 0.0
        return max_drawdown_relative

    @staticmethod
    def _calculate_mc_profit_ratio(results: pd.DataFrame, config: Config) -> float:
        """
        Performs a Monte Carlo simulation to estimate future profit ratio.

        Parameters:
        - results (pd.DataFrame): Trading results.
        - config (Config): Configuration object with starting balance.

        Returns:
        - float: Estimated profit ratio from the Monte Carlo simulation.
        """
        starting_balance = config["dry_run_wallet"]
        t_intervals = len(results["profit_abs"])

        # Calculate cumulative profit and log returns for Monte Carlo simulation.
        cum_profit = starting_balance + results["profit_abs"].cumsum()
        log_returns = np.log(1 + cum_profit.pct_change())

        # Estimate future returns using Monte Carlo simulation.
        drift = log_returns.mean() - (0.5 * log_returns.var())
        stdev = log_returns.std()
        random_factors = norm.ppf(np.random.rand(t_intervals, ITERATIONS))
        mc_returns = np.exp(drift + stdev * random_factors)

        # Calculate Monte Carlo profit outcomes and the specified quantile.
        profit_mc = np.zeros_like(mc_returns)
        profit_mc[0] = starting_balance
        for t in range(1, t_intervals):
            profit_mc[t] = profit_mc[t - 1] * mc_returns[t]

        mc_profit = np.quantile(profit_mc[-1], QUANTILE)
        return (mc_profit - starting_balance) / starting_balance

    @staticmethod
    def _calculate_sqn(results: pd.DataFrame) -> float:
        """
        Calculates the System Quality Number (SQN) for the trading strategy.

        Parameters:
        - results (pd.DataFrame): Trading results.

        Returns:
        - float: The calculated SQN value.
        """
        profit = results["profit_ratio"]
        num_chunks = len(profit) // CHUNK_SIZE
        truncated_profit = profit[: num_chunks * CHUNK_SIZE]
        reshaped = truncated_profit.values.reshape(-1, CHUNK_SIZE)
        mean = np.mean(reshaped, axis=1)
        std = np.std(reshaped, axis=1)
        std[std == 0] = np.nan  # Avoid division by zero.
        sqn_values = (mean / std) * np.sqrt(CHUNK_SIZE)
        sqn_values = sqn_values[~np.isnan(sqn_values)]
        return np.mean(sqn_values) if len(sqn_values) > 0 else 0
