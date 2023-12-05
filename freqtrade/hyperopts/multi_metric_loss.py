import numpy as np
from datetime import datetime
from pandas import DataFrame

from freqtrade.constants import Config
from freqtrade.optimize.hyperopt import IHyperOptLoss
from freqtrade.data.metrics import (
    calculate_cagr,
    calculate_sharpe,
    calculate_sortino,
    calculate_calmar,
    calculate_max_drawdown,
)

class MultiMetricLoss(IHyperOptLoss):

    @staticmethod
    def hyperopt_loss_function(
        results: DataFrame,
        trade_count: int,
        min_date: datetime,
        max_date: datetime,
        config: Config,
        *args,
        **kwargs
    ) -> float:

        # Internal function to normalize a metric to a 0-1 scale
        def normalize_metric(
            metric: float, min_value: float, max_value: float
        ) -> float:
            return (min(metric, max_value) - min_value) / (max_value - min_value)

        # Calculate initial metrics
        start_balance = config["dry_run_wallet"]
        total_profit = results["profit_abs"].sum()
        final_balance = start_balance + total_profit
        backtest_days = (max_date - min_date).days or 1
        try:
            max_drawdown = abs(calculate_max_drawdown(results, 
                value_col="profit_abs", 
                starting_balance=start_balance)[5])
        except:
            max_drawdown = 0.0

        total_profit_pct = (total_profit / start_balance * 100.0)
        cagr = calculate_cagr(backtest_days, start_balance, final_balance)
        sortino = calculate_sortino(results, min_date, max_date, start_balance)
        sharpe = calculate_sharpe(results, min_date, max_date, start_balance)
        calmar = calculate_calmar(results, min_date, max_date, start_balance)
        max_drawdown_pct = (max_drawdown / start_balance * 100.0)

        # XXX: Normalize metrics -- ADJUST TO YOUR NEED!
        normalized_profit = normalize_metric(total_profit_pct, 0, (backtest_days / 365) * 100)
        normalized_cagr = normalize_metric(cagr, 0, 120.0)
        normalized_sortino = normalize_metric(sortino, 0, 15.0)
        normalized_sharpe = normalize_metric(sharpe, 0, 7.0)
        normalized_calmar = normalize_metric(calmar, 0, 80.0)
        normalized_drawdown = normalize_metric(max_drawdown_pct, 0, 20.0)

        # Define weights for each metric
        weights = {
            "profit": 2.0,
            "cagr": 1.0,
            "sortino": 1.0,
            "sharpe": 1.0,
            "calmar": 1.0,
            "drawdown": -2.0,  # negative weight
        }

        # Calculate weighted sum of metrics
        loss = (
            weights["profit"] * normalized_profit
            + weights["cagr"] * normalized_cagr
            + weights["sortino"] * normalized_sortino
            + weights["sharpe"] * normalized_sharpe
            + weights["calmar"] * normalized_calmar
            + weights["drawdown"] * normalized_drawdown
        )

        # Apply penalty if final balance is less than starting balance
        if final_balance < start_balance:
            return abs(loss) * 100.0

        return -loss
