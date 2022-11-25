import os
import sys
import shutil
import re
import fire

from os.path import exists, isfile
from glob import glob
from pathlib import Path
from collections import defaultdict
from itertools import combinations
from random import choice, sample, shuffle
from subprocess import check_output

BIN_PATH = "C:\\Program Files\\MT5.01"
TERMINAL_EXE = f'{BIN_PATH}\\terminal64.exe'
TERMINAL_ID = 'FA3BEB427BA1759C8F7D1F958883B017'
TERMINAL_BASE_DIR = 'C:\\Users\\Administrator\\AppData\\Roaming\\MetaQuotes'

TERMINAL_DIR = f'{TERMINAL_BASE_DIR}\\Terminal\\{TERMINAL_ID}'
TESTER_DIR = f'{TERMINAL_BASE_DIR}\\Tester\\{TERMINAL_ID}'

NORM_SYMBOLS = {
    'VIX10': 'Volatility 10 Index',
    'VIX25': 'Volatility 25 Index',
    'VIX50': 'Volatility 50 Index',
    'VIX75': 'Volatility 75 Index',
    'VIX100': 'Volatility 100 Index',
}


def clean_cache_dir():
    for fn in glob(f'{TERMINAL_DIR}\\Tester\\cache\\*', recursive=True):
        print(f'!!! Deleting {fn}')
        os.remove(fn)


def clean_reports_dir(clean_up, ea_dir, reset=False):
    for fn in glob(f'{TERMINAL_DIR}\\reports\\{ea_dir}\\**', recursive=True):
        if not isfile(fn): continue
        if reset:
            os.remove(fn)
        elif clean_up and os.stat(fn).st_size < 1024 * 100:
            print(f'!!! Deleting {fn}')
            os.remove(fn)


def main(ea_dir, 
         opt_cfg='sqx_tester.ini',
         tester_cfg='tester.ini',
         timeout=0,
         clean_up=False,
         clean_start=False):

    clean_cache_dir()
    clean_reports_dir(clean_up, ea_dir, clean_start)

    for ex5_path in glob(f'{TERMINAL_DIR}\\MQL5\\Experts\\{ea_dir}\\**\\*.ex5', recursive=True):
        ex5_normpath = os.path.normpath(ex5_path)
        ex5_listpath = ex5_normpath.split(os.sep)

        ex5_name = os.sep.join(ex5_listpath[-2:]).replace('.ex5', '')
        #ex5_symbol = ex5_listpath[-2]
        #ex5_tf = ex5_listpath[-3]

        #ex5_name = ex5_listpath[-1].replace('.ex5', '')
        if '_' in ex5_listpath[-1]:
            ex5_tf, ex5_symbol, _ = ex5_listpath[-1].split('_')

        else:
            #ex5_tf, ex5_symbol = 'd1', 'EURUSD'
            ex5_tf, ex5_symbol = 'h4', 'vix10'

        report_dir = f'{TERMINAL_DIR}\\reports\\{ea_dir}'

        try:
            os.makedirs(f'{report_dir}')
        except Exception as e:
            #print(f'Unable to create directory {report_dir}')
            pass

        if exists(f'{TERMINAL_DIR}\\reports\\{ex5_name}.html'):
            print(f'*** Skip {ex5_name}')
            continue

        sym = ex5_symbol.upper()

        cfg = open(opt_cfg, 'r').read()
        cfg = cfg.replace('__EXPERT__', ex5_name)
        cfg = cfg.replace('__SYMBOL__', NORM_SYMBOLS.get(sym, sym))
        cfg = cfg.replace('__PERIOD__', ex5_tf.upper())

        with open(tester_cfg, 'w') as out:
            out.write(cfg)

        try:
            print('Processing', ex5_name)
            if timeout > 0:
                _ = check_output(f'{TERMINAL_EXE} /config:{tester_cfg}' , timeout=timeout)
            else:
                 _ = check_output(f'{TERMINAL_EXE} /config:{tester_cfg}')

            for png in glob(f'{report_dir}\\*.png'):
                os.remove(png)

        except Exception as e:
            print('!!! timeout exceeded')

    clean_cache_dir()
    clean_reports_dir(clean_up, ea_dir)

if __name__ == '__main__':
    fire.Fire(main)
