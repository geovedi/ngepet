import numpy as np
import pandas as pd

def Reflex(dataframe, reflex_period=24):
    class ReflexIndicator:
        def __init__(self):
            self.val = []
            self.valc = []
            self.c1 = 1
            self.c2 = 1
            self.c3 = 1
            self.multi = 1
            self.m_array = []
            self.m_arraySize = -1
            self.m_period = 0

        def cosine(self, a):
            return np.cos(a * np.pi / 180.0)

        def initialize(self, period):
            self.m_period = period if period > 1 else 1
            a1 = np.exp(-1.414 * np.pi / (self.m_period * 0.5))
            b1 = 2.0 * a1 * self.cosine(np.cos(1.414 * 180 / (self.m_period * 0.5)))
            self.c2 = b1
            self.c3 = -a1 * a1
            self.c1 = 1.0 - self.c2 - self.c3
            self.multi = 1 + sum(range(1, self.m_period))

        def calculate(self, value, i, bars):
            if self.m_arraySize < bars:
                self.m_arraySize = bars + 500
                self.m_array = [0] * self.m_arraySize

            self.m_array[i]['value'] = value

            if i > 1:
                self.m_array[i]['ssm'] = self.c1 * (self.m_array[i]['value'] + self.m_array[i-1]['value']) / 2.0 + \
                                          self.c2 * self.m_array[i-1]['ssm'] + \
                                          self.c3 * self.m_array[i-2]['ssm']
            else:
                self.m_array[i]['ssm'] = value

            if i > self.m_period:
                self.m_array[i]['sum'] = self.m_array[i-1]['sum'] + self.m_array[i]['ssm'] - self.m_array[i-self.m_period]['ssm']
            else:
                self.m_array[i]['sum'] = self.m_array[i]['ssm']
                for k in range(1, self.m_period):
                    if i - k >= 0:
                        self.m_array[i]['sum'] += self.m_array[i-k]['ssm']

            tslope = (self.m_array[i-self.m_period]['ssm'] - self.m_array[i]['ssm']) / self.m_period if i >= self.m_period else 0

            sum_val = 0
            if i > inpReflexPeriod:
                for a in range(1, inpReflexPeriod + 1):
                    sum_val = sum_val + self.m_array[i]['ssm'] + a * tslope - self.m_array[i-a]['ssm']
                sum_val = sum_val / inpReflexPeriod

            self.m_array[i]['ms'] = 0.04 * sum_val * sum_val + 0.96 * self.m_array[i-1]['ms'] if i > 0 else 0

            return sum_val / np.sqrt(self.m_array[i]['ms']) if self.m_array[i]['ms'] != 0 else 0

    df = dataframe.copy()
    reflex = ReflexIndicator()
    reflex.initialize(reflex_period)

    val = []
    valc = []

    for i in range(len(df)):
        value = reflex.calculate(df['close'][i], i, len(df))
        val.append(value)
        valc.append(0 if i == 0 or val[i] == val[i-1] else (1 if val[i] < val[i-1] else 0))

    df['Reflex'] = val
    return df['Reflex']

# Example usage:
# Replace df with your pandas DataFrame containing columns ['close']
# Call the function with your desired reflex_period
# Example: reflex_values = Reflex(df, reflex_period=24)
