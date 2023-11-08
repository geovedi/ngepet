import pandas as pd
import talib as ta

def AvgVol(df, ma_period=14):
    """
    Calculates the Average Volume over a specified period.
    
    :param df: pandas DataFrame containing 'high', 'low', 'open', 'close', and 'volume' columns
    :param ma_period: Period over which to calculate the moving average of volume
    :return: pandas DataFrame with an additional 'avg_volume' column representing the moving average of volume
    """
    # Ensure the volume column is a float64 type for precise calculations
    df['volume'] = df['volume'].astype('float64')
    
    # Calculate the moving average of volume using TA-Lib
    df['avg_volume'] = ta.SMA(df['volume'], timeperiod=ma_period)
    
    return df

# Example usage:
# Assuming 'data' is a pandas DataFrame with the required columns
# data = AvgVol(data, ma_period=14)
