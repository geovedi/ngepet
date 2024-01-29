import streamlit as st

st.set_page_config(page_title="Strategy Dashboard", layout="wide")

import rapidjson
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

from pathlib import Path

pd.options.mode.chained_assignment = None  # default='warn'
sns.set(font_scale=0.8)

INITIAL_BALANCE = 1_000
DATA_DIR = "/home/ubuntu/streamlit/data/USDT"
PORTFOLIO_NUM_STRATEGIES = 5

LIV1_STRATEGIES = [
    "Evolver_000f_0078",
    "Evolver_0025_0023",
    "Evolver_0029_007b",
    "Evolver_0046_0076",
    "Evolver_010f_0032",
]

LIV5_STRATEGIES = [
    "Evolver_0000_0002",
    "Evolver_000a_0028",
    "Evolver_001e_0007",
    "Evolver_0025_0036",
    "Evolver_0025_003f",
]


def calculate_stability(series):
    ret = series.cumsum()
    trendline = np.linspace(ret.iloc[0], ret.iloc[-1], len(ret))
    similarity = np.corrcoef(ret, trendline)[0, 1]
    stability = similarity**2
    return stability


@st.cache_data
def load_data(directory):
    daily_profit, stats, trades = {}, {}, []

    for fname in Path(directory).glob("*.json"):
        if str(fname).endswith(".meta.json") or str(fname).endswith("last_result.json"):
            continue

        with fname.open("r") as file:
            try:
                data = rapidjson.load(file)
            except Exception as e:
                print(e)

        for strat_name, strat_data in data["strategy"].items():
            force_exit_profit = 0.0
            for trade in strat_data["trades"]:
                trade["strategy"] = strat_name
                trade["direction"] = "SHORT" if trade["is_short"] else "LONG"
                del trade["is_short"]
                if trade["exit_reason"] == "force_exit":
                    force_exit_profit += trade["profit_abs"]
                trades.append(trade)

            df = pd.DataFrame(
                strat_data["daily_profit"],
                columns=["Date", "Profit"],
            )
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date")
            df.loc[df.tail(1).index, "Profit"] -= force_exit_profit
            daily_profit[strat_name] = df["Profit"]

            stats[strat_name] = {
                "Trades": strat_data["total_trades"],
                "Profit": strat_data["profit_total"],
                "Max Drawdown": strat_data["max_relative_drawdown"],
                "CAGR": strat_data["cagr"],
                "Sharpe": strat_data["sharpe"],
                "Sortino": strat_data["sortino"],
                "Expectancy Ratio": strat_data["expectancy_ratio"],
                "Profit Factor": strat_data["profit_factor"],
                "Returns/Drawdown": (
                    strat_data["profit_total"] / strat_data["max_relative_drawdown"]
                ),
                "Stability": calculate_stability(df["Profit"]),
            }

    trades = pd.DataFrame(trades)
    daily_profit = pd.concat(daily_profit, axis=1)

    stats = pd.DataFrame(stats).T
    stats.index.names = ["Strategy"]

    return {
        "trades": trades,
        "stats": stats,
        "daily_profit": daily_profit,
    }


def display_open_trades(strategies, data):
    df = (
        data["trades"]
        .loc[
            (data["trades"]["strategy"].isin(strategies))
            & (data["trades"]["exit_reason"] == "force_exit")
        ]
        .reset_index(drop=True)
    )
    df = df[
        [
            "strategy",
            "pair",
            "open_date",
            "open_rate",
            "amount",
            "profit_ratio",
            "direction",
        ]
    ]

    st.subheader("Open Trades")
    st.dataframe(df, use_container_width=True, hide_index=True)


def display_statistics(strategies, data):
    df = data["stats"].loc[strategies]
    st.dataframe(df, use_container_width=True)


def display_equity_chart(strategies, data):
    df = data["daily_profit"][strategies]
    df = df.cumsum()
    df["Portfolio"] = df.sum(axis=1)
    df /= INITIAL_BALANCE
    st.subheader("Equity")
    st.line_chart(df)


def display_correlation(strategies, data):
    if len(strategies) == 0:
        return

    st.subheader("Correlation")
    df = data["daily_profit"][strategies]

    fig = plt.figure(figsize=(9, 3))
    sns.heatmap(df.corr(), annot=True)
    st.pyplot(fig, use_container_width=True)


def display_portfolio_comparison(data):
    mapping = {
        "RDD": "Returns/Drawdown",
        "PRF": "Profit Factor",
        "STB": "Stability",
        "CGR": "CAGR",
        "SHR": "Sharpe",
        "SOR": "Sortino",
        "EXR": "Expectancy Ratio",
    }

    df_dict = {
        "LIV1": data["daily_profit"][LIV1_STRATEGIES].cumsum(axis=0).sum(axis=1),
        "LIV5": data["daily_profit"][LIV5_STRATEGIES].cumsum(axis=0).sum(axis=1),
    }

    for porto, column in mapping.items():
        df = data["stats"]
        df = df.sort_values(by=column, ascending=False)
        df["base"] = df.index.map(lambda x: x.split("_")[1])
        df = df.drop_duplicates(subset="base", keep="first")
        strategies = df.head(PORTFOLIO_NUM_STRATEGIES).index.tolist()
        df_dict[porto] = data["daily_profit"][strategies].cumsum(axis=0).sum(axis=1)

    df = pd.concat(df_dict, axis=1)
    df = df / INITIAL_BALANCE
    st.subheader("Portfolio Comparison")
    st.line_chart(df, use_container_width=True)


