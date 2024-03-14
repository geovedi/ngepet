import numpy as np
from freqtrade.strategy import CategoricalParameter, IStrategy


class StrategyWithATRAveraging(IStrategy):
    averaging_multiplier_ratio = CategoricalParameter(np.arange(1.0, 2.05, 0.05).round(2), default=1.6, space="sell")
    averaging_gap_ratio = CategoricalParameter(np.arange(0.25, 3.25, 0.25).round(2), default=1.0, space="sell")
    averaging_open_rate_method = CategoricalParameter(["AVERAGE", "DIRECTION"], default="AVERAGE", space="sell")
    averaging_mode = CategoricalParameter(["NONE", "UP", "DOWN", "BOTH"], default="UP", space="sell")


    def populate_indicators(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        # ...
        dataframe["atr"] = ta.EMA(ta.ATR(dataframe, timeperiod=15), timeperiod=20)
        return dataframe


    # def populate_entry_trend(...):
    # def populate_exit_trend(...):


    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float,
                              min_stake: Optional[float], max_stake: float,
                              current_entry_rate: float, current_exit_rate: float,
                              current_entry_profit: float, current_exit_profit: float,
                              **kwargs
                              ) -> Union[Optional[float], Tuple[Optional[float], Optional[str]]]:
        if not self._is_fresh_candle(current_time):
            return None

        entry_tag = trade.enter_tag
        if self.averaging_mode.value == "NONE":
            return None

        dataframe, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
        current_candle = dataframe.iloc[-1].squeeze()
        current_rate = current_candle["close"]
        atr = current_candle["atr"]
        side = -1 if trade.is_short else 1
        gap_ratio = self.averaging_gap_ratio.value
        new_position_trigger = None
        trade_dur = (current_time - trade.open_date_utc).days

        if current_profit < 0:
            # AVERAGING DOWN
            if trade.is_short:
                outter_order_price = max(t.safe_price for t in trade.orders)
            else:
                outter_order_price = min(t.safe_price for t in trade.orders)
            if self.averaging_mode.value in ["DOWN", "BOTH"]:
                new_position_rate = outter_order_price - (atr * gap_ratio * side)
                new_position_trigger = (
                    (current_rate >= new_position_rate)
                    if trade.is_short
                    else (current_rate <= new_position_rate)
                )
        else:
            # AVERAGING UP
            if trade.is_short:
                outter_order_price = min(t.safe_price for t in trade.orders)
            else:
                outter_order_price = max(t.safe_price for t in trade.orders)
            if self.averaging_mode.value in ["UP", "BOTH"]:
                new_position_rate = outter_order_price + (atr * gap_ratio * side)
                new_position_trigger = (
                    (current_rate <= new_position_rate)
                    if trade.is_short
                    else (current_rate >= new_position_rate)
                )

        if new_position_trigger:
            mult_ratio = self.averaging_multiplier_ratio.value
            num_orders = len(trade.orders) + 1
            return (
                mult_ratio * trade.orders[-1].stake_amount,
                f"{trade.enter_tag}_add_{num_orders:02d}",
            )

        return None
