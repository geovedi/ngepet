import pandas as pd
import numpy as np
import talib

def KaufmanAdaptiveMovingAverage(dataframe, ama_period=10, fast_ema_period=2, slow_ema_period=30):
    df = dataframe.copy()

    # Calculate Efficiency Ratio (ER)
    df['delta'] = df['close'].diff()
    df['delta_abs'] = df['delta'].abs()
    df['sum_delta_abs'] = df['delta_abs'].rolling(window=ama_period).sum()
    df['sum_delta'] = df['delta'].rolling(window=ama_period).sum()
    df['er'] = df['delta_abs'] / df['sum_delta_abs']
    
    # Calculate Smoothed Efficiency Ratio (SER)
    df['ser'] = df['er'].rolling(window=ama_period * 2 - 1).mean()
    
    # Calculate Smoothing Constant (SC)
    df['sc'] = ((df['er'] * (fast_ema_period - 1)) + 2) / ((fast_ema_period + 1) * (fast_ema_period + 1))
    
    # Initialize KAMA
    df['kama'] = 0.0
    
    # Calculate KAMA values
    for i in range(ama_period - 1, len(df)):
        if i == ama_period - 1:
            df['kama'].iloc[i] = df['close'].iloc[i]
        else:
            df['kama'].iloc[i] = df['kama'].iloc[i - 1] + df['sc'].iloc[i] * (df['close'].iloc[i] - df['kama'].iloc[i - 1])
    
    return df['kama']

# Usage
# Replace df with your pandas DataFrame containing columns ['high', 'low', 'open', 'close', 'volume']
#kama = KaufmanAdaptiveMovingAverage(df, ama_period=10, fast_ema_period=2, slow_ema_period=30)
