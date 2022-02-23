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

import logging

logging.basicConfig(
    format='%(asctime)s [%(process)d] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO)

TERMINAL_ID = "D0E8209F77C8CF37AD8BF550E51FF075"

BIN_PATH = "C:\\Program Files\\MetaTrader 5"
METATADER5_APPDATA_DIR = "C:\\Users\\Administrator\\AppData\\Roaming\\MetaQuotes"
TERMINAL_DIR = f"{METATADER5_APPDATA_DIR}\\Terminal\\{TERMINAL_ID}"
TESTER_DIR = f"{METATADER5_APPDATA_DIR}\\Tester\\{TERMINAL_ID}"
CONFIG_DIR = f"{METATADER5_APPDATA_DIR}\\Terminal\\Common\\Files"

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


def kill_tester():
    try:
        cmd_out = check_output("taskkill.exe /IM metatester64.exe /F",
                               shell=True)
    except:
        pass


def reset_env():
    try:
        shutil.rmtree(f"{TERMINAL_DIR}\\Tester\\cache")
        shutil.rmtree(f"{TERMINAL_DIR}\\Tester\\reports")
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
    symbol = symbol.replace('Yoji-MACD v1.0 ', '')

    df = pd.DataFrame(rows)
    df['_symbol_name'] = symbol
    return df


CONFIG = f'''
[Tester]
Expert=Yoji-MACD v1.0.ex5
Symbol=__SYMBOL__
Period=M1
Optimization=2
Model=1
FromDate=__START_DATE__
ToDate=__END_DATE__
ForwardMode=4
ForwardDate=__FORWARD_DATE__
ForwardMode=2
Deposit=3000
Currency=USD
ProfitInPips=0
Leverage=500
ExecutionMode=120
OptimizationCriterion=6
UseCloud=0
Report=reports\\__REPORT__.xml
ReplaceReport=1
ShutdownTerminal=1


[TesterInputs]
; Generic Setting
_risk_type=0
_risk_value=50.0||10||1.0||100.0||N
_close_all_button=true
_min_profit=0
; Single Strategy Setting
_symbol_name=__SYMBOL__
_magic_number=__MAGIC__
_session_start=22||0||2||22||Y
_session_length=12||8||4||20||Y
_tf=16385||5||0||16385||Y
_trend_period=200||50||50||300||Y
_macd_fast=12||2||2||18||Y
_macd_slow=26||12||4||40||Y
_macd_sma=9||7||2||13||Y
_adx_period=10||10||5||15||Y
_adx_smoothing=10||10||10||50||Y
_atr_period=15||7||2||15||N
_atr_factor=2.0||0.50||0.50||5.0||Y
_rr_ratio=2.0||0.50||0.10||2.00||Y
_inverse=false||false||0||true||Y
; Portfolio Strategy
_config=__CONFIG_NAME__

'''


def read_xml(fname, magic):
    df = xml2df(fname)
    print(f'Reading XML with {len(df)} entries...')

    df = df[(df['Forward Result'] > 0.0)]
    df = df[(df['Back Result'] > 0.0)]

    df = df.drop_duplicates(subset=['Forward Result', 'Back Result', 'Profit'], keep=False)

    df['NP'] = np.floor(df['Profit'] / 500) * 500
    df = df[df['NP'] > 0]

    cols = ['Back Result', 'Forward Result']
    df['score'] = df[cols].std(axis=1)
    df = df.dropna()

    #df = df.sort_values(['NP', 'score'], ascending=(False, True,))
    df = df.sort_values(['score', 'NP'], ascending=(True, False,))

    if not df.empty:
        print(df.head())
    else:
        return None

    row = df.iloc[0].to_dict()
    row['_magic_number'] = magic
    if '_trend_period' not in row:
        row['_trend_period'] = 200
    if '_atr_period' not in row:
        row['_atr_period'] = 15
    if '_inverse' not in row:
        row['_inverse'] = 0
    else:
        row['_inverse'] = 1 if row['_inverse'] == 'true' else 0
    
    cfg = (f'{row["_symbol_name"]},'
           f'{row["_magic_number"]},'
           f'{row["_session_start"]},'
           f'{row["_session_length"]},'
           f'{row["_tf"]},'
           f'{row["_trend_period"]},'
           f'{row["_macd_fast"]},'
           f'{row["_macd_slow"]},'
           f'{row["_macd_sma"]},'
           f'{row["_adx_period"]},'
           f'{row["_adx_smoothing"]},'
           f'{row["_atr_period"]},'
           f'{row["_atr_factor"]:.2f},'
           f'{row["_rr_ratio"]:.2f},'
           f'{row["_inverse"]}')
    return cfg


def main(start_date="2021.04.01",
         end_date="2022.02.01",
         base_magic=100,
         max_span_config=1,
         range_span=6,
         run_config='run.ini',
         exp_name='exp'):

    reset_env()

    start = arrow.get(start_date)
    end = arrow.get(end_date)

    magic = base_magic + 1
    report_file = f"{exp_name}.xml"
    config_file = f"{exp_name}.cfg"

    for s in arrow.Arrow.range('month', start, end):
        e = s.shift(months=range_span)
        f = e.shift(months=-int(np.max([1, np.floor(range_span / 3)])))

        if e > end:
            break

        sd = s.strftime("%Y.%m.%d")
        #sd = start_date
        fd = f.strftime("%Y.%m.%d")
        ed = e.strftime("%Y.%m.%d")

        with open(f"{CONFIG_DIR}\\{config_file}", "a") as out:
            out.write(f"# {sd} / {fd} / {ed}\n")

        n_cfg = 0

        while n_cfg < max_span_config:

            symbol = random.choice(SYMBOLS)

            logging.info(
                f"optimisation started for {symbol}, magic={magic}, "
                f"start date={sd}, forward date={fd}, end date={ed}"
            )

            try:
                cfg = CONFIG
                cfg = cfg.replace("__SYMBOL__", symbol)
                cfg = cfg.replace("__START_DATE__", sd)
                cfg = cfg.replace("__END_DATE__", ed)
                cfg = cfg.replace("__FORWARD_DATE__", fd)
                cfg = cfg.replace("__MAGIC__", str(magic))
                cfg = cfg.replace("__REPORT__", report_file)
                cfg = cfg.replace("__CONFIG_NAME__", config_file)

                with open(run_config, 'w') as out:
                    out.write(cfg)

                cmd_out = check_output(
                    f"{BIN_PATH}\\terminal64.exe /config:{run_config}")
                res = read_xml(
                    f"{TERMINAL_DIR}\\reports\\"
                    f"{report_file}.forward.xml", magic)

                if res:
                    with open(f"{CONFIG_DIR}\\{config_file}", "a") as out:
                        out.write(f"{res}\n")
                    logging.info(f"found config: {res}")
                    magic += 1
                    n_cfg += 1

            except Exception as e:
                logging.error(e)

            except KeyboardInterrupt:
                sys.exit(1)


if __name__ == '__main__':
    fire.Fire(main)
