import pandas as pd
import numpy as np

def Vortex(dataframe, period=32):
    """
    Calculate Vortex Indicator components for a given pandas DataFrame.

    Args:
        dataframe (pd.DataFrame): DataFrame with columns ['high', 'low', 'open', 'close', 'volume'].
        period (int): Vortex period.

    Returns:
        pd.Series: Vortex Positive (VI+)
        pd.Series: Vortex Negative (VI-)
    """
    df = dataframe.copy()
    
    # Calculate True Range (TR), Vortex Positive (VI+), and Vortex Negative (VI-)
    df['tr'] = df['high'].combine_first(df['close'].shift(1)) - df['low'].combine_first(df['close'].shift(1))
    df['vi_plus'] = abs(df['high'] - df['low'].shift(1))
    df['vi_minus'] = abs(df['low'] - df['high'].shift(1))
    
    # Calculate the Vortex Indicator components
    df['tr_sum'] = df['tr'].rolling(window=period).sum()
    df['vi_plus_sum'] = df['vi_plus'].rolling(window=period).sum()
    df['vi_minus_sum'] = df['vi_minus'].rolling(window=period).sum()
    
    # Calculate the Vortex Indicator values
    vortex_positive = (df['vi_plus_sum'] / df['tr_sum']).fillna(0)
    vortex_negative = (df['vi_minus_sum'] / df['tr_sum']).fillna(0)
    
    return vortex_positive, vortex_negative

# Example usage:
# Replace df with your pandas DataFrame containing columns ['open', 'high', 'low', 'close', 'volume']
# Call the function as follows:
# vi_plus, vi_minus = Vortex(df, period=32)
