import pandas as pd
import numpy as np

def HighestInRange(dataframe, time_from="00:00", time_to="00:00"):
    df = dataframe.copy()
    
    # Convert time_from and time_to to datetime objects
    df["Time"] = pd.to_datetime(df["Time"])
    time_from = pd.to_datetime(time_from)
    time_to = pd.to_datetime(time_to)
    
    # Initialize the indicator values
    highest_values = np.zeros(len(df))
    last_value = 0
    last_usable_value = 0
    highest_value = 0
    
    for i in range(len(df)):
        if df["Time"][i] >= time_to:
            # Time range is over, set new indicator value and recalculate start/end times
            
            next_start_time = df["Time"][i].replace(hour=time_from.hour, minute=time_from.minute)
            next_end_time = df["Time"][i].replace(hour=time_to.hour, minute=time_to.minute)
            
            if next_end_time < next_start_time:
                next_end_time += pd.DateOffset(days=1)
            
            last_value = highest_value
            highest_value = 0
            
            if next_end_time <= df["Time"][i]:
                if next_end_time < next_start_time:
                    next_end_time += pd.DateOffset(days=1)
                else:
                    next_start_time += pd.DateOffset(days=1)
                    next_end_time += pd.DateOffset(days=1)
            
            if next_start_time <= df["Time"][i]:
                highest_value = df["High"][i]
        elif df["Time"][i] >= next_start_time:
            highest_value = max(highest_value, df["High"][i])
        else:
            highest_value = 0
        
        # Avoid outputting zero values if there was a gap in data
        if last_value > 0:
            last_usable_value = last_value
            highest_values[i] = last_value
        else:
            highest_values[i] = last_usable_value
    
    df["HighestInRange"] = highest_values
    return df

# Example usage:
# Assuming you have a pandas DataFrame df with columns ["Time", "High"]
# You can calculate SqHighestInRange as follows:
# sq_highest_in_range_result = HighestInRange(df, time_from="00:00", time_to="23:59")
