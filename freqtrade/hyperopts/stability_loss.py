import numpy as np

from datetime import datetime
from pandas import DataFrame, date_range
from freqtrade.constants import Config
from freqtrade.optimize.hyperopt import IHyperOptLoss

MAX_LOSS = 100000
RESAMPLE_FREQ = '1D'
SLIPPAGE_PER_TRADE_RATIO = 0.0005
DAYS_IN_YEAR = 365
MIN_ANNUAL_GROWTH_COEF = 1.0


def cosine_similarity(A, B):
    """
    Calculates the cosine similarity between two time-series datasets A and B.
    """
    # Normalize the datasets
    A_norm = (A - np.mean(A)) / np.std(A)
    B_norm = (B - np.mean(B)) / np.std(B)
 
    # Calculate dot product and norms
    dot_product = np.dot(A_norm, B_norm)
    norm_A = np.linalg.norm(A_norm)
    norm_B = np.linalg.norm(B_norm)
 
    # Calculate cosine similarity
    cosine_sim = dot_product / (norm_A * norm_B)
 
    return cosine_sim


class StabilityLoss(IHyperOptLoss):
    """
    A custom loss class for the freqtrade optimization process, focusing on the stability of profits.
    Inherits from freqtrade's IHyperOptLoss interface.
    """

    @staticmethod
    def hyperopt_loss_function(results: DataFrame, trade_count: int, config: Config,
                               min_date: datetime, max_date: datetime,
                               *args, **kwargs) -> float:
        starting_balance = config["dry_run_wallet"]
        total_profit_abs = results["profit_abs"].sum()
        backtest_days = (max_date - min_date).days or 1
        years = max(1, backtest_days // DAYS_IN_YEAR)

        if total_profit_abs < starting_balance * years * MIN_ANNUAL_GROWTH_COEF:
            return MAX_LOSS

        # Adjust profits for slippage and resample to daily
        results['profit_ratio_after_slippage'] = results['profit_ratio'] - SLIPPAGE_PER_TRADE_RATIO
        t_index = date_range(start=min_date, end=max_date, freq=RESAMPLE_FREQ, normalize=True)
        sum_daily = results.resample(RESAMPLE_FREQ, on='close_date').agg(
            {"profit_ratio_after_slippage": 'sum'}
        ).reindex(t_index).fillna(0)

        # Calculate cumulative returns and linear trend
        returns = sum_daily['profit_ratio_after_slippage'].cumsum()
        trendline = np.linspace(returns.iloc[0], returns.iloc[-1], len(returns))

        # Compute cosine similarity with the trendline
        similarity = cosine_similarity(trendline, returns)
        score = np.log(returns.iloc[-1]) * similarity

        # Apply penalty for net losses, otherwise return negative stability score
        return MAX_LOSS if returns.iloc[-1] <= 0 else -score
