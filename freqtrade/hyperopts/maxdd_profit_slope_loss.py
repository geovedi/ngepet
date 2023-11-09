import numpy as np
from pandas import DataFrame
from freqtrade.optimize.hyperopt import IHyperOptLoss
from freqtrade.data.metrics import calculate_max_drawdown
from freqtrade.constants import Config

MIN_TRADES = 500
MIN_TOTAL_PROFIT = 50000.0


class MaxDrawdownProfitSlopeLoss(IHyperOptLoss):
    """Custom loss function for freqtrade hyperparameter optimization that balances
    total return with risk management.

    This loss function considers maximum drawdown, profit slope, and total profit.
    It rewards strategies with a positive profit slope and penalizes higher drawdowns
    to find parameter sets that maximize
    profit while controlling for risk.

    Attributes:
        None
    """

    @staticmethod
    def hyperopt_loss_function(
        results: DataFrame, trade_count: int, config: Config, *args, **kwargs
    ) -> float:
        """Calculate the loss score for hyperparameter optimization.

        Args:
            results (DataFrame): DataFrame containing trading results.
            trade_count (int): Number of trades.
            config (Config): Configuration dictionary.
            *args, **kwargs: Additional arguments (not used).

        Returns:
            float: Loss score for optimization.
        """
        # Calculate cumulative profit over trades
        profits = results["profit_abs"].cumsum()
        starting_balance = config["dry_run_wallet"]

        # Early exit with a high loss score if trade count or total profit
        # criteria are not met
        if trade_count < MIN_TRADES or profits.iloc[-1] < MIN_TOTAL_PROFIT:
            return 9999.0

        # Number of Monte Carlo simulations
        num_simulations = 1000
        sim_results = []

        # Perform Monte Carlo simulations to assess risk
        for _ in range(num_simulations):
            # Shuffle trading results to simulate different outcomes
            shuffled_results = results.sample(frac=1, replace=False)

            # Calculate net profit and maximum drawdown for the simulated results
            sim_net_profit = shuffled_results["profit_abs"].cumsum().iloc[-1]
            try:
                sim_max_dd = calculate_max_drawdown(
                    shuffled_results,
                    value_col="profit_abs",
                    starting_balance=starting_balance,
                    relative=True,
                )[0]
            except ValueError:
                # Assign a small non-zero value if there's no drawdown
                sim_max_dd = 1e-5

            sim_results.append((sim_net_profit, sim_max_dd))

        # Calculate the 20th percentile of net profit and 80th percentile
        # of max drawdown from simulations
        profit_lower = np.percentile([x[0] for x in sim_results], 20.0)
        max_dd_upper = np.percentile([x[1] for x in sim_results], 80.0)

        # Calculate the actual maximum drawdown from the original results
        try:
            max_dd = calculate_max_drawdown(
                results,
                value_col="profit_abs",
                starting_balance=starting_balance,
                relative=True,
            )[0]
        except ValueError:
            max_dd = 1e-5

        # Check if profit and drawdown criteria are met based on Monte Carlo simulations
        if profit_lower < 0.5 * profits.iloc[-1] or max_dd_upper > 2.0 * max_dd:
            return 9999.0

        # Generate a trendline for profit slope calculation
        trendline = np.linspace(profits.iloc[0], profits.iloc[-1], trade_count)

        # Calculate the slope of the profit curve
        slope = np.polyfit(trendline, profits, 1)[0]

        # Calculate the final score using a combination of slope, profit, and max drawdown
        final_score = np.round(
            -1.0 * slope * np.log(trade_count) * np.log(profits.iloc[-1] / max_dd), 5
        )
        return final_score
