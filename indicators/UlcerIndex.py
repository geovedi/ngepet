import pandas as pd
import numpy as np
import talib.abstract as ta

def UlcerIndex(dataframe, ui_mode=1, ui_period=24):
    """
    Calculate Ulcer Index (UI) for a given pandas DataFrame.

    Args:
        dataframe (pd.DataFrame): DataFrame with columns ['high', 'low', 'open', 'close', 'volume'].
        ui_mode (int): Ulcer Index mode (1 or 2).
        ui_period (int): Ulcer Index period.

    Returns:
        pd.Series: Ulcer Index values.
    """
    df = dataframe.copy()

    if ui_mode not in [1, 2]:
        raise ValueError("Invalid Ulcer Index mode. Use 1 or 2.")

    # Calculate Moving Average
    df["ma"] = ta.SMA(df, timeperiod=ui_period)

    buffer_pd = []

    for i in range(len(df)):
        if ui_mode == 2:
            index = df["close"].rolling(window=ui_period).idxmin()
            max_value = 1 / df["ma"].iat[index]
            pr = 1 / df["ma"].iat[i]
        else:
            index = df["close"].rolling(window=ui_period).idxmax()
            max_value = df["ma"].iat[index]
            pr = df["ma"].iat[i]

        buffer_pd.append((pr - max_value) ** 2)

    df["buffer_pd"] = buffer_pd
    df["ui"] = np.sqrt(df["buffer_pd"].rolling(window=ui_period).mean()) * 100

    return df["ui"]

# Example usage:
# Replace df with your pandas DataFrame containing columns ['open', 'high', 'low', 'close', 'volume']
# Call the function as follows:
# ulcer_index_values = UlcerIndex(df, ui_mode=1, ui_period=24)
