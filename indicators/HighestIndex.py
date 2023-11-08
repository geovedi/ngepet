import pandas as pd
import numpy as np
import talib
from talib import MA_Type

def HighestIndex(dataframe, period=14, price="high"):
    df = dataframe.copy()
    
    # Select the price column based on the input parameter
    price_column = df[price]
    
    # Initialize the indicator values
    highest_index_values = np.zeros(len(df))
    
    for i in range(len(df)):
        if i < period - 1:
            highest_index_values[i] = 0
        else:
            highest_index = 0
            highest_value = -1
            
            for a in range(i - period + 1, i + 1):
                value = getValue(df, price, a)
                
                if value - highest_value > 0.00000001:
                    highest_index = i - a
                    highest_value = value
            
            highest_index_values[i] = highest_index
    
    df["HighestIndex"] = highest_index_values
    return df

def getValue(dataframe, price, index):
    price_column = dataframe[price]
    
    if price == "open":
        return price_column.iloc[index]
    elif price == "high":
        return price_column.iloc[index]
    elif price == "low":
        return price_column.iloc[index]
    elif price == "close":
        return price_column.iloc[index]
    elif price == "median":
        return (dataframe["high"].iloc[index] + dataframe["low"].iloc[index]) / 2
    elif price == "typical":
        return (dataframe["high"].iloc[index] + dataframe["low"].iloc[index] + dataframe["close"].iloc[index]) / 3
    elif price == "weighted":
        return (dataframe["high"].iloc[index] + dataframe["low"].iloc[index] + dataframe["close"].iloc[index] + dataframe["close"].iloc[index]) / 4
    else:
        return 0

# Example usage:
# Assuming you have a pandas DataFrame df with columns ["high", "low", "open", "close", "volume"]
# You can calculate SqHighestIndex as follows:
# sq_highest_index_result = HighestIndex(df, period=14, price="high")
