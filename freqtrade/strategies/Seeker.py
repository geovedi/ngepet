import numpy as np
import pandas as pd
import talib.abstract as ta

from functools import reduce
from pandas import DataFrame, Series
from datetime import datetime
from typing import Any, Dict, List
from freqtrade.constants import Config
from freqtrade.strategy import BooleanParameter, CategoricalParameter, IStrategy
from freqtrade.optimize.space import Categorical, SKDecimal, Dimension


class Seeker(IStrategy):
    INTERFACE_VERSION = 3
    process_only_new_candles = True
    can_short: False
    stoploss = -0.06
    minimal_roi = {"0": 0.1}
    trailing_stop = False
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True
    use_custom_stoploss = False
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    timeframe = "4h"
    NUM_RULES = 2

    class HyperOpt:
        def stoploss_space() -> List[Dimension]:
            return [SKDecimal(-0.20, -0.02, decimals=2, name="stoploss")]

        def roi_space() -> List[Dimension]:
            return [SKDecimal(0.03, 0.30, decimals=2, name="roi")]

        def generate_roi_table(p: Dict) -> Dict[int, float]:
            return {0: p["roi"]}
        
        def max_open_trades_space() -> List[Dimension]:
            return [Categorical(range(5, 20, 5), name="max_open_trades")]

    def __init__(self, config: Config):
        super().__init__(config)
        self.config = config
        self.initialize_parameters()

    def compare_series(self, series1: Series, series2: Series, shift: int = 0, comparison: str = "CROSS_UP") -> bool:
        value1 = series1.shift(shift + 1)
        value2 = series2.shift(shift + 1)
        value3 = series1.shift(shift)
        value4 = series2.shift(shift)

        if comparison == "CROSS_UP":
            return (value1 < value2) & (value3 > value4)
        elif comparison == "CROSS_DOWN":
            return (value1 > value2) & (value3 < value4)
        elif comparison == "GREATER_THAN":
            return series1.shift(shift) > series2.shift(shift)
        elif comparison == "LESSER_THAN":
            return series1.shift(shift) < series2.shift(shift)
        elif comparison == "RAISING":
            return value1 < value3
        elif comparison == "FALLING":
            return value1 > value3
        return False

    def initialize_parameters(self):
        SERIES = """upperband lowerband macd macdsignal slowk slowd fastk fastd
        adx atr cci ema mom roc rsi sma
        close volume
        """.split()
        OPERATORS = ["DISABLED", "CROSS_UP", "CROSS_DOWN", "GREATER_THAN", "LESSER_THAN", "RAISING", "FALLING"]
        SHIFT_RANGE = range(0, 10, 2)
        SMOOTH_RANGE = range(5, 50, 5)

        setattr(self, "smooth", CategoricalParameter(SMOOTH_RANGE, default=5, space="buy"))

        for idx in range(self.NUM_RULES):
            for side in ["buy", "sell"]:
                setattr(self, f"{side}_{idx}_series", CategoricalParameter(SERIES, default="sma", space=side))
                setattr(self, f"{side}_{idx}_operator", CategoricalParameter(OPERATORS, default="DISABLED", space=side))
                setattr(self, f"{side}_{idx}_shift", CategoricalParameter(SHIFT_RANGE, default=0, space=side))

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        multiple_output_indicators = {
            "BBANDS": ("upperband", "lowerband"),
            "MACD": ("macd", "macdsignal"),
            "STOCH": ("slowk", "slowd"),
            "STOCHF": ("fastk", "fastd"),
        }

        single_output_indicators = """ADX ATR CCI EMA MOM ROC RSI SMA""".split()
        smooth = self.smooth.value

        for indicator_name, columns in multiple_output_indicators.items():
            indicator_result = getattr(ta, indicator_name)(dataframe)
            for column in columns:
                dataframe[column] = indicator_result[column]
                dataframe[f"{column}_smooth"] = ta.SMA(dataframe[column], timeperiod=smooth)

        for indicator_name in single_output_indicators:
            column = indicator_name.lower()
            dataframe[column] = getattr(ta, indicator_name)(dataframe)
            dataframe[f"{column}_smooth"] = ta.SMA(dataframe[column], timeperiod=smooth)

        for column in "close volume".split():
            dataframe[f"{column}_smooth"] = ta.SMA(dataframe[column], timeperiod=smooth)

        return dataframe

    def populate_trend(self, dataframe: DataFrame, side: str) -> DataFrame:
        conditions = []

        for idx in range(self.NUM_RULES):
            operator = getattr(self, f"{side}_{idx}_operator").value
            indicator = getattr(self, f"{side}_{idx}_series").value
            shift = getattr(self, f"{side}_{idx}_shift").value

            left = dataframe[f"{indicator}"]
            right = dataframe[f"{indicator}_smooth"]

            if operator != "DISABLED":
                conditions.append(self.compare_series(left, right, shift, operator))

        conditions.append(dataframe["volume"] > 0)
        return conditions

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = self.populate_trend(dataframe, "buy")
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = self.populate_trend(dataframe, "sell")
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), "exit_long"] = 1
        return dataframe

