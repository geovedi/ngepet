import pandas as pd
import talib

def TrueRange(dataframe):
    """
    Calculate True Range (TR) for a given pandas DataFrame.

    Args:
        dataframe (pd.DataFrame): DataFrame with columns ['high', 'low', 'open', 'close', 'volume'].

    Returns:
        pd.Series: True Range values.
    """
    df = dataframe.copy()
    
    # Initialize True Range buffer
    true_range = [0.0] * len(df)

    for i in range(len(df)):
        cur_high = df['high'][i]
        cur_low = df['low'][i]
        close1 = df['close'][i - 1] if i > 0 else df['close'][i]

        true_high = max(close1, cur_high)
        true_low = min(close1, cur_low)

        tr = true_high - true_low
        true_range[i] = tr

    return pd.Series(true_range, name='TrueRange')

# Example usage:
# Replace df with your pandas DataFrame containing columns ['open', 'high', 'low', 'close', 'volume']
# Call the function as follows:
# true_range_values = TrueRange(df)
