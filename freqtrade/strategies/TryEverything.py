import numpy as np
import pandas as pd
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

from functools import reduce
from freqtrade.constants import Config
from freqtrade.optimize.space import SKDecimal
from freqtrade.strategy import CategoricalParameter, BooleanParameter
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame


def to_safe_numeric(series, fill_value):
    return pd.to_numeric(series, errors="coerce").fillna(fill_value)


def is_rising(series, n):
    if not isinstance(n, int) or n <= 0:
        raise ValueError("'n' must be a positive integer.")
    if not pd.api.types.is_numeric_dtype(series):
        raise TypeError("Series must contain numeric data.")

    differences = series.diff()
    is_rising = differences > 0
    rising_streaks = is_rising.rolling(window=n).sum() == n
    return rising_streaks.shift(-(n - 1)).fillna(False)


def is_falling(series, n):
    if not isinstance(n, int) or n <= 0:
        raise ValueError("'n' must be a positive integer.")
    if not pd.api.types.is_numeric_dtype(series):
        raise TypeError("Series must contain numeric data.")

    differences = series.diff()
    is_falling = differences < 0
    falling_streaks = is_falling.rolling(window=n).sum() == n
    return falling_streaks.shift(-(n - 1)).fillna(False)


class TryEverything(IStrategy):
    INTERFACE_VERSION = 3
    RULES_SIZE = 2
    minimal_roi = {}
    stoploss = -0.03
    timeframe = "1h"
    use_custom_stoploss = True
    startup_candle_count = 100

    # Define a dictionary of parameter spaces for hyperopt optimization
    class HyperOpt:
        @staticmethod
        def stoploss_space() -> list:
            return [SKDecimal(-0.30, -0.01, decimals=2, name="stoploss")]

        @staticmethod
        def roi_space() -> list:
            return [SKDecimal(0.02, 0.30, decimals=2, name="roi")]

        @staticmethod
        def generate_roi_table(params: dict) -> dict:
            return {0: params["roi"]}

    # Initialize parameters for buying and selling
    def __init__(self, config: Config):
        super().__init__(config)
        self.config = config
        self._initialize_parameters()

    def _initialize_parameters(self):
        self._define_parameters_for_side("buy", "bband_upper")
        self._define_parameters_for_side("sell", "bband_lower")

    def _define_parameters_for_side(self, side: str, default_indicator: str):
        indicators = [
            # Multiple output indicators
            "upperband", "middleband", "lowerband",
            "mama", "fama",
            "aroondown", "aroonup",
            "macd", "macdsignal", "macdhist",
            "slowk", "slowd",
            "fastk", "fastd",
            # Single output indicators
            "adx", "adxr", "apo", "aroonosc", "atr", "bop", "cci", "cmo",
            "dema", "dx", "ema", "ht_trendline", "kama", "ma", "mfi", 
            "minus_di", "minus_dm", "mom", "plus_di", "plus_dm", "ppo", "roc",
            "rocp", "rsi", "sar", "sarext", "sma", "tema", "trima", "trix",
            "ultosc", "willr", "wma",
        ]
        signal_ops = [
            "disabled", "crossed_above", "crossed_below", "raising", "falling"
        ]
        price_type = [
            "open", "high", "low", "close", 
            "avgprice", "medprice", "typprice", "wclprice"
        ]
        indicator_shift = range(0, 10, 2)  # np.arange(0, 10, 2)

        for i in range(TryEverything.RULES_SIZE):
            self._create_categorical_parameter(f"{side}_indicator_{i}",
                                               indicators, default_indicator,
                                               side)
            self._create_categorical_parameter(f"{side}_signal_ops_{i}",
                                               signal_ops, "disabled", side)
            self._create_categorical_parameter(f"{side}_indicator_shift_{i}",
                                               indicator_shift, 0, side)
            self._create_categorical_parameter(f"{side}_price_type_{i}",
                                               price_type, "close", side)
            self._create_boolean_parameter(f"{side}_use_price_{i}", False,
                                           side)

    def _create_categorical_parameter(self, name, categories, default, space):
        setattr(self, name,
                CategoricalParameter(categories, default=default, space=space))

    def _create_boolean_parameter(self, name, default, space):
        setattr(self, name, BooleanParameter(default=default, space=space))

    def populate_indicators(self, dataframe: DataFrame,
                            metadata: dict) -> DataFrame:
        # Multiple-output indicators
        multi_output_indicators = {
            "BBANDS": ("upperband", "middleband", "lowerband"),
            "MAMA": ("mama", "fama"),
            "AROON": ("aroondown", "aroonup"),
            "MACD": ("macd", "macdsignal", "macdhist"),
            "STOCH": ("slowk", "slowd"),
            "STOCHF": ("fastk", "fastd"),
        }

        for indicator, column_names in multi_output_indicators.items():
            results = getattr(ta, indicator)(dataframe)
            for i, column_name in enumerate(column_names):
                dataframe[column_name] = results[column_name]

        # Single-output indicators
        single_output_indicators = [
            "ADX", "ADXR", "APO", "AROONOSC", "ATR", "BOP", "CCI", "CMO",
            "DEMA", "DX", "EMA", "HT_TRENDLINE", "KAMA", "MA", "MFI",
            "MINUS_DI", "MINUS_DM", "MOM", "PLUS_DI", "PLUS_DM", "PPO", "ROC", 
            "ROCP", "RSI", "SAR", "SAREXT", "SMA", "TEMA", "TRIMA", "TRIX",
            "ULTOSC", "WILLR", "WMA",
            "AVGPRICE", "MEDPRICE", "TYPPRICE", "WCLPRICE",
        ]

        for func_name in single_output_indicators:
            dataframe[func_name.lower()] = getattr(ta, func_name)(dataframe)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame,
                             metadata: dict) -> DataFrame:
        conditions = []

        for i in range(TryEverything.RULES_SIZE):
            ops_val = getattr(self, f"buy_signal_ops_{i}").value
            if ops_val != "disabled":
                ind_val = getattr(self, f"buy_indicator_{i}").value
                price_type = getattr(self, f"buy_price_type_{i}").value
                shift_val = int(
                    getattr(self, f"buy_indicator_shift_{i}").value)
                use_price = getattr(self, f"buy_use_price_{i}").value

                left_val = dataframe[price_type] if use_price else dataframe[ind_val]
                right_val = dataframe[ind_val].shift(shift_val)

                if ops_val == "crossed_above":
                    conditions.append(
                        qtpylib.crossed_above(
                            to_safe_numeric(left_val, -np.inf),
                            to_safe_numeric(right_val, -np.inf),
                        ))
                elif ops_val == "crossed_below":
                    conditions.append(
                        qtpylib.crossed_below(
                            to_safe_numeric(left_val, np.inf),
                            to_safe_numeric(right_val, np.inf),
                        ))
                elif ops_val == "raising":
                    conditions.append(is_rising(left_val, shift_val + 1))
                elif ops_val == "falling":
                    conditions.append(is_falling(left_val, shift_val + 1))

        if conditions:
            conditions.append(dataframe["volume"] > 0)
            dataframe.loc[reduce(lambda x, y: x & y, conditions),
                          "enter_long"] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame,
                            metadata: dict) -> DataFrame:
        conditions = []

        for i in range(TryEverything.RULES_SIZE):
            ops_val = getattr(self, f"sell_signal_ops_{i}").value
            if ops_val != "disabled":
                ind_val = getattr(self, f"sell_indicator_{i}").value
                price_type = getattr(self, f"sell_price_type_{i}").value
                shift_val = int(
                    getattr(self, f"sell_indicator_shift_{i}").value)
                use_price = getattr(self, f"sell_use_price_{i}").value

                left_val = dataframe[price_type] if use_price else dataframe[ind_val]
                right_val = dataframe[ind_val].shift(shift_val)

                if ops_val == "crossed_above":
                    conditions.append(
                        qtpylib.crossed_above(
                            to_safe_numeric(left_val, -np.inf),
                            to_safe_numeric(right_val, -np.inf),
                        ))
                elif ops_val == "crossed_below":
                    conditions.append(
                        qtpylib.crossed_below(
                            to_safe_numeric(left_val, np.inf),
                            to_safe_numeric(right_val, np.inf),
                        ))
                elif ops_val == "raising":
                    conditions.append(is_rising(left_val, shift_val + 1))
                elif ops_val == "falling":
                    conditions.append(is_falling(left_val, shift_val + 1))

        if conditions:
            conditions.append(dataframe["volume"] > 0)
            dataframe.loc[reduce(lambda x, y: x & y, conditions),
                          "exit_long"] = 1

        return dataframe
