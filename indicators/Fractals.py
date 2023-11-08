import pandas as pd
import numpy as np

def Fractals(dataframe, fractal=3):
    """
    Calculate fractal indicators for high and low prices based on the input parameters.

    Parameters:
    dataframe (DataFrame): Input DataFrame with columns ["high", "low"].
    fractal (int): Number of bars to consider for fractal calculations (default is 3).

    Returns:
    DataFrame: A new DataFrame with fractal up and down values as "Fractal_Up" and "Fractal_Down" columns.
    """
    df = dataframe.copy()

    if (fractal - 1) / 2 <= 0:
        fractal_used = 3
        print(f"Incorrect value for input variable fractal={fractal}. Using the default value={fractal_used} for calculations.")
    else:
        fractal_used = fractal

    ext_up_fractals_buffer = np.zeros(len(df))
    ext_down_fractals_buffer = np.zeros(len(df))

    for i in range(len(df)):
        if i <= fractal_used - 1:
            ext_up_fractals_buffer[i] = 0
            ext_down_fractals_buffer[i] = 0
            continue

        middle_bar = i - (fractal_used - 1) // 2 - 1
        current_high = df["high"].iloc[middle_bar]
        current_low = df["low"].iloc[middle_bar]
        found_high = True
        found_low = True

        for a in range(i - fractal_used, i):
            if a == middle_bar:
                continue

            # Fractals up
            if df["high"].iloc[a] >= current_high:
                found_high = False
            # Fractals down
            if df["low"].iloc[a] <= current_low:
                found_low = False

        ext_up_fractals_buffer[i] = current_high if found_high else 0
        ext_down_fractals_buffer[i] = current_low if found_low else 0

    df["Fractal_Up"] = ext_up_fractals_buffer
    df["Fractal_Down"] = ext_down_fractals_buffer

    return df
