import talib.abstract as ta
import numpy as np

from freqtrade.optimize.space import SKDecimal
from freqtrade.strategy import (
    BooleanParameter,
    CategoricalParameter,
    IStrategy
)
from pandas import DataFrame
from functools import reduce


class ADXMomentum(IStrategy):
    """
    ADXMomentum Strategy

    This strategy uses the Average Directional Movement Index (ADX) and Momentum (MOM)
    to determine entry and exit points for trades. The ADX is used to gauge trend strength,
    while the momentum indicator is used to measure the speed at which the price of a security
    is moving. The strategy is configured with a range of parameters to optimize for various
    timeframes and market conditions during hyperoptimization.
    """

    use_custom_stoploss = True

    class HyperOpt:
        # Define a custom stoploss space.
        def stoploss_space():
            return [SKDecimal(-0.1, -0.01, decimals=2, name="stoploss")]

    INTERFACE_VERSION: int = 3

    stoploss = -0.03
    minimal_roi = {"0": 0.1}

    timeframe = "1h"

    entry_adx_period = CategoricalParameter(np.arange(5, 100, 5), default=15, space="buy", optimize=True)
    entry_mom_period = CategoricalParameter(np.arange(5, 100, 5), default=15, space="buy", optimize=True)
    entry_adx_level = CategoricalParameter(np.arange(10, 50, 5), default=25, space="buy", optimize=True)
    entry_plus_di_level = CategoricalParameter(np.arange(10, 50, 5), default=25, space="buy", optimize=True)
    entry_shift = CategoricalParameter(np.arange(0, 30, 2), default=0, space="buy", optimize=True)
    entry_di_needed = BooleanParameter(default=True, space="buy", optimize=True)

    exit_adx_period = CategoricalParameter(np.arange(5, 100, 5), default=15, space="sell", optimize=True)
    exit_mom_period = CategoricalParameter(np.arange(5, 100, 5), default=15, space="sell", optimize=True)
    exit_adx_level = CategoricalParameter(np.arange(10, 50, 5), default=25, space="sell", optimize=True)
    exit_minus_di_level = CategoricalParameter(np.arange(10, 50, 5), default=25, space="sell", optimize=True)
    exit_shift = CategoricalParameter(np.arange(0, 30, 2), default=0, space="sell", optimize=True)
    exit_di_needed = BooleanParameter(default=True, space="sell", optimize=True)

    # Define the startup candle count using max value from buy/sell period parameters
    startup_candle_count: int = 50

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add several indicators needed for the strategy logic on the dataframe: ADX, +DI, -DI, and MOM.
        
        For both entry and exit, it uses different or the same timeperiod for ADX and MOM as configured.
        
        :param dataframe: Original dataframe with historical candle data.
        :param metadata: Additional information such as pair, timeframe, etc.
        :return: the dataframe with the new indicators.
        """

        # Entry indicators
        dataframe["entry_adx"] = ta.ADX(dataframe, timeperiod=self.entry_adx_period.value)
        dataframe["entry_plus_di"] = ta.PLUS_DI(dataframe, timeperiod=self.entry_adx_period.value)
        dataframe["entry_minus_di"] = ta.MINUS_DI(dataframe, timeperiod=self.entry_adx_period.value)
        dataframe["entry_mom"] = ta.MOM(dataframe, timeperiod=self.entry_mom_period.value)

        # Exit indicators
        dataframe["exit_adx"] = ta.ADX(dataframe, timeperiod=self.exit_adx_period.value)
        dataframe["exit_plus_di"] = ta.PLUS_DI(dataframe, timeperiod=self.exit_adx_period.value)
        dataframe["exit_minus_di"] = ta.MINUS_DI(dataframe, timeperiod=self.exit_adx_period.value)
        dataframe["exit_mom"] = ta.MOM(dataframe, timeperiod=self.exit_mom_period.value)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Create entry conditions by combining various indicators. It signals a long entry (buy) when ADX 
        is above the threshold indicating a strong trend, and the MOM indicator confirms upward momentum.
        
        Additional condition of the +DI being above the -DI can be used based on the `entry_di_needed` flag.
        
        :param dataframe: Dataframe with indicators and historical candle data.
        :param metadata: Additional information such as pair, timeframe, etc.
        :return: the dataframe with entry signals.
        """

        conditions = [
            (dataframe["entry_adx"].shift(self.entry_shift.value) > self.entry_adx_level.value),
            (dataframe["entry_plus_di"].shift(self.entry_shift.value) > self.entry_plus_di_level.value),
            (dataframe["entry_mom"] > 0),
            (dataframe["volume"] > 0),
        ]

        if self.entry_di_needed.value:
            conditions.append((dataframe["entry_plus_di"] > dataframe["entry_minus_di"]))

        dataframe.loc[reduce(lambda x, y: x & y, conditions), "enter_long"] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Create exit conditions similar to entry conditions but typically in the opposite direction
        or using a different logic that may define a safe exit point before the trend reverses or diminishes.
        
        It signals an exit from a long position (sell) when ADX is above the threshold for exit conditions,
        and the MOM indicator shows downward momentum, with the possibility of checking the DI crossover based
        on the `exit_di_needed` flag.
        
        :param dataframe: Dataframe with indicators and historical candle data.
        :param metadata: Additional information such as pair, timeframe, etc.
        :return: the dataframe with exit signals.
        """

        conditions = [
            (dataframe["exit_adx"].shift(self.exit_shift.value) > self.exit_adx_level.value),
            (dataframe["exit_minus_di"].shift(self.exit_shift.value) > self.exit_minus_di_level.value),
            (dataframe["exit_mom"] < 0),
            (dataframe["volume"] > 0),
        ]

        if self.exit_di_needed.value:
            conditions.append((dataframe["exit_plus_di"] < dataframe["exit_minus_di"]))

        dataframe.loc[reduce(lambda x, y: x & y, conditions), "exit_long"] = 1

        return dataframe
