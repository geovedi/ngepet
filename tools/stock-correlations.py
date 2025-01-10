import pandas as pd
import numpy as np
from itertools import combinations
import os
from pathlib import Path
import fire
import gc

def read_ohlcv_data(file_path):
    """
    Read OHLCV data from CSV file and process it memory-efficiently
    """
    df = pd.read_csv(
        file_path, 
        delimiter=',',  # For comma-separated files
    )
    
    # Convert Date and Time to datetime
    df['DateTime'] = pd.to_datetime(
        df['Date'].astype(str) + ' ' + df['Time'].astype(str),
        format='%Y%m%d %H:%M:%S'
    )
    
    df = df[['DateTime', 'Close']]  # Select only needed columns
    df.set_index('DateTime', inplace=True)
    
    gc.collect()
    return df

def calculate_correlation_metrics(series1, series2, stock1, stock2):
    """
    Calculate correlation metrics between two price series
    """
    returns1 = series1.pct_change().dropna()
    returns2 = series2.pct_change().dropna()
    returns1, returns2 = returns1.align(returns2, join='inner')
    
    metrics = {
        'stock1': stock1,
        'stock2': stock2,
        'pearson': returns1.corr(returns2),
        'sample_size': len(returns1)
    }
    
    return metrics

def find_least_correlated(data_directory, min_samples=1000, top_n=10):
    """
    Find top N least correlated assets for each stock
    """
    files = list(Path(data_directory).glob('*.csv'))
    total_files = len(files)
    print(f"Found {total_files} files")
    
    # First pass: read all stock data
    all_stocks = {}
    for file_path in files:
        stock_name = file_path.stem.split('-')[1]
        try:
            df = read_ohlcv_data(file_path)
            if len(df) >= min_samples:
                all_stocks[stock_name] = df['Close']
                print(f"Processed {stock_name}")
        except Exception as e:
            print(f"Error processing {stock_name}: {e}")
    
    print(f"Successfully loaded {len(all_stocks)} stocks")
    
    # Calculate correlations for all pairs
    stock_names = list(all_stocks.keys())
    all_correlations = []
    
    # Calculate all pairs of correlations
    total_pairs = len(stock_names) * (len(stock_names) - 1) // 2
    processed = 0
    
    for i, stock1 in enumerate(stock_names):
        for j, stock2 in enumerate(stock_names):
            if stock1 != stock2:  # Don't calculate correlation with itself
                try:
                    metrics = calculate_correlation_metrics(
                        all_stocks[stock1],
                        all_stocks[stock2],
                        stock1,
                        stock2
                    )
                    all_correlations.append(metrics)
                    processed += 1
                    if processed % 1000 == 0:
                        print(f"Processed {processed} pairs")
                except Exception as e:
                    print(f"Error processing pair {stock1}-{stock2}: {e}")
    
    # Convert to DataFrame
    df_corr = pd.DataFrame(all_correlations)
    
    # Find least correlated stocks for each stock
    for stock in stock_names:
        # Get correlations where this stock is stock1
        stock_corr = df_corr[df_corr['stock1'] == stock].copy()
        
        # Sort by absolute correlation and get top N least correlated
        stock_corr['abs_pearson'] = stock_corr['pearson'].abs()
        least_corr = stock_corr.nsmallest(top_n, 'abs_pearson')
        least_corr = least_corr.drop('abs_pearson', axis=1)
        
        # Save results for this stock
        with open('least_correlated_pairs.txt', 'a') as f:
            f.write(f"\nTop {top_n} least correlated stocks for {stock}:\n")
            f.write(least_corr.to_string())
            f.write("\n" + "="*50)
            f.write(f"\nAverage {stock} pearson score: {stock_corr['abs_pearson'].mean():.2f}\n")
        
        # Also save in CSV format
        least_corr.to_csv(f'correlations_{stock}.csv', index=False)
    
    # Save complete correlation matrix
    correlation_matrix = df_corr.pivot(index='stock1', columns='stock2', values='pearson')
    correlation_matrix.to_csv('complete_correlation_matrix.csv')

def main(data_dir):
    find_least_correlated(
        data_dir,
        min_samples=1000,
        top_n=10
    )
    print("\nResults have been saved to:")
    print("1. 'least_correlated_pairs.txt' - Top N least correlated stocks for each stock")
    print("2. Individual 'correlations_STOCKNAME.csv' files for each stock")
    print("3. 'complete_correlation_matrix.csv' - Complete correlation matrix")

if __name__ == "__main__":
    fire.Fire(main)
