import pandas as pd
import numpy as np

def KeltnerChannel(dataframe, period=20, const=1.5):
    df = dataframe.copy()

    upper = np.zeros(len(df))
    middle = np.zeros(len(df))
    lower = np.zeros(len(df))

    for i in range(len(df)):
        if i >= period:
            offset = avg_diff(df['high'], df['low'], period, i) * const
            middle[i] = avg_true_range(df['high'], df['low'], df['close'], period, i)
            upper[i] = middle[i] + offset
            lower[i] = middle[i] - offset

    upper_series = pd.Series(upper, name='Upper')
    middle_series = pd.Series(middle, name='Middle')
    lower_series = pd.Series(lower, name='Lower')

    return upper_series, middle_series, lower_series

def avg_true_range(high, low, close, atr_period, shift):
    sum = 0
    for x in range(shift, shift + atr_period):
        sum += (high[x] + low[x] + close[x]) / 3

    return sum / atr_period

def avg_diff(high, low, atr_period, shift):
    sum = 0
    for x in range(shift, shift + atr_period):
        sum += high[x] - low[x]

    return sum / atr_period

# Usage:
# Replace df with your pandas DataFrame containing columns ['high', 'low', 'open', 'close', 'volume']
# Call the function with your desired parameters
#upper, middle, lower = KeltnerChannel(df, period=20, const=1.5)
