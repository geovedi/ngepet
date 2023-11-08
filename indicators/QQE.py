import pandas as pd
import numpy as np
import talib.abstract as ta

def QQE(dataframe, rsi_period=14, sF=5, wF=4.236):
    """
    Calculate QQE (Quantitative Qualitative Estimation) indicator components for a given pandas DataFrame.

    Args:
        dataframe (pd.DataFrame): DataFrame with columns ['high', 'low', 'open', 'close', 'volume'].
        rsi_period (int): RSIPeriod parameter for QQE (default is 14).
        sF (int): sF parameter for QQE (default is 5).
        wF (float): wF parameter for QQE (default is 4.236).

    Returns:
        pd.Series: qqe_value1
        pd.Series: qqe_value2
    """
    df = dataframe.copy()
    
    wilders_period = rsi_period * 2 - 1
    
    rsi_values = ta.RSI(df, timeperiod=rsi_period)["RSI"]
    rsi_ema_values = ta.EMA(rsi_values, timeperiod=sF)
    
    atr_rsi_values = pd.Series(index=df.index)
    ma_atr_rsi_values = pd.Series(index=df.index)
    
    for i in range(len(df)):
        if i == 0:
            atr_rsi_values.iloc[i] = 0
            ma_atr_rsi_values.iloc[i] = 0
        else:
            atr_rsi_values.iloc[i] = abs(rsi_values.iloc[i-1] - rsi_ema_values.iloc[i])
            ma_atr_rsi_values.iloc[i] = atr_rsi_values.iloc[i:].rolling(window=wilders_period).mean().iloc[0]
    
    qqe_value1 = rsi_ema_values.copy()
    qqe_value2 = rsi_ema_values.copy()
    
    for i in range(len(df)):
        rsi0 = rsi_ema_values.iloc[i]
        rsi1 = rsi_ema_values.iloc[i-1] if i > 0 else rsi0
        dv = rsi_values.iloc[i-1] if i > 0 else rsi0
        
        atr_rsi = atr_rsi_values.iloc[i]
        ma_atr_rsi = ma_atr_rsi_values.iloc[i]
        
        dar = ma_atr_rsi * wF
        tr = qqe_value2.iloc[i-1] if i > 0 else qqe_value2.iloc[i]
        
        if rsi0 < tr:
            tr = rsi0 + dar
            if rsi1 < dv and tr > dv:
                tr = dv
        elif rsi0 > tr:
            tr = rsi0 - dar
            if rsi1 > dv and tr < dv:
                tr = dv
        
        qqe_value1.iloc[i] = rsi0
        qqe_value2.iloc[i] = tr
        
    qqe_value1.name = 'qqe_value1'
    qqe_value2.name = 'qqe_value2'
    
    return qqe_value1, qqe_value2

# Example usage:
# Replace df with your pandas DataFrame containing columns ['open', 'high', 'low', 'close', 'volume']
# Call the function as follows:
# qqe_value1, qqe_value2 = QQE(df, rsi_period=14, sF=5, wF=4.236)
