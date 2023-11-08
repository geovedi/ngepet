import pandas as pd
import numpy as np
import talib.abstract as ta

def LinReg(dataframe, period=14, price_mode=ta.PRICE_HIGH):
    df = dataframe.copy()
    df.fillna(0, inplace=True)
    
    linreg_values = []

    for i in range(len(df)):
        if i < period:
            linreg_values.append(0.0)
        else:
            linreg_value = linreg_calculation(df, price_mode, period, i)
            linreg_values.append(linreg_value)
    
    linreg_series = pd.Series(linreg_values, name='LinReg')
    return linreg_series

def linreg_calculation(dataframe, price_mode, period, index):
    sum_y = sum_x = slope = 0
    
    for x in range(period):
        value = get_value(dataframe, price_mode, index - x)
        sum_y += value
        sum_x += x * value
    
    sum_bars = period * (period - 1) / 2
    sum_sqr_bars = (period - 1) * period * (2 * period - 1) / 6
    sum_2 = sum_bars * sum_y
    num1 = period * sum_x - sum_2
    num2 = sum_bars * sum_bars - period * sum_sqr_bars
    
    if num2 != 0:
        slope = num1 / num2
    
    intercept = (sum_y - slope * sum_bars) / period
    linreg_value = intercept + slope * (period - 1)
    
    return linreg_value

def get_value(dataframe, price_mode, index):
    if price_mode == ta.PRICE_OPEN:
        return dataframe['open'].iloc[index]
    elif price_mode == ta.PRICE_HIGH:
        return dataframe['high'].iloc[index]
    elif price_mode == ta.PRICE_LOW:
        return dataframe['low'].iloc[index]
    elif price_mode == ta.PRICE_CLOSE:
        return dataframe['close'].iloc[index]
    elif price_mode == ta.PRICE_MEDIAN:
        return (dataframe['high'].iloc[index] + dataframe['low'].iloc[index]) / 2
    elif price_mode == ta.PRICE_TYPICAL:
        return (dataframe['high'].iloc[index] + dataframe['low'].iloc[index] + dataframe['close'].iloc[index]) / 3
    elif price_mode == ta.PRICE_WEIGHTED:
        return (dataframe['high'].iloc[index] + dataframe['low'].iloc[index] + 2 * dataframe['close'].iloc[index]) / 4
    else:
        return 0.0

# Usage:
# Replace df with your pandas DataFrame containing columns ['high', 'low', 'open', 'close', 'volume']
# Call the function with your desired period and price mode (e.g., ta.PRICE_HIGH)
#linreg_values = LinReg(df, period=14, price_mode=ta.PRICE_HIGH)
