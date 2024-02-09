import numpy as np
import pandas as pd
from typing import Tuple
from datetime import datetime
from freqtrade.constants import Config
from freqtrade.data.metrics import calculate_max_drawdown, calculate_expectancy
from freqtrade.optimize.hyperopt import IHyperOptLoss

MAX_LOSS = 100000
CHUNK_SIZE = 100
MAX_DRAWDOWN = 0.5
MIN_PERCENTILE = 5

def calculate_system_quality(trades: pd.DataFrame) -> float:
    return (
        np.sqrt(len(trades))
        * trades["profit_ratio"].mean()
        / trades["profit_ratio"].std()
    )


class CustomLoss(IHyperOptLoss):
    @staticmethod
    def hyperopt_loss_function(
        results: pd.DataFrame,
        config: Config,
        min_date: datetime,
        max_date: datetime,
        *args,
        **kwargs
    ) -> float:
        if results.empty:
            return MAX_LOSS

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

        if total_profit_abs < starting_balance * years:
            return MAX_LOSS

        if max_drawdown_abs / total_profit_abs > MAX_DRAWDOWN:
            return MAX_LOSS

        num_chunks = len(results) // CHUNK_SIZE
        truncated_results = results.iloc[:num_chunks * CHUNK_SIZE]

        scores = []

        for i in range(0, num_chunks * CHUNK_SIZE, CHUNK_SIZE):
            chunk = truncated_results.iloc[i : i + CHUNK_SIZE]
            total_profit_abs = chunk["profit_abs"].sum()
            max_drawdown_abs = calculate_max_drawdown(
                chunk,
                value_col="profit_abs",
                # starting_balance=starting_balance,
                # relative=True,
            )[0]
            exp, exp_ratio = calculate_expectancy(chunk)
            system_quality = calculate_system_quality(chunk)
            return_over_max_drawdown = total_profit_abs / max_drawdown_abs
            profit_ratio = total_profit_abs / starting_balance
            score = np.sqrt(
                exp_ratio * profit_ratio * system_quality * return_over_max_drawdown
            )
            scores.append(np.nan_to_num(score, nan=0.0, posinf=0.0, neginf=0.0))
            # starting_balance += total_profit_abs

        return -np.percentile(scores, MIN_PERCENTILE) if scores else MAX_LOSS
