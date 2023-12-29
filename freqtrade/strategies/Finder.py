import numpy as np
import pandas as pd
import talib.abstract as ta
import pandas_ta as pta
from itertools import product
from functools import reduce
from pandas import DataFrame, Series
from datetime import datetime
from typing import Any, Dict, List
from freqtrade.constants import Config
from freqtrade.strategy import BooleanParameter, CategoricalParameter, IStrategy
from freqtrade.optimize.space import Categorical, SKDecimal, Dimension


class Finder(IStrategy):
    INTERFACE_VERSION = 3
    process_only_new_candles = True
    can_short = False
    stoploss = -0.20
    minimal_roi = {"0": 0.30}
    max_open_trades = 10
    trailing_stop = False
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True
    use_custom_stoploss = False
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    ignore_buying_expired_candle_after = 300
    timeframe = "4h"
    NUM_RULES = 2
    SIDES = ["buy", "sell"]

    class HyperOpt:
        def stoploss_space() -> List[Dimension]:
            return [SKDecimal(-0.30, -0.01, decimals=2, name="stoploss")]

        def roi_space() -> List[Dimension]:
            return [SKDecimal(0.01, 0.30, decimals=2, name="roi")]

        def generate_roi_table(p: Dict) -> Dict[int, float]:
            return {0: p["roi"]}

        def max_open_trades_space() -> List[Dimension]:
            return [Categorical(range(5, 10, 1), name="max_open_trades")]

    def __init__(self, config: Config):
        super().__init__(config)
        self.config = config
        self._initialize_parameters()

    def _initialize_parameters(self):
        INDICATORS = """
        upperband lowerband macd macdsignal slowk slowd fastk fastd
        dema ema kama midpoint midprice sar sma t3 tema trima wma
        adx aroonosc cci cmo mfi mom roc rsi trix willr
        atr natr
        supertrend
        """.split()

        OPERATORS = [
            "DISABLED",
            "GOING_UP",
            "GOING_DOWN",
            "RISING",
            "FALLING",
            "ABOVE_AVERAGED",
            "BELOW_AVERAGED",
        ]
        PERIOD_RANGE = list(range(3, 15)) + list(range(15, 55, 5))
        SHIFT_RANGE = range(0, 12, 2)
        DOW_RANGE = range(0, 7)

        for side in self.SIDES:
            for idx in range(self.NUM_RULES):
                setattr(self, f"{side}_{idx}_indicator",
                    CategoricalParameter(INDICATORS, default="sma", space=side),
                )
                setattr(self, f"{side}_{idx}_period",
                    CategoricalParameter(PERIOD_RANGE, default=10, space=side),
                )
                setattr(self, f"{side}_{idx}_shift",
                    CategoricalParameter(SHIFT_RANGE, default=0, space=side),
                )
                setattr(self, f"{side}_{idx}_operator",
                    CategoricalParameter(OPERATORS, default="DISABLED", space=side),
                )
            setattr(self, f"{side}_min_dow", 
                CategoricalParameter(DOW_RANGE, default=0, space=side))
            setattr(self, f"{side}_max_dow", 
                CategoricalParameter(DOW_RANGE, default=0, space=side))

    def _is_rule_disabled(self, side: str, idx: int) -> bool:
        return getattr(self, f"{side}_{idx}_operator").value == "DISABLED"

    def _get_rule_parameters(self, side: str, idx: int):
        ind = getattr(self, f"{side}_{idx}_indicator").value
        prd = int(getattr(self, f"{side}_{idx}_period").value)
        sft = int(getattr(self, f"{side}_{idx}_shift").value)
        return ind, prd, sft

    def _calculate_indicator(self, dataframe, indicator, period):
        indicator_mapping = {
            "upperband": "bbands",
            "lowerband": "bbands",
            "macd": "macd",
            "macdsignal": "macd",
            "slowk": "stoch",
            "slowd": "stoch",
            "fastk": "stochf",
            "fastd": "stochf",
        }

        if indicator in indicator_mapping:
            ta_func = getattr(ta, indicator_mapping[indicator].upper())
            result = ta_func(dataframe, timeperiod=period)
            result = result[indicator]
        elif indicator == "supertrend":
            result = pta.supertrend(
                dataframe["high"], dataframe["low"], dataframe["close"], length=period
            )[f"SUPERT_{period}_3.0"]
        else:
            ta_func = getattr(ta, indicator.upper())
            result = ta_func(dataframe, timeperiod=period)

        return pd.Series(result)

    def _apply_operator(self, series, side, idx, shift):
        operator = getattr(self, f"{side}_{idx}_operator").value
        averaged = pd.Series(ta.EMA(series, timeperiod=10))
        shifted = series.shift(shift)

        if operator in ["ABOVE_AVERAGED", "BELOW_AVERAGED"]:
            comparison = (
                series > averaged.shift(shift)
                if operator == "ABOVE_AVERAGED"
                else series < averaged.shift(shift)
            )
            return comparison

        value0, value1, value2 = shifted, shifted.shift(1), shifted.shift(2)

        comparison_operators = {
            "GOING_UP": (value0 > value1) & (value1 < value2),
            "GOING_DOWN": (value0 < value1) & (value1 > value2),
            "RISING": (value0 > value1) & (value1 > value2),
            "FALLING": (value0 < value1) & (value1 < value2),
        }

        return comparison_operators.get(operator, pd.Series(False, index=series.index))

    def _apply_dow_conditions(self, dataframe, side):
        min_dow = getattr(self, f"{side}_min_dow").value
        max_dow = getattr(self, f"{side}_max_dow").value
        if min_dow < max_dow:
            return [(dataframe["dow"] >= min_dow) & (dataframe["dow"] <= max_dow)]
        else:
            return [(dataframe["dow"] <= min_dow) & (dataframe["dow"] >= max_dow)]

    def _populate_trend(self, dataframe: pd.DataFrame, side: str) -> pd.DataFrame:
        conditions = []

        for idx in range(self.NUM_RULES):
            if self._is_rule_disabled(side, idx):
                continue

            indicator, period, shift = self._get_rule_parameters(side, idx)
            result = self._calculate_indicator(dataframe, indicator, period)
            conditions.append(self._apply_operator(result, side, idx, shift))

        conditions.append(dataframe["volume"] > 0)
        conditions.extend(self._apply_dow_conditions(dataframe, side))

        return conditions

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["dow"] = dataframe["date"].dt.dayofweek
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = self._populate_trend(dataframe, "buy")
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = self._populate_trend(dataframe, "sell")
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), "exit_long"] = 1
        return dataframe
