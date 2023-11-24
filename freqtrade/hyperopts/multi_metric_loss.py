from datetime import datetime
from pandas import DataFrame

from freqtrade.constants import Config
from freqtrade.optimize.hyperopt import IHyperOptLoss
from freqtrade.data.metrics import calculate_cagr, calculate_sharpe, calculate_underwater

class MultiMetricLoss(IHyperOptLoss):
    """
    Multi-metric loss function for hyperoptimization in freqtrade.

    This class is designed to balance multiple trading metrics including
    Compound Annual Growth Rate (CAGR), Sharpe ratio, profit factor, trade count,
    return/drawdown ratio and drawdown. It aims to find an optimal balance 
    between these metrics to maximize trading strategy effectiveness.

    Additionally, this class imposes a significant penalty if the final balance
    of a backtest is less than the starting balance, indicating a losing strategy.
    """

    @staticmethod
    def hyperopt_loss_function(results: DataFrame, trade_count: int,
                               min_date: datetime, max_date: datetime,
                               config: Config, *args, **kwargs) -> float:
        """
        Calculate the loss for a set of trading results based on multiple metrics.

        This function computes various trading metrics including CAGR, Sharpe ratio,
        profit factor, maximum drawdown, return/drawdown ratio and trade count. 
        These metrics are normalized, weighted, and summed to produce a loss value 
        which HyperOpt will seek to minimize.

        If the final balance is less than the starting balance, a heavy penalty is applied,
        effectively disqualifying losing strategies.
        """

        # Internal function to calculate profit factor
        def calculate_profit_factor(results: DataFrame) -> float:
            """Calculate the profit factor from the results DataFrame."""
            winning_profit = results.loc[results['profit_abs'] > 0, 'profit_abs'].sum()
            losing_profit = results.loc[results['profit_abs'] < 0, 'profit_abs'].sum()
            return winning_profit / abs(losing_profit) if losing_profit else 0.0

        # Internal function to normalize a metric to a 0-1 scale
        def normalize_metric(metric: float, min_value: float, max_value: float) -> float:
            return (min(metric, max_value) - min_value) / (max_value - min_value)

        # Calculate initial metrics
        starting_balance = config['dry_run_wallet']
        final_balance = starting_balance + results["profit_abs"].sum()
        backtest_days = (max_date - min_date).days or 1
        drawdown_df = calculate_underwater(results, value_col="profit_abs", starting_balance=starting_balance)
        max_drawdown = abs(min(drawdown_df["drawdown"]))
        profit_factor = calculate_profit_factor(results)
        sharpe_ratio = calculate_sharpe(results, min_date, max_date, starting_balance)
        cagr = calculate_cagr(backtest_days, starting_balance, final_balance)
        ret_dd_ratio = (final_balance - starting_balance) / (max_drawdown + 1e5)

        # Normalize metrics
        normalized_cagr = normalize_metric(cagr, 0.0, (backtest_days / 365) * 100)
        normalized_sharpe_ratio = normalize_metric(sharpe_ratio, 0.0, 5.0)
        normalized_profit_factor = normalize_metric(profit_factor, 0.0, 5.0)
        normalized_max_drawdown = normalize_metric(max_drawdown, 0.0, starting_balance * 5.0)
        normalized_trade_count = normalize_metric(trade_count, 0, 5000)
        normalized_ret_dd_ratio = normalize_metric(ret_dd_ratio, 0, 5.0)

        # Define weights for each metric
        weights = {
            "cagr": 1.0,
            "sharpe": 0.5,
            "profit_factor": 2.0,
            "ret_dd": 2.0, 
            "trade_count": 0.5,   # trade count might have less impact
            "drawdown": -2.0      # negative weight for drawdown as we want to minimize it
        }

        # Calculate weighted sum of metrics
        loss = (weights['cagr'] * normalized_cagr +
                weights['sharpe'] * normalized_sharpe_ratio +
                weights['profit_factor'] * normalized_profit_factor +
                weights['ret_dd'] * normalized_ret_dd_ratio +
                weights['trade_count'] * normalized_trade_count -
                weights['drawdown'] * normalized_max_drawdown)

        # Apply penalty if final balance is less than starting balance
        if final_balance < starting_balance:
            return abs(loss) * 100.0

        return -loss
