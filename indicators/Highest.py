import pandas as pd
import numpy as np
import talib
from talib import MA_Type

def Highest(dataframe, period=14, price="high"):
    df = dataframe.copy()
    
    # Select the price column based on the input parameter
    price_column = df[price]
    
    # Initialize the indicator values
    highest_values = np.zeros(len(df))
    
    for i in range(len(df)):
        if i < period - 1:
            highest_values[i] = 0.0
        else:
            price_slice = price_column[i - period + 1:i + 1]
            highest_value = max(price_slice)
            highest_values[i] = highest_value
    
    df["Highest"] = highest_values
    return df

# Example usage:
# Assuming you have a pandas DataFrame df with columns ["high", "low", "open", "close", "volume"]
# You can calculate SqHighest as follows:
# sq_highest_result = Highest(df, period=14, price="high")
