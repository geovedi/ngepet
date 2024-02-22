# WARNING: This code is experimental and not known to be profitable!

import numpy as np
from freqtrade.strategy import CategoricalParameter, IStrategy


class StrategyWithOpenProfitRatio(IStrategy):
    # ...
    take_profit_ratio = CategoricalParameter(
        np.arange(1.0, 20.25, 0.25).round(2), default=3.0, space="sell"
    )
    stop_loss_ratio = CategoricalParameter(
        np.arange(0.05, 1.0, 0.05).round(2), default=0.25, space="sell"
    )

    # def populate_indicators(...):
    # def populate_entry_trend(...):
    # def populate_exit_trend(...):

    def custom_exit(
        self,
        pair: str,
        trade: "Trade",
        current_time: "datetime",
        current_rate: float,
        current_profit: float,
        **kwargs,
    ):
        trade_max_profit = trade.calc_profit_ratio(trade.max_rate)
        trade_min_profit = trade.calc_profit_ratio(trade.min_rate)
        profit_ratio = trade_max_profit / abs(trade_min_profit)

        if profit_ratio >= self.take_profit_ratio.value:
            return "take_profit"
        elif profit_ratio <= self.stop_loss_ratio.value:
            return "stop_loss"

    def custom_exit_price(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        proposed_rate: float,
        current_profit: float,
        exit_tag: Optional[str],
        **kwargs,
    ) -> float:
        dataframe, last_updated = self.dp.get_analyzed_dataframe(
            pair=pair, timeframe=self.timeframe
        )
        return dataframe["close"].iat[-1]
