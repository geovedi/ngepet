import pandas as pd
import talib

def BearsPower(dataframe, period=13, price='low'):
    """
    Calculate the Bears Power indicator.

    Bears Power evaluates the strength of sellers in the market by comparing the lowest
    price with an Exponential Moving Average (EMA) of the lows.

    Args:
    dataframe: pandas.DataFrame
        A pandas DataFrame with 'high', 'low', 'open', 'close' and 'volume' columns.
    period: int
        The period over which to calculate the EMA of the low prices.
    price: str
        The price type to use in the EMA calculation. Defaults to 'low' based on the
        standard Bears Power indicator.

    Returns:
    pandas.Series:
        A pandas Series with the Bears Power values.
    """

    if price not in ['high', 'low', 'open', 'close', 'median', 'typical', 'weighted']:
        raise ValueError("Invalid price type. Allowed values are 'high', 'low', 'open', 'close', 'median', 'typical', 'weighted'.")

    # Validate that the required 'low' column is present in the dataframe
    if 'low' not in dataframe.columns:
        raise ValueError("The input dataframe must contain a 'low' column.")

    # Calculate the EMA of the specified price series over the given period
    ema_low = talib.EMA(dataframe[price], timeperiod=period)

    # Compute the Bears Power as the difference between the low prices and the EMA of lows
    bears = dataframe['low'] - ema_low

    # Return the Bears Power series
    return bears

# Example usage:
# Assuming 'data' is a pandas DataFrame with the required columns:
# data['BearsPower'] = BearsPower(data, period=13, price='low')
