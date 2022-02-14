import fire
import os
import random
import sys
import shutil
import arrow
import pandas as pd
import numpy as np

from subprocess import check_output
from bs4 import BeautifulSoup
from fire import Fire



TERMINAL_ID = "D0E8209F77C8CF37AD8BF550E51FF075"
TERMINAL_DIR = (
    "C:\\Users\\Administrator\\AppData\\Roaming\\MetaQuotes\\Terminal\\"
    f"{TERMINAL_ID}")
TESTER_DIR = (
    "C:\\Users\\Administrator\\AppData\\Roaming\\MetaQuotes\\Tester\\"
    f"{TERMINAL_ID}")
CONFIG_DIR = (
    "C:\\Users\\Administrator\\AppData\\Roaming\\MetaQuotes\\Terminal\\Common\\Files"
    )
BIN_PATH = "C:\\Program Files\\MetaTrader 5"


FOREX_MAJOR = '''
AUDUSD EURUSD GBPUSD NZDUSD USDCAD USDCHF USDJPY XAUUSD
'''.strip().split()

FOREX_ALL = '''
AUDCAD AUDCHF AUDJPY AUDNZD AUDUSD
CADCHF CADJPY
CHFJPY
EURAUD EURCAD EURCHF EURGBP EURJPY EURNZD EURUSD
GBPAUD GBPCAD GBPCHF GBPJPY GBPNZD GBPUSD
NZDCAD NZDCHF NZDJPY NZDUSD
USDCAD USDCHF USDJPY
XAUUSD
'''.strip().split()

DERIV_INDEX = '''
Jump 10 Index
Jump 25 Index
Jump 50 Index
Jump 75 Index
Jump 100 Index
Volatility 10 Index
Volatility 25 Index
Volatility 50 Index
Volatility 75 Index
Volatility 100 Index
'''.strip().split("\n")

DERIV_CRYPTO = '''
BTCUSD ETHUSD
BNBUSD BTCXAG BTCXAU 
DSHUSD 
EOSUSD 
IOTUSD
LTCUSD 
NEOUSD 
OMGUSD 
XLMUSD XMRUSD XRPUSD 
ZECUSD 
'''.strip().split()

SYMBOLS = DERIV_INDEX

LEFTOVERS = set('''
'''.strip().split())


def kill_tester():
    try:
        cmd_out = check_output("taskkill.exe /IM metatester64.exe /F",
                               shell=True)
    except:
        pass


def reset_env():
    try:
        shutil.rmtree(f"{TERMINAL_DIR}\\Tester\\cache")
    except:
        pass

    try:
        shutil.rmtree(TESTER_DIR)
    except:
        pass

def str2num(x):
    try:
        return int(x)
    except:
        try:
            return float(x)
        except:
            return x


def xml2df(fname):
    soup = BeautifulSoup(open(fname).read(), 'xml')
    header = None
    rows = []

    for i, r in enumerate(
            soup.find_all('Worksheet')[0].find_all('Table')[0].find_all(
                'Row')):
        row = [str2num(c.Data.text) for c in r.find_all('Cell')]
        if i == 0:
            header = row
        else:
            rows.append(dict(zip(header, row)))

    symbol = soup.find_all('Title')[0].text
    symbol = symbol.split(',')[0]
    symbol = symbol.replace('Yoji-ADX Breakout v1.0 ', '')

    df = pd.DataFrame(rows)
    df['_symbol'] = symbol
    return df

