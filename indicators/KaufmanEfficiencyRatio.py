import pandas as pd
import numpy as np
import talib

def KaufmanEfficiencyRatio(dataframe, period=10):
    """
    Calculate Kaufman's Efficiency Ratio (KER) for a given DataFrame.
    
    Kaufman's Efficiency Ratio (also known as Generalized Fractal Efficiency) is designed
    to account for market efficiency, which can highlight the strength and direction of a trend.
    
    The formula for the KER is:
    KER = ABS(Change in price over N periods) / Sum of individual absolute price changes over N periods

    Args:
        dataframe (pd.DataFrame): A pandas DataFrame with 'high', 'low', 'open', 'close', 'volume' columns.
        period (int): The period over which to calculate the KER.

    Returns:
        pd.Series: A pandas Series containing the KER values.
    """

    # Check if 'close' column is in the DataFrame
    if 'close' not in dataframe:
        raise ValueError("DataFrame must include a 'close' column.")

    # Net price movement over the period
    change = dataframe['close'].diff(period).abs()

    # Volatility is the sum of absolute price changes over the period
    volatility = dataframe['close'].diff().abs().rolling(window=period).sum()

    # Kaufman Efficiency Ratio calculation
    # Adding a small number to avoid division by zero
    ker = change / (volatility + 1e-10)

    # Fill the initial 'nan' values which are less than 'period' with zero or previous actual calculated KER
    ker[:period] = np.nan  # Ensuring NaN for the look-back period

    # Return the KER values
    return ker

# Example usage:
# Assuming 'data' is a pandas DataFrame with the required columns:
# data['KER'] = KaufmanEfficiencyRatio(data, period=10)
