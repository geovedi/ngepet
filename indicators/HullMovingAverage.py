import numpy as np
import pandas as pd

def HullMovingAverage(dataframe, period=20, divisor=2.0):
    df = dataframe.copy()
    df["HMA"] = np.nan

    full_period = max(int(period) if period > 1 else 1, 1)
    half_period = max(int(full_period / divisor) if divisor > 1 else 1, 1)
    sqrt_period = int(np.sqrt(full_period))
    array_size = -1
    weight1 = 1.0
    weight2 = 1.0
    weight3 = 1.0
    value_col = df["close"]
    hull_col = np.zeros(len(df))

    for i in range(len(df)):
        value = value_col.iloc[i]

        if array_size < len(df):
            array_size = len(df) + 500
            array = np.zeros((array_size, 8))

        m = array
        m[i, 0] = value

        if i > full_period:
            m[i, 1] = m[i - 1, 1] + value * half_period - m[i - 1, 5]
            m[i, 5] = m[i - 1, 5] + value - value_col.iloc[i - half_period]
            m[i, 2] = m[i - 1, 2] + value * full_period - m[i - 1, 6]
            m[i, 6] = m[i - 1, 6] + value - value_col.iloc[i - full_period]
        else:
            m[i, 1] = m[i, 2] = m[i, 5] = m[i, 6] = weight1 = weight2 = 0
            w1 = half_period
            w2 = full_period
            for k in range(i, -1, -1):
                if w1 > 0:
                    m[i, 1] += value_col.iloc[k] * w1
                    m[i, 5] += value_col.iloc[k]
                    weight1 += w1
                m[i, 2] += value_col.iloc[k] * w2
                m[i, 6] += value_col.iloc[k]
                weight2 += w2
                if w1 > 0:
                    w1 -= 1
                w2 -= 1

        m[i, 7] = 2.0 * m[i, 1] / weight1 - m[i, 2] / weight2

        if i > sqrt_period:
            m[i, 3] = m[i - 1, 3] + m[i, 7] * sqrt_period - m[i - 1, 7]
            m[i, 7] = m[i - 1, 7] + m[i, 7] - m[i - sqrt_period, 7]
        else:
            m[i, 3] = m[i, 7] = weight3 = 0
            w3 = sqrt_period
            for k in range(i, -1, -1):
                m[i, 3] += m[k, 7] * w3
                m[i, 7] += m[k, 7]
                weight3 += w3
                w3 -= 1

        hull_col[i] = m[i, 3] / weight3

    df["HMA"] = hull_col
    return df["HMA"]
