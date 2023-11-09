import numpy as np
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

from freqtrade.optimize.space import Categorical, Dimension, Integer, SKDecimal
from freqtrade.strategy import CategoricalParameter, IStrategy
from pandas import DataFrame
from functools import reduce
from typing import Any, Dict, List


class BBandRSI(IStrategy):
    """This is a strategy for trading cryptocurrencies using the Bollinger Bands and
    the Relative Strength Index (RSI) as indicators for entry and exit points, within
    the freqtrade framework. It aims to buy and sell on conditions based on
    statistical measures and momentum indicators.
    """

    use_custom_stoploss = True

    class HyperOpt:
        # Define a custom stoploss space.
        def stoploss_space():
            return [SKDecimal(-0.30, -0.01, decimals=2, name="stoploss")]

        # Define custom ROI space
        def roi_space() -> List[Dimension]:
            return [SKDecimal(0.01, 0.30, decimals=2, name="roi")]

        def generate_roi_table(params: Dict) -> Dict[int, float]:
            roi_table = {0: params["roi"]}
            return roi_table

    INTERFACE_VERSION: int = 3

    stoploss = -0.03
    minimal_roi = {}

    timeframe = "1h"

    entry_bb_period = CategoricalParameter(np.arange(5, 100, 5), default=15, space="buy", optimize=True)
    entry_bb_std = CategoricalParameter(np.arange(1.0, 5.0, 0.25), default=2.0, space="buy", optimize=True)
    entry_shift = CategoricalParameter(np.arange(0, 10, 2), default=0, space="buy", optimize=True)

    exit_rsi_period = CategoricalParameter(np.arange(5, 100, 5), default=15, space="sell", optimize=True)
    exit_rsi_level = CategoricalParameter(np.arange(50, 95, 5), default=70, space="sell", optimize=True)
    exit_shift = CategoricalParameter(np.arange(0, 10, 2), default=0, space="sell", optimize=True)

    startup_candle_count: int = 100

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Adds several indicators to the given DataFrame such as RSI and lower
        Bollinger Band.

        Args:
            dataframe: Original DataFrame with OHLCV data.
            metadata: Additional information (like pair, timeframe) provided by the exchange.

        Returns:
            DataFrame: The DataFrame with the new indicators added.
        """
        dataframe["exit_rsi"] = ta.RSI(
            dataframe, timeperiod=int(self.exit_rsi_period.value)
        )

        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe),
            window=int(self.entry_bb_period.value),
            stds=float(self.entry_bb_std.value),
        )
        dataframe["entry_bb_lu"] = bollinger["lower"]

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Generates entry signals for a long position based on defined conditions
        including RSI value crossing above the lower Bollinger Band and the specified
        RSI level.

        Args:
            dataframe: DataFrame containing the indicators.
            metadata: Additional metadata for the entry signal.

        Returns:
            DataFrame: The DataFrame with the entry signal column updated.
        """
        conditions = [
            (
                qtpylib.crossed_above(
                    dataframe["close"].shift(self.entry_shift.value),
                    dataframe["entry_bb_lu"],
                ).shift(self.entry_shift.value)
            ),
            (dataframe["volume"] > 0),
        ]

        dataframe.loc[reduce(lambda x, y: x & y, conditions), "enter_long"] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Generates exit signals for a long position based on the RSI being greater
        than a defined level.

        Args:
            dataframe: DataFrame containing the indicators.
            metadata: Additional metadata for the exit signal.

        Returns:
            DataFrame: The DataFrame with the exit signal column updated.
        """
        conditions = [
            (
                dataframe["exit_rsi"].shift(self.exit_shift.value)
                > self.exit_rsi_level.value
            ),
            (dataframe["volume"] > 0),
        ]

        dataframe.loc[reduce(lambda x, y: x & y, conditions), "exit_long"] = 1

        return dataframe
