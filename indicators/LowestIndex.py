import pandas as pd
import numpy as np
import talib
from talib import MA_Type

def LowestIndex(dataframe, period=14, price="low"):
    df = dataframe.copy()
    
    # Select the price column based on the input parameter
    price_column = df[price]
    
    # Initialize the indicator values
    lowest_index_values = np.zeros(len(df))
    
    for i in range(len(df)):
        if i < period - 1:
            lowest_index_values[i] = 0
        else:
            lowest_index = 0
            lowest_value = float('inf')
            
            for a in range(i - period + 1, i + 1):
                value = getValue(df, price, a)
                
                if value < lowest_value:
                    lowest_index = i - a
                    lowest_value = value
            
            lowest_index_values[i] = lowest_index
    
    df["LowestIndex"] = lowest_index_values
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
# You can calculate SqLowestIndex as follows:
# sq_lowest_index_result = LowestIndex(df, period=14, price="low")
