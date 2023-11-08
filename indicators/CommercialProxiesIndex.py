import numpy as np
import pandas as pd
import talib

def CommercialProxiesIndex(dataframe, index_period=200, atr_period=40, smoothing=3):
    """
    Calculate the Commercial Proxies Index (CPI) for a given DataFrame.

    Args:
    dataframe: A pandas DataFrame containing 'high', 'low', 'open', 'close', and 'volume' columns.
    index_period: The lookback period to find the highest and lowest Value1 for normalization.
    atr_period: The period for calculating the Average True Range (ATR).
    smoothing: The period for the Simple Moving Average (SMA) of the final CPI value.

    Returns:
    A pandas Series representing the CPI after applying SMA.

    The CPI is calculated as follows:
    1. Calculate the difference between open and close prices to find price movement.
    2. Compute the sum of these differences over the specified atr_period.
    3. Normalize this sum by dividing it by the ATR and multiply by 100 to get a percentage.
    4. Determine the max and min values of this normalized figure over the index_period.
    5. Normalize these values into an index from 0 to 100.
    6. Apply a simple moving average to smooth out the index values.
    """
    df = dataframe.copy()

    # Calculate Open-Close difference
    df['OCBuffer'] = df['open'] - df['close']

    # Rolling sum of the Open-Close Buffer
    df['sum_OC'] = df['OCBuffer'].rolling(window=atr_period, min_periods=1).sum()

    # Calculate the ATR using TA-Lib's function
    df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=atr_period)

    # Normalize the sum_OC by ATR
    df['Value1'] = (df['sum_OC'] / atr_period) / df['atr'] * 100

    # Handle potential division by zero if ATR is zero
    df['Value1'].replace([np.inf, -np.inf], np.nan, inplace=True)
    df['Value1'].fillna(method='ffill', inplace=True)

    # Rolling max and min for normalization
    df['max_Value1'] = df['Value1'].rolling(window=index_period, min_periods=1).max()
    df['min_Value1'] = df['Value1'].rolling(window=index_period, min_periods=1).min()

    # Normalize the index to a 0-100 scale
    df['CPI_without_SMA'] = 100 * (df['Value1'] - df['min_Value1']) / (df['max_Value1'] - df['min_Value1'])

    # Replace NaN with zero where max equals min (to handle division by zero after normalization)
    df['CPI_without_SMA'].replace([np.inf, -np.inf], np.nan, inplace=True)
    df['CPI_without_SMA'].fillna(0, inplace=True)

    # Apply SMA to the CPI index
    df['CPI'] = df['CPI_without_SMA'].rolling(window=smoothing, min_periods=1).mean()

    return df['CPI']

# Example usage:
# df = pd.read_csv('path_to_your_csv_file.csv')
# df['CPI'] = CommercialProxiesIndex(df)
