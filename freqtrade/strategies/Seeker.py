import numpy as np
import pandas as pd
import talib.abstract as ta
import pandas_ta as pta

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
    can_short = False
    stoploss = -0.20
    minimal_roi = {"0": 0.15, "10080": 0}
    max_open_trades = 10
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
    SIDES = ["buy", "sell"]

    class HyperOpt:
        def stoploss_space() -> List[Dimension]:
            return [SKDecimal(-0.20, -0.05, decimals=2, name="stoploss")]

        def roi_space() -> List[Dimension]:
            return [SKDecimal(0.05, 0.30, decimals=2, name="roi")]

        def generate_roi_table(p: Dict) -> Dict[int, float]:
            return {0: p["roi"], 10080: 0}

        def max_open_trades_space() -> List[Dimension]:
            return [Categorical(range(5, 10, 1), name="max_open_trades")]

    def __init__(self, config: Config):
        super().__init__(config)
        self.config = config
        self.initialize_parameters()

    def compare_series(
        self,
        series1: Series,
        series2: Series,
        shift: int = 0,
        comparison: str = "CROSS_UP",
    ) -> bool:
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
        adx atr cci mom roc rsi supertrend
        close volume
        """.split()
        OPERATORS = [
            "DISABLED",
            "CROSS_UP",
            "CROSS_DOWN",
            "GREATER_THAN",
            "LESSER_THAN",
            "RAISING",
            "FALLING",
        ]
        SHIFT_RANGE = range(0, 20, 2)
        SMOOTH_RANGE = range(5, 100, 5)
        # HOUR_RANGE = range(0, 24)

        setattr(
            self, "smooth", CategoricalParameter(SMOOTH_RANGE, default=5, space="buy")
        )
        # setattr(
        #    self, "min_hour", CategoricalParameter(HOUR_RANGE, default=0, space="buy")
        # )
        # setattr(
        #    self, "max_hour", CategoricalParameter(HOUR_RANGE, default=0, space="buy")
        # )

        for side in self.SIDES:
            for idx in range(self.NUM_RULES):
                setattr(
                    self,
                    f"{side}_{idx}_series",
                    CategoricalParameter(SERIES, default="close", space=side),
                )
                setattr(
                    self,
                    f"{side}_{idx}_operator",
                    CategoricalParameter(OPERATORS, default="DISABLED", space=side),
                )
                setattr(
                    self,
                    f"{side}_{idx}_shift",
                    CategoricalParameter(SHIFT_RANGE, default=0, space=side),
                )

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        multiple_output_indicators = {
            "bbands": ("upperband", "lowerband"),
            "macd": ("macd", "macdsignal"),
            "stoch": ("slowk", "slowd"),
            "stochf": ("fastk", "fastd"),
        }
        single_output_indicators = """adx atr cci mom roc rsi""".split()
        smoothed_columns = "close volume supertrend".split()

        for indicator, columns in multiple_output_indicators.items():
            result = getattr(ta, indicator.upper())(dataframe)
            for column in columns:
                dataframe[column] = result[column]
                smoothed_columns.append(column)

        for indicator in single_output_indicators:
            column = indicator
            dataframe[column] = getattr(ta, indicator.upper())(dataframe)
            smoothed_columns.append(column)

        # PTA
        st = pta.supertrend(dataframe["high"], dataframe["low"], dataframe["close"])
        dataframe["supertrend"] = st["SUPERT_7_3.0"]

        smoothed = {}
        for column in smoothed_columns:
            for val in self.smooth.range:
                column_name = f"{column}_smooth_{val}"
                smoothed[column_name] = ta.EMA(dataframe[column], timeperiod=val)

        dataframe = pd.concat([dataframe, pd.DataFrame(smoothed)], axis=1)

        return dataframe

    def populate_trend(self, dataframe: DataFrame, side: str) -> DataFrame:
        conditions = []

        for idx in range(self.NUM_RULES):
            operator = getattr(self, f"{side}_{idx}_operator").value
            indicator = getattr(self, f"{side}_{idx}_series").value
            shift = getattr(self, f"{side}_{idx}_shift").value

            left = dataframe[f"{indicator}"]
            right = dataframe[f"{indicator}_smooth_{self.smooth.value}"]

            if operator != "DISABLED":
                conditions.append(self.compare_series(left, right, shift, operator))

        if conditions:
            conditions.append(dataframe["volume"] > 0)
        return conditions

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = self.populate_trend(dataframe, "buy")
        if conditions:
            # max_hour = self.max_hour.value
            # min_hour = self.min_hour.value
            # data_hour = dataframe["date"].dt.hour
            # if min_hour < max_hour:
            #    conditions.append((data_hour >= min_hour) & (data_hour < max_hour))
            # else:
            #    conditions.append((data_hour < min_hour) & (data_hour >= max_hour))
            dataframe.loc[reduce(lambda x, y: x & y, conditions), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if "sell" in self.SIDES:
            conditions = self.populate_trend(dataframe, "sell")
            if conditions:
                dataframe.loc[reduce(lambda x, y: x & y, conditions), "exit_long"] = 1
        return dataframe
