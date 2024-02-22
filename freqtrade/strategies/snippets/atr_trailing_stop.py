import numpy as np
from freqtrade.strategy import CategoricalParameter, IStrategy

# from freqtrade.exchange import timeframe_to_prev_date


class StrategyWithATRTrailingStop(IStrategy):
    # ...
    trailing_start = CategoricalParameter(
        np.arange(0.25, 6.0, 0.25).round(2), default=1.5, space="sell"
    )

    trailing_offset = CategoricalParameter(
        np.arange(0.25, 3.0, 0.25).round(2), default=0.5, space="sell"
    )

    stop_loss_ratio = CategoricalParameter(
        np.arange(0.25, 6.0, 0.25).round(2), default=1.5, space="sell"
    )

    max_trade_day = CategoricalParameter(range(1, 30, 2), default=7, space="sell")

    def populate_indicators(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        # ...
        dataframe["atr"] = ta.EMA(ta.ATR(dataframe, timeperiod=15), timeperiod=20)
        return dataframe

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
        if not self._is_fresh_candle(current_time):
            return None

        trade_dur = (current_time - trade.open_date_utc).days
        if trade_dur >= self.max_trade_day.value:
            return "expired"

        dataframe, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
        current_candle = dataframe.iloc[-1].squeeze()
        current_rate = current_candle["close"]

        # -- faster method; EMA-ATR should give a reasonable true range.
        atr = current_candle["atr"]

        # -- slower method; need to import timeframe_to_prev_date
        # trade_date = timeframe_to_prev_date(self.timeframe, trade.open_date_utc)
        # trade_candle = dataframe.loc[dataframe['date'] == trade_date]
        # if trade_candle.empty:
        #     return None
        # atr = trade_candle["atr"]

        stop_loss_value = self.stop_loss_ratio.value
        trailing_start_value = self.trailing_start.value
        trailing_offset_value = self.trailing_offset.value

        side = -1 if trade.is_short else 1

        stop_loss_rate = trade.open_rate - (atr * stop_loss_value * side)
        trailing_start_rate = trade.open_rate + (atr * trailing_start_value * side)
        trailing_stop_rate = (
            min(trade.open_rate, trade.min_rate + (atr * trailing_offset_value))
            if trade.is_short
            else max(trade.open_rate, trade.max_rate - (atr * trailing_offset_value))
        )

        stop_loss_trigger = (
            current_rate <= stop_loss_rate
            if not trade.is_short
            else current_rate >= stop_loss_rate
        )

        trailing_stop_trigger = (
            (current_rate <= trailing_start_rate and current_rate >= trailing_stop_rate)
            if trade.is_short
            else (
                current_rate >= trailing_start_rate
                and current_rate <= trailing_stop_rate
            )
        )

        if stop_loss_trigger:
            return "stop_loss"
        elif trailing_stop_trigger:
            return "trailing_stop"

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
