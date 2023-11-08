import pandas as pd
import numpy as np
import talib

def SRPercentRank(dataframe, Mode=2, Lenght=120, ATRPeriod=12):
    df = dataframe.copy()
    
    # Calculate ATR
    df['ATR'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=ATRPeriod)

    # Initialize indicator buffer
    ind_buffer = [0.0] * len(df)

    for i in range(len(df)):
        count = 0
        for a in range(1, Lenght + 1):
            if Mode == 1:  # Mode without ATR, only high-low Range
                if df['close'][i] > df['low'][i + a] and df['close'][i] < df['high'][i + a]:
                    count += 1
            elif Mode == 2:  # Mode with ATR +- high-low Range
                atr_value = df['ATR'][i]
                if df['close'][i] > (df['low'][i + a] - atr_value) and df['close'][i] < (df['high'][i + a] + atr_value):
                    count += 1

        percrank = (count / Lenght) * 100
        ind_buffer[i] = percrank

    df['SR Percent Rank'] = ind_buffer
    return df['SR Percent Rank']

# Example usage:
# Replace df with your pandas DataFrame containing columns ['open', 'high', 'low', 'close', 'volume']
# Call the function with your desired parameters
# Example: sr_percent_rank_values = SRPercentRank(df, Mode=2, Lenght=120, ATRPeriod=12)
