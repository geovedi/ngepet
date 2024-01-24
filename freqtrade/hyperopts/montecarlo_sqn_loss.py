import numpy as np
import pandas as pd
from scipy.stats import norm
from freqtrade.optimize.hyperopt import IHyperOptLoss
from freqtrade.constants import Config
from freqtrade.data.metrics import calculate_max_drawdown

# Constants
ITERATIONS = 500
QUANTILE = 0.1
CHUNK_SIZE = 100
MAX_DRAWDOWN = 0.3
MIN_SQN = 2.0

np.random.seed(1337)


class MontecarloSQNLoss(IHyperOptLoss):
    @staticmethod
    def hyperopt_loss_function(
        results: pd.DataFrame, config: Config, *args, **kwargs
    ) -> float:
        mc_profit_ratio = MontecarloSQNLoss._calculate_mc_profit_ratio(results, config)
        sqn = MontecarloSQNLoss._calculate_sqn(results)
        dd = MontecarloSQNLoss._calculate_drawdown(results, config)
        profit_total = results["profit_abs"].sum()

        if (
            profit_total <= 0
            or mc_profit_ratio <= 0
            or dd >= MAX_DRAWDOWN
            or sqn <= MIN_SQN
        ):
            return 100000

        return -mc_profit_ratio

    @staticmethod
    def _calculate_drawdown(results: pd.DataFrame, config: Config) -> float:
        starting_balance = config["dry_run_wallet"]
        try:
            max_drawdown_relative = abs(
                calculate_max_drawdown(
                    results,
                    value_col="profit_abs",
                    starting_balance=starting_balance,
                    relative=True,
                )[5]
            )
        except Exception as e:
            import logging

            logging.error(e)
            max_drawdown_relative = 0.0
        return max_drawdown_relative

    @staticmethod
    def _calculate_mc_profit_ratio(results: pd.DataFrame, config: Config) -> float:
        starting_balance = config["dry_run_wallet"]
        t_intervals = len(results["profit_abs"])

        cum_profit = starting_balance + results["profit_abs"].cumsum()
        log_returns = np.log(1 + cum_profit.pct_change())

        drift = log_returns.mean() - (0.5 * log_returns.var())
        stdev = log_returns.std()
        random_factors = norm.ppf(np.random.rand(t_intervals, ITERATIONS))
        mc_returns = np.exp(drift + stdev * random_factors)

        profit_mc = np.zeros_like(mc_returns)
        profit_mc[0] = starting_balance
        for t in range(1, t_intervals):
            profit_mc[t] = profit_mc[t - 1] * mc_returns[t]

        mc_profit = np.quantile(profit_mc[-1], QUANTILE)
        return (mc_profit - starting_balance) / starting_balance

    @staticmethod
    def _calculate_sqn(results: pd.DataFrame) -> float:
        profit = results["profit_abs"].cumsum().pct_change()
        num_chunks = len(profit) // CHUNK_SIZE
        truncated_profit = profit[: num_chunks * CHUNK_SIZE]
        reshaped = truncated_profit.values.reshape(-1, CHUNK_SIZE)
        mean = np.mean(reshaped, axis=1)
        std = np.std(reshaped, axis=1)
        std[std == 0] = np.nan
        sqn_values = (mean / std) * np.sqrt(CHUNK_SIZE)
        sqn_values = sqn_values[~np.isnan(sqn_values)]
        return np.mean(sqn_values) if len(sqn_values) > 0 else 0
