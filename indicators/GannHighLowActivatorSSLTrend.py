import pandas as pd
import talib.abstract as ta

def GannHighLowActivatorSSLTrend(dataframe, period=10):
    """
    Calculate the trend of Gann High-Low Activator SSL indicator based on the input parameters.

    Parameters:
    dataframe (DataFrame): Input DataFrame with columns ["high", "low", "close"].
    period (int): Period for the indicator (default is 10).

    Returns:
    Series: A Series containing the trend values (1 for uptrend, -1 for downtrend, 0 for no trend).
    """
    df = dataframe.copy()

    # Calculate SMA of High and Low prices
    df["SMA_High"] = df["high"].rolling(window=period).mean()
    df["SMA_Low"] = df["low"].rolling(window=period).mean()

    # Calculate SSL and trend
    df["Trend"] = 0
    df.loc[df["close"] > df["SMA_High"], "Trend"] = 1
    df.loc[df["close"] < df["SMA_Low"], "Trend"] = -1

    return df["Trend"]
