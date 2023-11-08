import pandas as pd
import numpy as np
import talib

def Ichimoku(dataframe, tenkan=9, kijun=26, senkou=52):
    df = dataframe.copy()
    
    tenkan_sen = (df['high'].rolling(window=tenkan).max() + df['low'].rolling(window=tenkan).min()) / 2
    kijun_sen = (df['high'].rolling(window=kijun).max() + df['low'].rolling(window=kijun).min()) / 2
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun)
    senkou_span_b = ((df['high'].rolling(window=senkou).max() + df['low'].rolling(window=senkou).min()) / 2).shift(kijun)
    
    chikou_span = df['close'].shift(-kijun)
    
    return tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span

# Usage
# Replace df with your pandas DataFrame containing columns ['high', 'low', 'open', 'close', 'volume']
#tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span = Ichimoku(df, tenkan=9, kijun=26, senkou=52)
