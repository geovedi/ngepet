import pandas as pd
import numpy as np

def FibonacciLevels(dataframe, fibo_range=1, x=0, fibo_level=61.8, custom_fibo_level=None, start_date=None):
    """
    Calculate Fibonacci levels for price ranges based on input parameters.

    Parameters:
    dataframe (DataFrame): Input DataFrame with columns ["high", "low", "open", "close", "volume"].
    fibo_range (int): Fibo range mode [1-10] (default is 1).
        - 1  : High-Low previous day
        - 2  : High-low previous week
        - 3  : High-low previous month
        - 4  : High-Low of last X days
        - 5  : Open-Close previous day
        - 6  : Open-Close previous week
        - 7  : Open-Close previous month
        - 8  : Open-Close of last X days
        - 9  : Highest-Lowest for last X bars back
        - 10 : Open-Close for last X bars back    
    x (int): Custom days/bars count (default is 0).
    fibo_level (float): Default Fibonacci level (default is 61.8).
    custom_fibo_level (float): Custom Fibonacci level (default is None).
    start_date (datetime): Start point for calculations (default is None).

    Returns:
    DataFrame: A new DataFrame with the calculated Fibonacci levels added as a "fibo_level" column.
    """
    df = dataframe.copy()

    # Initialize variables
    tf_end_time = 0
    bars_used = -1
    prev_tf_open = 0
    prev_tf_high = 0
    prev_tf_low = 0
    prev_tf_close = 0
    fibo_level = fibo_level
    fibo_range_used = fibo_range
    start_date_used = False

    # Create an empty array to store Fibonacci levels
    buffer = np.empty(len(df))
    buffer[:] = np.nan

    for i in range(len(df)):
        if _is_new_tf_start(df.index[i], start_date_used, start_date, fibo_range_used, tf_end_time, bars_used, x):
            upper_value, lower_value = _calculate_price_range(df, i, fibo_range_used, prev_tf_open, prev_tf_close, prev_tf_high, prev_tf_low)

            if not np.isnan(upper_value) and not np.isnan(lower_value):
                percent_step = (upper_value - lower_value) / 100
                delta = fibo_level * percent_step
                bullish = prev_tf_close > prev_tf_open
                fibo_level = (upper_value - delta) if bullish else (lower_value + delta)

            prev_tf_open = df["open"].iloc[i]
            prev_tf_high = df["high"].iloc[i]
            prev_tf_low = df["low"].iloc[i]
            prev_tf_close = df["close"].iloc[i]
            bars_used = 0 if i == 0 else 1

        else:
            if i != 0:
                prev_tf_high = max(prev_tf_high, df["high"].iloc[i])
                prev_tf_low = min(prev_tf_low, df["low"].iloc[i])
                prev_tf_close = df["close"].iloc[i]
                bars_used += 1

        buffer[i] = fibo_level

    return buffer

def _is_new_tf_start(time, start_date_used, start_date, fibo_range_used, tf_end_time, bars_used, x):
    if start_date is not None and not start_date_used and start_date <= time:
        _set_end_time(time, fibo_range_used, tf_end_time)
        return True

    if fibo_range_used in [9, 10]:
        if bars_used == -1 or bars_used == x:
            return True
        else:
            return False

    if fibo_range_used in [1, 2, 3, 4, 5, 6, 7, 8]:
        if tf_end_time == 0 or tf_end_time <= time:
            _set_end_time(time, fibo_range_used, tf_end_time)
            return True
        else:
            return False

    return False

def _set_end_time(time, fibo_range_used, tf_end_time):
    cur_day_start = pd.Timestamp(time).replace(hour=0, minute=0, second=0, microsecond=0)

    if fibo_range_used in [1, 5]:
        tf_end_time = cur_day_start + pd.Timedelta(days=1)
    elif fibo_range_used in [2, 6]:
        cur_day_start = cur_day_start - pd.Timedelta(days=cur_day_start.dayofweek)
        tf_end_time = cur_day_start + pd.Timedelta(weeks=1)
    elif fibo_range_used in [3, 7]:
        cur_day_start = cur_day_start - pd.Timedelta(days=cur_day_start.day - 1)
        tf_end_time = cur_day_start + pd.Timedelta(days=cur_day_start.days_in_month)

def _calculate_price_range(df, i, fibo_range_used, prev_tf_open, prev_tf_close, prev_tf_high, prev_tf_low):
    if fibo_range_used in [1, 2, 3, 4, 9]:
        upper_value = prev_tf_high
        lower_value = prev_tf_low
    elif fibo_range_used in [5, 6, 7, 8, 10]:
        upper_value = max(prev_tf_open, prev_tf_close)
        lower_value = min(prev_tf_open, prev_tf_close)
    else:
        upper_value = np.nan
        lower_value = np.nan

    return upper_value, lower_value
