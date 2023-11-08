import pandas as pd
import numpy as np
import talib.abstract as ta

def LaguerreRSI(dataframe, gamma=0.7):
    df = dataframe.copy()
    
    L0 = L1 = L2 = L3 = L0A = L1A = L2A = L3A = 0
    L0_ = L1_ = L2_ = L3_ = L0A_ = L1A_ = L2A_ = L3A_ = 0
    
    laguerre_values = []

    for i in range(len(df)):
        L0A = L0
        L1A = L1
        L2A = L2
        L3A = L3
        
        L0 = (1 - gamma) * df['close'][i] + gamma * L0A_
        L1 = -gamma * L0 + L0A + gamma * L1A_
        L2 = -gamma * L1 + L1A + gamma * L2A_
        L3 = -gamma * L2 + L2A + gamma * L3A_
        
        CU = CD = 0
        
        if L0 >= L1:
            CU = L0 - L1
        else:
            CD = L1 - L0
        
        if L1 >= L2:
            CU += L1 - L2
        else:
            CD += L2 - L1
        
        if L2 >= L3:
            CU += L2 - L3
        else:
            CD += L3 - L2
        
        if CU + CD != 0:
            LRSI = CU / (CU + CD)
        else:
            LRSI = 0
        
        laguerre_values.append(LRSI)
        
        # Update the previous values for the next iteration
        L0_ = L0
        L1_ = L1
        L2_ = L2
        L3_ = L3
        L0A_ = L0A
        L1A_ = L1A
        L2A_ = L2A
        L3A_ = L3A
    
    laguerre_series = pd.Series(laguerre_values, name='Laguerre')
    return laguerre_series

# Usage:
# Replace df with your pandas DataFrame containing columns ['high', 'low', 'open', 'close', 'volume']
# Call the function with your desired gamma value
#laguerre_values = LaguerreRSI(df, gamma=0.7)
