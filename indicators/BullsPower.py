import pandas as pd
import talib

def BullsPower(dataframe, period=13, price='high'):
    """
    Calculate the Bulls Power indicator.

    Bulls Power evaluates the strength of buyers in the market by comparing the highest
    price with an Exponential Moving Average (EMA) of the highs.

    Args:
    dataframe: pandas.DataFrame
        A pandas DataFrame with 'high', 'low', 'open', 'close' and 'volume' columns.
    period: int
        The period over which to calculate the EMA of the high prices.
    price: str
        The price type to use in the EMA calculation. Defaults to 'high' based on the
        standard Bulls Power indicator.

    Returns:
    pandas.Series:
        A pandas Series with the Bulls Power values.
    """

    if price not in ['high', 'low', 'open', 'close', 'median', 'typical', 'weighted']:
        raise ValueError("Invalid price type. Allowed values are 'high', 'low', 'open', 'close', 'median', 'typical', 'weighted'.")

    # Validate that the required 'high' column is present in the dataframe
    if 'high' not in dataframe.columns:
        raise ValueError("The input dataframe must contain a 'high' column.")

    # Calculate the EMA of the specified price series over the given period
    ema_high = talib.EMA(dataframe[price], timeperiod=period)

    # Compute the Bulls Power as the difference between the high prices and the EMA of highs
    bulls = dataframe['high'] - ema_high

    # Return the Bulls Power series
    return bulls

# Example usage:
# Assuming 'data' is a pandas DataFrame with the required columns:
# data['BullsPower'] = bulls_power(data, period=13, price='high')
