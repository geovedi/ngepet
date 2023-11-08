import numpy as np
import pandas as pd
import talib

def QQE(dataframe, rsi_period=14, sf=5, wf=4.236):
    df = dataframe.copy()
    
    # Calculate the Wilders Period
    wilders_period = rsi_period * 2 - 1
    start_bar = sf if wilders_period < sf else wilders_period
    
    rsi_handle = talib.RSI(df["close"].values, timeperiod=rsi_period)
    
    # Initialize indicator buffers
    rsi_ma = np.zeros(len(df))
    tr_level_slow = np.zeros(len(df))
    rsi_values = np.zeros(len(df))
    atr_rsi = np.zeros(len(df))
    ma_atr_rsi = np.zeros(len(df))
    ma_atr_rsi_wp = np.zeros(len(df))
    
    for i in range(1, len(df)):
        rsi_values[i] = rsi_handle[i]
        rsi_ma[i] = rsi_values[i]
    
    for i in range(1, len(df)):
        rsi_ma[i] = rsi_ma[i] * (2.0 / (1 + sf)) + (1 - (2.0 / (1 + sf))) * rsi_ma[i - 1]
        atr_rsi[i] = abs(rsi_ma[i - 1] - rsi_ma[i])
        ma_atr_rsi[i] = atr_rsi[i]
    
    for i in range(1, len(df)):
        ma_atr_rsi[i] = ma_atr_rsi[i] * (2.0 / (1 + wilders_period)) + (1 - (2.0 / (1 + wilders_period))) * ma_atr_rsi[i - 1]
        ma_atr_rsi_wp[i] = ma_atr_rsi[i]
    
    i = len(df) - 1
    tr = tr_level_slow[i - 1]
    rsi1 = rsi_ma[i - 1]
    
    while i >= 1:
        rsi0 = rsi_ma[i]
        ma_atr_rsi_wp[i] = ma_atr_rsi_wp[i] * (2.0 / (1 + wilders_period)) + (1 - (2.0 / (1 + wilders_period))) * ma_atr_rsi_wp[i - 1]
        dar = ma_atr_rsi_wp[i] * wf
        
        dv = tr
        if rsi0 < tr:
            tr = rsi0 + dar
            if rsi1 < dv:
                if tr > dv:
                    tr = dv
        elif rsi0 > tr:
            tr = rsi0 - dar
            if rsi1 > dv:
                if tr < dv:
                    tr = dv
        tr_level_slow[i] = tr
        rsi1 = rsi0
        i -= 1
    
    rsi_ma_series = pd.Series(rsi_ma, name="rsi_ma")
    tr_level_slow_series = pd.Series(tr_level_slow, name="tr_level_slow")
    rsi_values_series = pd.Series(rsi_values, name="rsi")
    atr_rsi_series = pd.Series(atr_rsi, name="atr_rsi")
    ma_atr_rsi_series = pd.Series(ma_atr_rsi, name="ma_atr_rsi")
    ma_atr_rsi_wp_series = pd.Series(ma_atr_rsi_wp, name="ma_atr_rsi_wp")
    
    return rsi_ma_series, tr_level_slow_series, rsi_values_series, atr_rsi_series, ma_atr_rsi_series, ma_atr_rsi_wp_series

# Example usage:
# Replace df with your pandas DataFrame containing columns ['close']
# Call the function with your desired parameters
#rsi_ma, tr_level_slow, rsi_values, atr_rsi, ma_atr_rsi, ma_atr_rsi_wp = QQE(df)
