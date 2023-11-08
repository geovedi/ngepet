import pandas as pd
import numpy as np
import talib

def SchaffTrendCycle(dataframe, SchaffPeriod=10, FastEma=20, SlowEma=50, SmoothPeriod=3):
    df = dataframe.copy()

    # Calculate MACD
    df['ema_fast'] = talib.EMA(df['close'], timeperiod=FastEma)
    df['ema_slow'] = talib.EMA(df['close'], timeperiod=SlowEma)
    df['macd'] = df['ema_fast'] - df['ema_slow']

    # Calculate Fast Stochastic
    df['low_macd'] = df['macd'].rolling(window=SchaffPeriod).min()
    df['high_macd'] = (df['macd'].rolling(window=SchaffPeriod).max() - df['low_macd'])

    df['fastk1'] = np.where(df['high_macd'] > 0, 100 * ((df['macd'] - df['low_macd']) / df['high_macd']), 0)

    # Calculate Fast Stochastic D
    df['fastd1'] = df['fastk1'].rolling(window=3).mean()

    # Calculate Second Fast Stochastic
    df['low_stoch'] = df['fastd1'].rolling(window=SchaffPeriod).min()
    df['high_stoch'] = (df['fastd1'].rolling(window=SchaffPeriod).max() - df['low_stoch'])

    df['fastk2'] = np.where(df['high_stoch'] > 0, 100 * ((df['fastd1'] - df['low_stoch']) / df['high_stoch']), 0)

    # Calculate Schaff Trend Cycle
    df['val'] = df['fastk2'].ewm(alpha=0.5).mean()
    df['valc'] = np.where(df['val'].diff() > 0, 1, np.where(df['val'].diff() < 0, 2, 0))

    return df['val']

# Example usage:
# Replace df with your pandas DataFrame containing columns ['open', 'high', 'low', 'close']
# Call the function with your desired parameters
# Example: schaff_trend_cycle_values = SchaffTrendCycle(df, SchaffPeriod=10, FastEma=20, SlowEma=50, SmoothPeriod=3)
