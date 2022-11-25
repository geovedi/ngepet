import os
import fire

import numpy as np
import pandas as pd

from glob import glob

from pypfopt import EfficientFrontier
from pypfopt import risk_models
from pypfopt import expected_returns
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices



TERMINAL_COMMON_DIR = 'C:\\Users\\Administrator\\AppData\\Roaming\\MetaQuotes\\Terminal\\Common\\Files'


def prepare_df(data_dir, start_date, deposit, period):
    portfolio = pd.DataFrame()

    for fname in glob(f'{data_dir}/*.csv'):
        df = pd.read_csv(fname, sep=';')
        df['OpenTime'] = pd.to_datetime(df['OpenTime'], unit='ns')
        df['CloseTime'] = pd.to_datetime(df['CloseTime'], unit='ns')
        df = df.set_index('CloseTime')

        list_path = os.path.normpath(fname).split(os.sep)

        colname = list_path[-1].replace('.csv', '')
        portfolio[colname] = df['ProfitLoss'].resample('D').sum() 

    portfolio = portfolio.sort_index()
    portfolio = portfolio.loc[start_date:]

    portfolio.loc['2001-01-01', :] = deposit
    portfolio = portfolio.sort_index()

    portfolio = portfolio.cumsum().pct_change()

    sqn = np.sqrt(period) * (portfolio.rolling(period).mean() / portfolio.rolling(period).std())
    x = (sqn.iloc[-1] > 1.75)

    portfolio = portfolio.loc[start_date:]
    portfolio = (1 + portfolio).cumprod()

    print("---", start_date, "---")

    """
    portfolio_ma = portfolio.rolling(period).mean()
    x = (portfolio.iloc[-1] > portfolio_ma.iloc[-1])
    """

    #print(sqn.iloc[-1])
    portfolio = portfolio.loc[:, x]

    print(portfolio.resample('W').last().tail(5).round(5).T)

    return portfolio


def main(data_dir=TERMINAL_COMMON_DIR, deposit=100_000, multiplier=4, period=200):
    for start_date in ["2021-11-01", "2022-05-01"]:
        calculate(data_dir, start_date, deposit, multiplier, period)

def calculate(data_dir, start_date, deposit, multiplier, period):
    data = prepare_df(data_dir, start_date, deposit, period)
    if data.empty:
        print("empty data")
        return

    mu = expected_returns.mean_historical_return(data)
    S = risk_models.sample_cov(data)
    ef = EfficientFrontier(mu, S)
    raw_weights = ef.max_sharpe()
    weights = ef.clean_weights()

    latest_prices = get_latest_prices(data)
    da = DiscreteAllocation(weights, latest_prices, total_portfolio_value=deposit)
    allocation, leftover = da.greedy_portfolio()
    allocation = pd.Series(allocation).sort_index()

    print()
    print(start_date)
    print(multiplier * (allocation / deposit))
    print()

if __name__ == '__main__':
    fire.Fire(main)
