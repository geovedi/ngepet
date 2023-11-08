import pandas as pd
import talib

def BearsPower(dataframe, period=13):
    """
    Calculate the Bears Power indicator.

    Bears Power measures the balance of power between bears (sellers) and the bulls (buyers).
    It is calculated as the difference between the lowest price and an Exponential Moving Average.

    Args:
    dataframe : pandas.DataFrame
        A pandas DataFrame with 'high', 'low', 'open', 'close' and 'volume' columns.
    period : int
        The lookback period to calculate the Exponential Moving Average (EMA).

    Returns:
    pandas.Series
        A pandas Series containing the Bears Power indicator values.
    """

    # Ensure that the DataFrame index is sequential (resetting index if needed)
    df = dataframe.reset_index(drop=True)

    # Calculate the EMA on the 'low' price series
    ema_low = talib.EMA(df['low'], timeperiod=period)

    # Calculate Bears Power as the difference between the low prices and their EMA
    bears = df['low'] - ema_low

    # Return the Bears Power indicator series
    return bears

# Example usage:
# Assuming 'data' is a pandas DataFrame with the required columns
# data['BearsPower'] = bears_power(data, period=13)
