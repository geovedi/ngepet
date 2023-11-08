import pandas as pd
import numpy as np
import talib

def SuperTrend(dataframe, st_mode=1, atr_period=24, atr_multiplication=3):
    df = dataframe.copy()
    
    # Calculate ATR
    df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=atr_period)

    # Initialize indicator buffer
    ind_buffer = [0.0] * len(df)

    for i in range(len(df)):
        if st_mode == 1:
            atr_value = df['atr'][i]
            upper_level = (df['high'][i] + df['low'][i]) / 2 + atr_multiplication * atr_value
            lower_level = (df['high'][i] + df['low'][i]) / 2 - atr_multiplication * atr_value
            
            if df['close'][i] > ind_buffer[i - 1] and df['close'][i - 1] <= ind_buffer[i - 1]:
                ind_buffer[i] = lower_level
            elif df['close'][i] < ind_buffer[i - 1] and df['close'][i - 1] >= ind_buffer[i - 1]:
                ind_buffer[i] = upper_level
            elif ind_buffer[i - 1] < lower_level:
                ind_buffer[i] = lower_level
            elif ind_buffer[i - 1] > upper_level:
                ind_buffer[i] = upper_level
            else:
                ind_buffer[i] = ind_buffer[i - 1]

    df['sq_super_trend'] = ind_buffer
    return df['sq_super_trend']

# Example usage:
# Replace df with your pandas DataFrame containing columns ['open', 'high', 'low', 'close', 'volume']
# Call the function with your desired parameters
# Example: super_trend_values = SuperTrend(df, st_mode=1, atr_period=24, atr_multiplication=3)
