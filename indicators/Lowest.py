import pandas as pd
import numpy as np
import talib
from talib import MA_Type

def Lowest(dataframe, period=14, price="low"):
    df = dataframe.copy()
    
    # Select the price column based on the input parameter
    price_column = df[price]
    
    # Initialize the indicator values
    lowest_values = np.zeros(len(df))
    
    for i in range(len(df)):
        if i < period - 1:
            lowest_values[i] = 0.0
        else:
            price_slice = price_column[i - period + 1:i + 1]
            lowest_value = min(price_slice)
            lowest_values[i] = lowest_value
    
    df["Lowest"] = lowest_values
    return df

# Example usage:
# Assuming you have a pandas DataFrame df with columns ["high", "low", "open", "close", "volume"]
# You can calculate SqLowest as follows:
# sq_lowest_result = Lowest(df, period=14, price="low")
