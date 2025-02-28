
from datetime import datetime
import sys
import MetaTrader5 as mt5
import pandas as pd
import pytz
import fire


utc = pytz.timezone("Etc/UTC")

def convert_timeframe(timeframe):
	tf = {
		"M1": mt5.TIMEFRAME_M1,
		"H1": mt5.TIMEFRAME_H1,
		"H4": mt5.TIMEFRAME_H4,
		"D1": mt5.TIMEFRAME_D1,
	}
	return tf.get(timeframe, mt5.TIMEFRAME_M1)

def copy_rates(symbol, timeframe="M1", year_from=2000):
	date_from = datetime(year_from, 1, 1, tzinfo=utc)
	date_now = datetime.now(tz=utc)
	rates = mt5.copy_rates_range(symbol.name, convert_timeframe(timeframe), date_from, date_now)
	df = pd.DataFrame(rates)
	df["time"] = pd.to_datetime(df["time"], unit="s")
	outdir = '/'.join(symbol.path.split('\\')[:-1])
	df.to_csv(f"{outdir}/{symbol.name}.csv")
	print(f"...saving {symbol.path} rates from {df['time'].iloc[0]}")


def main():
	if not mt5.initialize():
	    print(f"initialize() failed, error code = {mt5.last_error()}", )
	    sys.exit()

	symbols = mt5.symbols_get()
	for symbol in symbols:
		if 'Nasdaq' in symbol.path:
			copy_rates(symbol)

	mt5.shutdown()


if __name__ == '__main__':
	fire.Fire(main)
