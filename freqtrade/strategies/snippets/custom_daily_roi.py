from datetime import datetime, timedelta

import numpy as np
from freqtrade.exchange import timeframe_to_prev_date
from freqtrade.strategy import CategoricalParameter, IStrategy


class StrategyWithCustomROI(IStrategy):
    # ...
    roi_days = CategoricalParameter(range(3, 14), default=7, space="sell")
    roi_max = CategoricalParameter(
        np.arange(0.2, 1.0, 0.05).round(2), default=0.45, space="sell"
    )

    @property
    def custom_roi(self):
        d = self.roi_days.value
        r = self.roi_max.value
        n = 2  # gap day
        roi = [(d, -1.0)] + list(
            zip(reversed(range(1, d, n)), np.linspace(0, r, d // n).round(3))
        )
        return roi

    # def populate_indicators(...):
    # def populate_entry_trend(...):
    # def populate_exit_trend(...):

    def custom_exit(
        self,
        pair: str,
        trade: "Trade",
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ):
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        current_profit = trade.calc_profit_ratio(dataframe["close"].iat[-1])
        trade_dur = (current_time - trade.open_date_utc).days

        for min_days, min_roi in self.custom_roi:
            if trade_dur >= min_days and current_profit >= min_roi:
                return f"roi_{min_days:02d}_{min_roi:.03f}"

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
