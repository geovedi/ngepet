import numpy as np
from freqtrade.strategy import CategoricalParameter, IStrategy

# from freqtrade.exchange import timeframe_to_prev_date


class StrategyWithRewardRiskRatio(IStrategy):
    # ...
    reward_risk_ratio = CategoricalParameter(
        np.arange(1.0, 20.25, 0.25).round(2), default=3.0, space="sell"
    )
    stop_loss_ratio = CategoricalParameter(
        np.arange(0.5, 5.0, 0.05).round(2), default=1.5, space="sell"
    )

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
        take_profit_value = stop_loss_value * self.reward_risk_ratio.value

        side = 1 if trade.is_short else -1
        stop_loss_rate = trade.open_rate + (atr * stop_loss_value * side)
        take_profit_rate = trade.open_rate - (atr * take_profit_value * side)

        if current_rate >= take_profit_rate:
            return "take_profit"
        elif current_rate <= stop_loss_rate:
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