CONFIG = f'''
[Tester]
Expert=Yoji-ADX Breakout v1.0.ex5
Symbol=__SYMBOL__
Period=M1
Optimization=2
Model=1
FromDate=__START_DATE__
ToDate=__END_DATE__
ForwardMode=1
Deposit=10000
Currency=USD
ProfitInPips=0
Leverage=1000
ExecutionMode=120
OptimizationCriterion=6
UseCloud=0
Report=reports\\__REPORT__.xml
ReplaceReport=1
ShutdownTerminal=1


[TesterInputs]
; Generic Setting
_risk_type=0||0||0||2||N
_risk_value=100.0||10.0||1.0||100.0||N
_expire=1
; Single Strategy Setting
_symbol_name=__SYMBOL__
_magic_number=__MAGIC__
_session_start=22||0||2||22||Y
_session_length=8||4||4||12||Y
_lookback=15||10||5||20||Y
_adx_tf=15||5||0||16385||Y
_adx_period=7||9||2||15||Y
_adx_level=15||15||5||25||Y
_atr_tf=15||5||0||16385||Y
_atr_period=9||9||2||15||Y
_atr_factor=2||1.0||1.0||5.0||Y
_rr_ratio=6||1.0||1.0||6.0||Y
; Portfolio Strategy
_config=__CONFIG_NAME__

'''


def read_xml(fname, magic):
    df = xml2df(fname)
    print(f'Reading XML with {len(df)} entries...')

    if '_exit_mom' in df.columns:
        df['_exit_mom'] = df['_exit_mom'].apply(lambda x: True if x == 'true' else False)

    df = df[(df['Forward Result'] > 1.0) & (df['Back Result'] > 1.0)]
    df['profit'] = np.floor(df['Profit'] / 2500) * 2500
    df = df[df['profit'] > 0]
    rescol = ['Forward Result', 'Back Result']
    df['score'] = df[rescol].std(axis=1)
    df = df[(df['score']) < (df['score'].mean())]
    df = df.sort_values(['score'], ascending=(True))
    df = df.iloc[:30]
    df = df.sort_values(['profit', 'Back Result'], ascending=(False, False))
    if not df.empty:
        print(df.head())

    if df.empty:
        return (None, 0.0)

    row = df.iloc[0].to_dict()
    rr_ratio = row.get('_rr_ratio', 3.0)

    cfg = (f'{row["_symbol"]},'
            f'{magic},'
            f'{row["_session_start"]},'
            f'{row["_session_length"]},'
            f'{row["_lookback"]},'
            f'{row["_adx_tf"]},'
            f'{row["_adx_period"]},'
            f'{row["_adx_level"]},'
            f'{row["_atr_tf"]},'
            f'{row["_atr_period"]},'
            f'{row["_atr_factor"]:.2f},'
            f'{rr_ratio:.2f}'
            )
    return (cfg, row["profit"])


def main(start_date="2021.04.01", end_date="2022.02.01", 
         base_magic=100, max_cycle=3,
         run_config='run.ini', exp_name='exp'):


    report_file = f"{exp_name}.xml"
    config_file = f"{exp_name}.cfg"

    with open(f"{CONFIG_DIR}\\{config_file}", "w") as out:
        out.write(f"\n# {start_date} - {end_date}\n")

    magic = base_magic + 1
    profit = 0

    for n_cycle in range(max_cycle):
        random.shuffle(SYMBOLS)

        for symbol in SYMBOLS:
            reset_env()

            print(f"\noptimisation started for {symbol}, magic={magic}, "
                  f"min target={profit}")

            try:
                cfg = CONFIG
                cfg = cfg.replace("__SYMBOL__", symbol)
                cfg = cfg.replace("__START_DATE__", start_date)
                cfg = cfg.replace("__END_DATE__", end_date)
                cfg = cfg.replace("__MAGIC__", str(magic))
                cfg = cfg.replace("__REPORT__", report_file)
                cfg = cfg.replace("__CONFIG_NAME__", config_file)
                
                with open(run_config, 'w') as out:
                    out.write(cfg)

                cmd_out = check_output(
                    f"{BIN_PATH}\\terminal64.exe /config:{run_config}"
                )
                (res, res_profit) = read_xml(f"{TERMINAL_DIR}\\reports\\"
                                             f"{report_file}.forward.xml", 
                                             magic)

                if res and res_profit > profit:
                    with open(f"{CONFIG_DIR}\\{config_file}", "a") as out:
                        out.write(f"{res}\n")
                    print(f"\nfound config: {res}\n\n")
                    magic += 1
                    profit = res_profit

            except Exception as e:
                print(e)

            except KeyboardInterrupt:
                sys.exit(1)


if __name__ == '__main__':
    fire.Fire(main)
