import pandas as pd
import numpy as np

def Pivots(dataframe, start_hour=8, start_minute=20, days_to_plot=0):
    df = dataframe.copy()
    
    # Calculate the number of minutes in a day
    minutes_per_day = 24 * 60
    
    # Calculate the start time in minutes
    start_time_minutes = start_hour * 60 + start_minute
    
    # Calculate the closing time in minutes
    close_time_minutes = start_time_minutes - df["timeframe"].iloc[0]
    
    # Ensure close_time_minutes is positive
    if close_time_minutes < 0:
        close_time_minutes += minutes_per_day
    
    # Calculate the number of bars in a day
    bars_per_day = minutes_per_day / df["timeframe"].iloc[0]
    
    # Initialize pivot level dictionaries
    pivot_levels = {
        "P": [],
        "R1": [],
        "R2": [],
        "R3": [],
        "S1": [],
        "S2": [],
        "S3": []
    }

    for i in range(len(df)):
        # Calculate the previous day's opening and closing bars
        previous_closing_bar = find_last_time_match_fast(close_time_minutes, i + 1, df, True)
        
        if df["time"].iloc[previous_closing_bar] != df["time"].iloc[previous_closing_bar - 1]:
            previous_opening_bar = find_last_time_match_fast(start_time_minutes, previous_closing_bar + 1, df, False)
            previous_high = df["high"].iloc[previous_closing_bar]
            previous_low = df["low"].iloc[previous_closing_bar]
            previous_close = df["close"].iloc[previous_closing_bar]
            
            # Calculate the previous day's high and low
            for j in range(previous_closing_bar, previous_opening_bar + 1):
                if df["high"].iloc[j] > previous_high:
                    previous_high = df["high"].iloc[j]
                if df["low"].iloc[j] < previous_low:
                    previous_low = df["low"].iloc[j]
            
            # Calculate pivot levels
            P = (previous_high + previous_low + previous_close) / 3
            R1 = (2 * P) - previous_low
            S1 = (2 * P) - previous_high
            R2 = P + (previous_high - previous_low)
            S2 = P - (previous_high - previous_low)
            R3 = P + 2 * (previous_high - previous_low)
            S3 = P - 2 * (previous_high - previous_low)
            
            pivot_levels["P"].append(P)
            pivot_levels["R1"].append(R1)
            pivot_levels["R2"].append(R2)
            pivot_levels["R3"].append(R3)
            pivot_levels["S1"].append(S1)
            pivot_levels["S2"].append(S2)
            pivot_levels["S3"].append(S3)
        else:
            # If the previous closing bar is the same as the current closing bar,
            # just append NaN values to the pivot level buffers
            pivot_levels["P"].append(np.nan)
            pivot_levels["R1"].append(np.nan)
            pivot_levels["R2"].append(np.nan)
            pivot_levels["R3"].append(np.nan)
            pivot_levels["S1"].append(np.nan)
            pivot_levels["S2"].append(np.nan)
            pivot_levels["S3"].append(np.nan)
    
    # Filter the DataFrame based on days_to_plot
    if days_to_plot > 0:
        df = df.iloc[-int(days_to_plot * bars_per_day):]

    return pivot_levels

def find_last_time_match_fast(time_to_look_for, starting_bar, df, is_closing_bar):
    how_many_bars_back = min(len(df) - 1, int(3 * 1440 / df["timeframe"].iloc[0]))

    if check_bar_is_what_we_look_for(time_to_look_for, starting_bar, df, is_closing_bar):
        return starting_bar
    elif starting_bar < how_many_bars_back and check_bar_is_what_we_look_for(time_to_look_for, starting_bar, df, is_closing_bar):
        return starting_bar
    elif starting_bar < how_many_bars_back and check_bar_is_what_we_look_for(time_to_look_for, starting_bar + 1, df, is_closing_bar):
        return starting_bar + 1
    else:
        for a in range(starting_bar + 1, how_many_bars_back):
            if check_bar_is_what_we_look_for(time_to_look_for, a, df, is_closing_bar):
                return a
    return how_many_bars_back + 1

def check_bar_is_what_we_look_for(time_to_look_for, bar, df, is_closing_bar):
    if bar >= len(df) - 1:
        return False

    previous_bars_time = (df["time"].iloc[bar - 1].hour * 60) + df["time"].iloc[bar - 1].minute
    current_bars_time = (df["time"].iloc[bar].hour * 60) + df["time"].iloc[bar].minute

    if current_bars_time == time_to_look_for:
        return True

    previous_bar_day = df["time"].iloc[bar - 1].dayofyear
    current_bar_day = df["time"].iloc[bar].dayofyear

    if current_bar_day != previous_bar_day:
        current_bars_time -= 1440

    if previous_bars_time > time_to_look_for and current_bars_time < time_to_look_for:
        return is_closing_bar if current_bars_time < time_to_look_for else True

    return False

# Example usage:
# Replace df with your pandas DataFrame containing columns ['time', 'high', 'low', 'open', 'close', 'volume', 'timeframe']
# Call the function with your desired parameters
#pivots = calculate_pivots(df, start_hour=8, start_minute=20, days_to_plot=0)
