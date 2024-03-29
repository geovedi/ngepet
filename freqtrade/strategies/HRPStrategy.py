# EXPERIMENTAL CODE
# $ freqtrade hyperopt --userdir user_data \
#    --config user_data/config.json --config user_data/HRPStrategy-pairs.json \
#    --strategy HRPStrategy --timerange 20230101- --spaces buy sell \
#    --epochs 1024 --print-all --disable-param-export \
#    --hyperopt-loss CalmarHyperOptLoss --timeframe-detail 1h



import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union

import numpy as np
import riskfolio as rp
import talib.abstract as ta
from freqtrade.constants import Config
from freqtrade.exchange import timeframe_to_minutes, timeframe_to_prev_date
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
    timeframe: str = "4h"
    can_short: bool = False
    process_only_new_candles: bool = True
    use_exit_signal: bool = True
    ignore_buying_expired_candle_after: int = 600
    position_adjustment_enable: bool = True
    startup_candle_count: int = 500
    minimal_roi: Dict[str, float] = {}
    stoploss: float = -1.0

    entry_dayofweek = IntParameter(0, 6, default=0, space="buy")
    rebalance_candle = CategoricalParameter(range(50, 351, 50), default=100, space="buy")
    history_length = CategoricalParameter(range(100, 501, 100), default=200, space="buy")
    risk_measure = CategoricalParameter(RISK_MEASURES, default="MV", space="buy", optimize=False)
    
    custom_stop_loss = CategoricalParameter(
        np.arange(-0.5, 0, 0.025).round(3),
        default=-0.5, space="sell"
    )
    custom_trailing_stop = CategoricalParameter(
        np.arange(0.025, 0.175, 0.025).round(3),
        default=0.05, space="sell"
    )
    custom_trailing_offset = CategoricalParameter(
        np.arange(0.125, 0.225, 0.025).round(3),
        default=0.2, space="sell"
    )

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.config = config
    
        for idx in range(self.config["max_open_trades"]):
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
        pairs = [getattr(self, f"pair_{i:02d}").value for i in range(self.max_open_trades)]
        if len(set(pairs)) < self.max_open_trades:
            return []
        return pairs

    def populate_indicators(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        dataframe["dayofweek"] = dataframe["date"].dt.dayofweek
        dataframe["hour"] = dataframe["date"].dt.hour
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

    def is_fresh_candle(self, current_time: datetime, delta_minutes: int = 5) -> bool:
        prev_candle_time = timeframe_to_prev_date(self.timeframe, current_time)
        if (current_time - prev_candle_time) >= timedelta(minutes=delta_minutes):
            return False
        return True

    def confirm_trade_exit(self, pair: str, trade: Trade, order_type: str, amount: float,
                           rate: float, time_in_force: str, exit_reason: str,
                           current_time: datetime, **kwargs) -> bool:
        if not self.is_fresh_candle(current_time):
            return False
        return True

    def custom_exit(self, pair: str, trade: "Trade", current_time: "datetime", current_rate: float,
                    current_profit: float, **kwargs):
        if not self.is_fresh_candle(current_time):
            return None

        dataframe, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
        current_candle = dataframe.iloc[-1].squeeze()
        current_rate = current_candle["close"]
        current_profit = trade.calc_profit_ratio(current_rate)

        if current_profit < self.custom_stop_loss.value:
            logging.info(
                f"{current_time} - custom_exit - {pair} - "
                f"stop_loss with current_profit: {current_profit:.08f}"
            )
            return "custom_stop_loss"

        max_rate = trade.min_rate if trade.is_short else trade.max_rate
        max_profit = trade.calc_profit_ratio(max_rate)

        if not max_profit > self.custom_trailing_offset.value:
            return None

        if (max_profit - current_profit) < self.custom_trailing_stop.value:
            logging.info(
                f"{current_time} - custom_exit - {pair} - "
                f"trailing stop with current_profit: {current_profit:.08f}"
            )
            return "custom_trailing_stop"

        return None

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: Optional[float], max_stake: float,
                            leverage: float, entry_tag: Optional[str], side: str,
                            **kwargs) -> float:
        weights = self.calculate_weights()
        pair_weight = weights.get(pair, 0.0)
        if pair_weight == 0:
            return 0.0

        capital = self.wallets.get_total_stake_amount()
        stake_amount = pair_weight * capital
        logging.info(
            f"{current_time} - custom_stake_amount - {pair} - "
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

        if not self.selected_pairs:
            return {}

        for pair in self.selected_pairs:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            data[pair] = dataframe.iloc[-self.startup_candle_count:]["close"]
        returns = DataFrame(data).pct_change(fill_method=None).dropna()

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
