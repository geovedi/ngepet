import numpy as np
import pandas as pd
import talib.abstract as ta
from functools import reduce
from freqtrade.constants import Config
from freqtrade.optimize.space import SKDecimal, Dimension
from freqtrade.strategy import CategoricalParameter, BooleanParameter
from freqtrade.strategy.interface import IStrategy
from freqtrade.vendor.qtpylib.indicators import crossed_above, crossed_below
from pandas import DataFrame, Series
from typing import Any, Dict, List


def to_numeric_safe(series: Series, fill_value: float) -> Series:
    return pd.to_numeric(series, errors="coerce").fillna(fill_value)


is_rising = lambda s, n: (s.diff() > 0).rolling(n).sum() == n
is_falling = lambda s, n: (s.diff() < 0).rolling(n).sum() == n


class TryEverything(IStrategy):
    INTERFACE_VERSION = 3
    RULES_SIZE = 2
    minimal_roi = {}
    stoploss = -0.03
    timeframe = "1h"
    use_custom_stoploss = True
    startup_candle_count = 100

    class HyperOpt:
        @staticmethod
        def stoploss_space() -> List[Dimension]:
            return [SKDecimal(-0.30, -0.01, decimals=2, name="stoploss")]

        @staticmethod
        def roi_space() -> List[Dimension]:
            return [SKDecimal(0.02, 0.30, decimals=2, name="roi")]

        @staticmethod
        def generate_roi_table(p: Dict) -> Dict[int, float]:
            return {0: p["roi"]}

    def __init__(self, config: Config):
        super().__init__(config)
        self.config = config
        self.initialize_parameters()

    def initialize_parameters(self):
        default_indicators = {"buy": "upperband", "sell": "lowerband"}
        for side in default_indicators:
            self.define_parameters_for_side(side, default_indicators[side])

    def create_categorical_parameter(self, name, categories, default, space):
        setattr(self, name, CategoricalParameter(categories, default=default, space=space))

    def create_boolean_parameter(self, name, default, space):
        setattr(self, name, BooleanParameter(default=default, space=space))

    def define_parameters_for_side(self, side: str, default_indicator: str):
        indicators = (
            "upperband middleband lowerband mama fama aroondown aroonup "
            "macd macdsignal macdhist slowk slowd fastk fastd ad adosc "
            "adx adxr apo aroonosc atr bop cci cmo dema dx ema "
            "ht_trendline kama ma mfi minus_di minus_dm mom obv "
            "plus_di plus_dm ppo roc rocp rsi sar sarext sma tema trima "
            "trix ultosc willr wma"
        ).split()
        operation_types = "disabled crossed_above crossed_below raising falling".split()
        price_types = "open high low close avgprice medprice typprice wclprice".split()
        shifts = range(0, 10, 2)  # Shifts range

        for rule_index in range(self.RULES_SIZE):
            self.create_categorical_parameter(
                f"{side}_indicator_{rule_index}", indicators, default_indicator, side
            )
            self.create_categorical_parameter(
                f"{side}_operator_{rule_index}", operation_types, "disabled", side
            )
            self.create_categorical_parameter(f"{side}_shift_{rule_index}", shifts, 0, side)
            self.create_categorical_parameter(
                f"{side}_pricetype_{rule_index}", price_types, "close", side
            )
            self.create_boolean_parameter(f"{side}_useprice_{rule_index}", False, side)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        multiple_output_indicators = {
            "BBANDS": ("upperband", "middleband", "lowerband"),
            "MAMA": ("mama", "fama"),
            "AROON": ("aroondown", "aroonup"),
            "MACD": ("macd", "macdsignal", "macdhist"),
            "STOCH": ("slowk", "slowd"),
            "STOCHF": ("fastk", "fastd"),
        }
        single_output_indicators = (
            "AD ADOSC ADX ADXR APO AROONOSC ATR BOP CCI CMO DEMA DX EMA "
            "HT_TRENDLINE KAMA MA MFI MINUS_DI MINUS_DM MOM OBV "
            "PLUS_DI PLUS_DM PPO ROC ROCP RSI SAR SAREXT SMA TEMA TRIMA "
            "TRIX ULTOSC WILLR WMA AVGPRICE MEDPRICE TYPPRICE WCLPRICE"
        ).split()

        for indicator_name, columns in multiple_output_indicators.items():
            indicator_result = getattr(ta, indicator_name)(dataframe)
            for column in columns:
                dataframe[column] = indicator_result[column]

        for indicator_name in single_output_indicators:
            dataframe[indicator_name.lower()] = getattr(ta, indicator_name)(dataframe)

        return dataframe

    def populate_trend(self, dataframe: DataFrame, trend_side: str) -> DataFrame:
        conditions = []

        for rule_index in range(self.RULES_SIZE):
            operator = getattr(self, f"{trend_side}_operator_{rule_index}").value
            if operator == "disabled":
                continue

            indicator_name = getattr(self, f"{trend_side}_indicator_{rule_index}").value
            shift_value = getattr(self, f"{trend_side}_shift_{rule_index}").value
            use_price = getattr(self, f"{trend_side}_useprice_{rule_index}").value
            price_type = getattr(self, f"{trend_side}_pricetype_{rule_index}").value

            series = dataframe[price_type] if use_price else dataframe[indicator_name]
            shifted_series = series.shift(shift_value)

            infinite_value = -np.inf if operator == "crossed_above" else np.inf
            compare_function = crossed_above if operator == "crossed_above" else crossed_below
            if operator in ["crossed_above", "crossed_below"]:
                conditions.append(
                    compare_function(
                        to_numeric_safe(series, infinite_value),
                        to_numeric_safe(shifted_series, infinite_value),
                    )
                )
            elif operator == "raising":
                conditions.append(is_rising(series, shift_value + 1))
            elif operator == "falling":
                conditions.append(is_falling(series, shift_value + 1))

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