def display_profit_distribution(strategies, data):
    df = data["trades"].loc[data["trades"]["strategy"].isin(strategies), "profit_ratio"]
    st.subheader("Profit Distribution")

    fig = plt.figure(figsize=(9, 3))
    sns.histplot(df, bins=50)
    st.pyplot(fig, use_container_width=True)

def run_montecarlo_simulation(strategies, data):
    df = data["daily_profit"][strategies].cumsum()
    df = (INITIAL_BALANCE + df).pct_change(axis=0)

    portfolio_stats = pd.DataFrame()
    portfolio_stats["daily_returns"] = df.mean(axis=0)
    portfolio_stats["weights"] = 1 / len(df.columns)

    covariance_matrix = df.cov()

    simulations = 20
    days = 90

    portfolio = np.zeros((days, simulations))

    historical_returns = np.full(
        shape=(days, len(df.columns)), fill_value=portfolio_stats.daily_returns
    )

    L = np.linalg.cholesky(covariance_matrix)

    for i in range(0, simulations):
        Z = np.random.normal(size=(days, len(df.columns)))
        daily_returns = historical_returns + np.dot(L, Z.T).T
        portfolio[:, i] = (
            np.cumprod(np.dot(daily_returns, portfolio_stats["weights"]) + 1)
            * INITIAL_BALANCE
        )

    simulated_portfolio = pd.DataFrame(portfolio) - INITIAL_BALANCE
    simulated_portfolio /= INITIAL_BALANCE
    alpha = 5

    def montecarlo_var(alpha):
        sim_val = simulated_portfolio.iloc[-1, :]
        return np.percentile(sim_val, alpha)

    def conditional_var(alpha):
        sim_val = simulated_portfolio.iloc[-1, :]
        return sim_val[sim_val <= montecarlo_var(alpha)].mean()

    mc_var = montecarlo_var(alpha)
    cond_var = conditional_var(alpha)

    mc_columns = simulated_portfolio.columns
    simulated_portfolio.loc[slice(None), "Montecarlo Var"] = mc_var
    simulated_portfolio.loc[slice(None), "Conditional Var"] = cond_var

    st.subheader(f"Montecarlo Simulation (Next {days} Days)")
    st.line_chart(simulated_portfolio, use_container_width=True)

def display_portfolio_info(strategies, data):
    display_statistics(strategies, data)
    display_equity_chart(strategies, data)
    display_correlation(strategies, data)
    run_montecarlo_simulation(strategies, data)
    display_profit_distribution(strategies, data)
    display_open_trades(strategies, data)

# Page Functions
def default_page(data):
    st.title("Strategies")
    display_statistics(slice(None), data)

    st.markdown("---")
    display_portfolio_comparison(data)

    st.markdown("---")
    st.header("Build Your Own Portfolio")

    strategies = st.multiselect(
        "Choose strategies",
        sorted(data["daily_profit"].columns),
        data["stats"]["Sortino"].head(5).index.tolist(),
    )
    display_portfolio_info(strategies, data)


def strategy_page(title, strategy_ids, data):
    st.title(title)
    display_portfolio_info(strategy_ids, data)


def ratio_driven_page(title, ratio_column, data):
    st.title(title)

    df = data["stats"]
    df = df.sort_values(by=ratio_column, ascending=False)
    df["base"] = df.index.map(lambda x: x.split("_")[1])
    df = df.drop_duplicates(subset="base", keep="first")
    strategies = df.head(PORTFOLIO_NUM_STRATEGIES).index.tolist()

    display_portfolio_info(strategies, data)

# Main Application
data = load_data(DATA_DIR)
page_names_to_funcs = {
    "—--": lambda: default_page(data),
    "RDD": lambda: ratio_driven_page("RDD", "Returns/Drawdown", data),
    "PRF": lambda: ratio_driven_page("PRF", "Profit Factor", data),
    "STB": lambda: ratio_driven_page("STB", "Stability", data),
    "CGR": lambda: ratio_driven_page("CGR", "CAGR", data),
    "SHR": lambda: ratio_driven_page("SHR", "Sharpe", data),
    "SOR": lambda: ratio_driven_page("SOR", "Sortino", data),
    "EXR": lambda: ratio_driven_page("EXR", "Expectancy Ratio", data),
    "LV1": lambda: strategy_page("LV1", LIV1_STRATEGIES, data),
    "LV5": lambda: strategy_page("LV5", LIV5_STRATEGIES, data),
}

page_name = st.sidebar.selectbox("Choose a portfolio", page_names_to_funcs.keys())
page_names_to_funcs[page_name]()
