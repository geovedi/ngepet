import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union

import numpy as np
import talib.abstract as ta
from freqtrade.constants import Config
from freqtrade.exchange import timeframe_to_prev_date
from freqtrade.strategy import CategoricalParameter, IStrategy
from pandas import DataFrame, Series

logger = logging.getLogger(__name__)


class Rotator(IStrategy):
    INTERFACE_VERSION: int = 3
    timeframe: str = "1d"
    can_short: bool = False
    process_only_new_candles: bool = True
    use_exit_signal: bool = True
    ignore_buying_expired_candle_after: int = 600
    startup_candle_count: int = 100
    minimal_roi: Dict[str, float] = {}
    stoploss: float = -1.0
    max_open_trades: int = 5

    roc_period = CategoricalParameter(range(5, 30, 2), default=20, space="buy")
    pair_threshold = CategoricalParameter(range(2, 10, 2), default=6, space="buy")

    top_pairs: List = []

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.config = config

    def populate_indicators(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        dataframe["roc"] = ta.ROC(dataframe, timeperiod=self.roc_period.value)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        dataframe["enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        return dataframe

    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        prev_candle_time = timeframe_to_prev_date(self.timeframe, current_time)
        if (current_time - prev_candle_time) >= timedelta(minutes=5):
           return

        data = {}
        for pair in self.config["exchange"]["pair_whitelist"]:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if dataframe.empty:
                continue
            data[pair] = dataframe["roc"].iat[-1]

        if not data:
            return

        data = sorted(data.items(), key=lambda x: x[1], reverse=True)
        self.top_pairs = [p[0] for p in data[: self.pair_threshold.value]]
        logging.info(f"{current_time} -- bot_loop_start -- Top Pair: {self.top_pairs}")
        logging.info(f"{current_time} -- bot_loop_start -- Wallet: {self.wallets.get_total_stake_amount()}")

    def confirm_trade_entry(self, pair: str, *args, **kwargs) -> bool:
        if pair not in self.top_pairs:
            return False
        return True

    def custom_exit(self, pair: str, *args, **kwargs):
        if pair not in self.top_pairs:
            return "out"
