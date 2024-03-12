import itertools
import logging
import warnings

from datetime import datetime, timedelta
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union

import numpy as np
import talib.abstract as ta
from freqtrade.constants import Config
from freqtrade.exchange import timeframe_to_prev_date
from freqtrade.strategy import BooleanParameter, CategoricalParameter, IStrategy
from pandas import DataFrame, Series

# Simply ignore warning about h5py not installed
from tslearn.clustering import TimeSeriesKMeans
from tslearn.preprocessing import TimeSeriesScalerMeanVariance

logger = logging.getLogger(__name__)


class DisableLogger:
    def __enter__(self):
        logging.disable(logging.CRITICAL)

    def __exit__(self, exit_type, exit_value, exit_traceback):
        logging.disable(logging.NOTSET)


class RotatorTSLearnStrategy(IStrategy):
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

    roc_period = CategoricalParameter(range(5, 50, 2), default=29, space="buy")
    pair_threshold = CategoricalParameter(range(2, 20, 2), default=6, space="buy")
    cooldown_lookback = CategoricalParameter(
        range(2, 48, 2), default=10, space="protection"
    )
    stop_duration = CategoricalParameter(
        range(2, 200, 2), default=100, space="protection"
    )
    use_stop_protection = BooleanParameter(default=True, space="protection")

    top_pairs: List = []

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.config = config

    @property
    def protections(self):
        prot = []

        prot.append(
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": self.cooldown_lookback.value,
            }
        )
        if self.use_stop_protection.value:
            prot.append(
                {
                    "method": "StoplossGuard",
                    "lookback_period_candles": 24 * 3,
                    "trade_limit": 4,
                    "stop_duration_candles": self.stop_duration.value,
                    "only_per_pair": False,
                }
            )

        return prot

    def populate_indicators(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        dataframe["roc"] = ta.ROC(dataframe, timeperiod=self.roc_period.value)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        dataframe[["enter_long", "enter_tag"]] = (1, "always_enter")
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
            # data[pair] = dataframe["roc"].iat[-1]
            data[pair] = dataframe["roc"].iloc[-50:]

        if not data:
            return

        # CLUSTERING
        df = DataFrame(data)
        df = df.dropna()

        with DisableLogger():
            X = TimeSeriesScalerMeanVariance().fit_transform(df.T)
            n = self.pair_threshold.value
            km = TimeSeriesKMeans(n_clusters=n, verbose=False)
            clusters = km.fit_predict(X)

        top_pairs = []
        for key, group in itertools.groupby(
            sorted(zip(clusters, df.columns)), lambda x: x[0]
        ):
            group_pairs = sorted(
                [(x[1], df[x[1]].iat[-1]) for x in list(group)],
                key=lambda x: x[1],
                reverse=True,
            )
            top_pairs.append(group_pairs[0][0])
        self.top_pairs = top_pairs

    def confirm_trade_entry(self, pair: str, *args, **kwargs) -> bool:
        if pair not in self.top_pairs:
            return False
        return True

    def custom_exit(self, pair: str, *args, **kwargs):
        if pair not in self.top_pairs:
            return "exit_trade"
