import pandas as pd
import numpy as np

def LowestInRange(dataframe, time_from="00:00", time_to="00:00"):
    df = dataframe.copy()
    
    # Convert time_from and time_to to datetime objects
    df["Time"] = pd.to_datetime(df["Time"])
    time_from = pd.to_datetime(time_from)
    time_to = pd.to_datetime(time_to)
    
    # Initialize the indicator values
    lowest_values = np.zeros(len(df))
    last_value = 0
    last_usable_value = 0
    lowest_value = float('inf')
    
    for i in range(len(df)):
        if df["Time"][i] >= time_to:
            # Time range is over, set new indicator value and recalculate start/end times
            
            next_start_time = df["Time"][i].replace(hour=time_from.hour, minute=time_from.minute)
            next_end_time = df["Time"][i].replace(hour=time_to.hour, minute=time_to.minute)
            
            if next_end_time < next_start_time:
                next_end_time += pd.DateOffset(days=1)
            
            last_value = lowest_value
            lowest_value = float('inf')
            
            if next_end_time <= df["Time"][i]:
                if next_end_time < next_start_time:
                    next_end_time += pd.DateOffset(days=1)
                else:
                    next_start_time += pd.DateOffset(days=1)
                    next_end_time += pd.DateOffset(days=1)
            
            if next_start_time <= df["Time"][i]:
                lowest_value = df["Low"][i]
        elif df["Time"][i] >= next_start_time:
            lowest_value = min(lowest_value, df["Low"][i])
        else:
            lowest_value = float('inf')
        
        # Avoid outputting zero values if there was a gap in data
        if last_value < float('inf'):
            last_usable_value = last_value
            lowest_values[i] = last_value
        else:
            lowest_values[i] = last_usable_value
    
    df["LowestInRange"] = lowest_values
    return df

# Example usage:
# Assuming you have a pandas DataFrame df with columns ["Time", "Low"]
# You can calculate SqLowestInRange as follows:
# sq_lowest_in_range_result = LowestInRange(df, time_from="00:00", time_to="23:59")
