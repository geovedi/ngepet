import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union

import numpy as np
import riskfolio as rp
import talib.abstract as ta
from freqtrade.constants import Config
from freqtrade.exchange import timeframe_to_minutes
from freqtrade.optimize.space import Categorical, Dimension, SKDecimal
from freqtrade.persistence import Trade
from freqtrade.strategy import CategoricalParameter, IntParameter, IStrategy
from pandas import DataFrame, Series

logger = logging.getLogger(__name__)

# fmt: on
RISK_MEASURES = ["vol", "MV", "MAD", "GMD", "MSV", "FLPM", "SLPM", "VaR", "CVaR",
    "TG", "EVaR", "WR", "RG", "CVRG", "TGRG", "MDD", "ADD", "DaR", "CDaR", "EDaR",
    "UCI", "MDD_Rel", "ADD_Rel", "DaR_Rel", "CDaR_Rel", "EDaR_Rel", "UCI_Rel",
]
# fmt: off


class HRPStrategy(IStrategy):
    INTERFACE_VERSION: int = 3
    timeframe: str = "12h"
    can_short: bool = False
    process_only_new_candles: bool = False
    use_exit_signal: bool = False
    ignore_buying_expired_candle_after: int = 3600
    startup_candle_count: int = 100
    position_adjustment_enable: bool = True

    minimal_roi: Dict[str, float] = {}
    stoploss: float = -0.5
    trailing_stop: bool = True
    trailing_stop_positive: float = 0.05
    trailing_stop_positive_offset: float = 0.2
    trailing_only_offset_is_reached: bool = True

    entry_dayofweek = IntParameter(0, 6, default=0, space="buy")
    rebalance_candle = CategoricalParameter(range(10, 360, 10), default=10, space="buy")
    risk_measure = CategoricalParameter(RISK_MEASURES, default="MV", space="buy", optimize=False)
    max_num_pairs: int = 5

    class HyperOpt:
        def stoploss_space() -> List[Dimension]:
            stoploss_ranges = np.arange(-0.5, 0, 0.025).round(3)
            return [Categorical(stoploss_ranges, name="stoploss")]
        
        def trailing_space() -> List[Dimension]:
            stop_ranges = np.arange(0.025, 0.175, 0.025).round(3)
            offset_ranges = np.arange(0.125, 0.225, 0.025).round(3)
            return [
                Categorical([True], name="trailing_stop"),
                Categorical(stop_ranges, name="trailing_stop_positive"),
                Categorical(offset_ranges, name="trailing_stop_positive_offset_p1"),
                Categorical([True], name="trailing_only_offset_is_reached"),
            ]


    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.config = config

        for idx in range(self.max_num_pairs):
            setattr(
                self,
                f"pair_{idx:02d}",
                CategoricalParameter(
                    self.config["exchange"]["pair_whitelist"], 
                    default="ETH/BTC",
                    space="buy"
                )
            )

    @property
    def selected_pairs(self):
        return set([getattr(self, f"pair_{i:02d}").value for i in range(self.max_num_pairs)])

    def populate_indicators(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        dataframe["dayofweek"] = dataframe["date"].dt.dayofweek
        dataframe["hour"] = dataframe["date"].dt.hour
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        dataframe.loc[
            ((dataframe["dayofweek"] == self.entry_dayofweek.value) 
                & (dataframe["hour"] == 0)),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        return dataframe

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: Optional[float], max_stake: float,
                            leverage: float, entry_tag: Optional[str], side: str,
                            **kwargs) -> float:
        weights = self.calculate_weights()
        pair_weight = weights.get(pair, 0.0)
        capital = self.wallets.get_total_stake_amount()
        stake_amount = pair_weight * capital
        logging.info(
            f"{current_time} - custom_stake_amount - {pair} "
            f"pair_weight: {pair_weight:.03f}, "
            f"stake_amount: {stake_amount:.08f}")
        return stake_amount

    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float,
                              min_stake: Optional[float], max_stake: float,
                              current_entry_rate: float, current_exit_rate: float,
                              current_entry_profit: float, current_exit_profit: float,
                              **kwargs
                              ) -> Union[Optional[float], Tuple[Optional[float], Optional[str]]]:
        tf_minutes = timeframe_to_minutes(self.timeframe)
        trade_date = max(t.date_last_filled_utc for t in Trade.get_trades_proxy(is_open=True))
        trade_dur = int((current_time - trade_date).total_seconds() // 60)
        if trade_dur < self.rebalance_candle.value * tf_minutes:
            return None

        weights = self.calculate_weights()
        pair_weight = weights.get(trade.pair, 0.0)
        if pair_weight <= 0:
            return -trade.stake_amount

        capital = self.wallets.get_total_stake_amount()
        pair_allocation = pair_weight * capital
        adjustment_amount = pair_allocation - trade.stake_amount
        logging.info(
            f"{current_time} - adjust_trade_position - {trade.pair} - "
            f"pair_weight: {pair_weight:.03f}, "
            f"trade_stake_amount: {trade.stake_amount:.08f}, "
            f"adjustment_amount: {adjustment_amount:.08f}, "
            f"capital: {capital:.08f}")
        return adjustment_amount

    def calculate_weights(self) -> Dict:
        data = {}

        for pair in self.selected_pairs:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            data[pair] = dataframe.iloc[-self.startup_candle_count:]["rsi"]
        returns = DataFrame(data).pct_change().dropna()

        portfolio = rp.HCPortfolio(returns=returns)
        weights = portfolio.optimization(
            model="HRP",
            codependence="pearson",
            rm=self.risk_measure.value,
            rf=0,
            linkage="single",
            max_k=10,
            leaf_order=True,
        )
        weights = weights["weights"].to_dict()
        return weights
