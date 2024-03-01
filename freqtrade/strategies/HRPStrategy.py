import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union

import numpy as np
import riskfolio as rp
from freqtrade.persistence import Trade
from freqtrade.strategy import CategoricalParameter, IntParameter, IStrategy
from pandas import DataFrame, Series

logger = logging.getLogger(__name__)

# fmt: on
RISK_MEASURES = ["vol", "MV", "MAD", "GMD", "MSV", "FLPM", "SLPM", "VaR", "CVaR",
    "TG", "EVaR", "WR", "RG", "CVRG", "TGRG", "MDD", "ADD", "DaR", "CDaR", "EDaR",
    "UCI", "MDD_Rel", "ADD_Rel", "DaR_Rel", "CDaR_Rel", "EDaR_Rel", "UCI_Rel",
]
REBALANCE_MINUTES = [240, 1440, 2880, 4320, 10080, 20160, 30240, 43200]
# fmt: off


class HRPStrategy(IStrategy):
    INTERFACE_VERSION: int = 3
    timeframe: str = "4h"
    can_short: bool = False
    process_only_new_candles: bool = False
    use_exit_signal: bool = False
    ignore_buying_expired_candle_after: int = 600
    startup_candle_count: int = 1000
    position_adjustment_enable: bool = True

    minimal_roi: Dict[str, float] = {}
    stoploss: float = -1.0

    entry_dayofweek = IntParameter(0, 7, default=0, space="buy")
    risk_measure = CategoricalParameter(RISK_MEASURES, default="MV", space="buy")
    rebalance_minute = CategoricalParameter(REBALANCE_MINUTES, default=1440, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        dataframe["dayofweek"] = dataframe["date"].dt.dayofweek
        dataframe["hour"] = dataframe["date"].dt.hour
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        dataframe.loc[
            ((dataframe["dayofweek"] == self.entry_dayofweek.value)),
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
        pair_weight = weights.get(pair, )
        capital = self.wallets.get_total_stake_amount()
        stake_amount = pair_weight * capital
        logging.info(
            f"{current_time} - custom_stake_amount - {pair} weight: {pair_weight}, "
            f"stake_amount: {stake_amount}")
        return stake_amount

    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float,
                              min_stake: Optional[float], max_stake: float,
                              current_entry_rate: float, current_exit_rate: float,
                              current_entry_profit: float, current_exit_profit: float,
                              **kwargs
                              ) -> Union[Optional[float], Tuple[Optional[float], Optional[str]]]:
        trade_dur = int((current_time - trade.date_last_filled_utc).total_seconds() // 60)
        if trade_dur < self.rebalance_minute.value:
            logging.info(f"{current_time} - adjust_trade_position - {trade.pair} - SKIP")
            return None

        weights = self.calculate_weights()
        pair_weight = weights.get(trade.pair, 0.0)
        capital = self.wallets.get_total_stake_amount()
        pair_allocation = pair_weight * capital
        allocation_delta = pair_allocation - trade.stake_amount
        logging.info(
            f"{current_time} - adjust_trade_position - {trade.pair} "
            f"allocation_delta: {allocation_delta}, pair_weight: {pair_weight}, "
            f"capital: {capital}")
        return allocation_delta

    def calculate_weights(self) -> Dict:
        data = {}
        pairs = self.config["exchange"]["pair_whitelist"]
        for pair in pairs:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            data[pair] = dataframe.iloc[-self.startup_candle_count:]["close"]
        returns = DataFrame(data).pct_change().dropna()

        portfolio = rp.HCPortfolio(returns=returns)
        model = "HRP"
        codependence = "pearson"
        risk_measure = self.risk_measure.value
        risk_free = 0
        linkage = "single"
        max_n_cluster = 10
        leaf_order = True

        weights = portfolio.optimization(
            model=model,
            codependence=codependence,
            rm=risk_measure,
            rf=risk_free,
            linkage=linkage,
            max_k=max_n_cluster,
            leaf_order=leaf_order,
        )
        weights = weights["weights"].round(2).to_dict() # might have ZERO weight
        return weights
