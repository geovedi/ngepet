import rapidjson
import fire
import pandas as pd


"""

# https://strategyquant.com/doc/quantanalyzer/formats-supported-in-quantanalyzer/
# add this spec to \\settings\\plugins\\LoaderGeneralCsv\\GeneralCSVImport.ini

Format.5.SkipRow=1
Format.5.Separator=,
Format.5.DateFormat=yyyy-MM-dd HH:mm:ssX
Format.5.LineFormat=Ticket,OpenTime,CloseTime,Symbol,Action,Size,OpenPrice,ClosePrice,PL,Comment

"""

def main(input_file, fiat_file=None):
    data = rapidjson.load(open(input_file, "r"))

    columns = [
        "Ticket",
        "OpenTime",
        "CloseTime",
        "Symbol",
        "Action",
        "Size",
        "OpenPrice",
        "ClosePrice",
        "PL",
        "Comment",
    ]

    if fiat_file:
        fiat = pd.read_feather(fiat_file)
        fiat["date"] = pd.to_datetime(fiat["date"], unit="s")
        fiat = fiat.set_index("date")

    for strat_data in data["strategy_comparison"]:
        results = list()
        key = strat_data["key"]

        for idx, trade in enumerate(data["strategy"][key]["trades"]):
            if trade["exit_reason"] == "force_exit":
                continue

            if fiat_file:
                fiat_date = trade["close_date"].split(" ")[0]
                fiat_value = fiat.loc[fiat_date, "open"]
            else:
                fiat_value = 1.0

            results.append(
                {
                    "Ticket": idx,
                    "OpenTime": trade["open_date"],
                    "CloseTime": trade["close_date"],
                    "Symbol": trade["pair"],
                    "Action": "short" if trade["is_short"] else "long",
                    "Size": trade["amount"],
                    "OpenPrice": trade["open_rate"],
                    "ClosePrice": trade["close_rate"],
                    "PL": trade["profit_abs"] * fiat_value,
                    "Comment": "{0}|{1}".format(
                        trade["enter_tag"], trade["exit_reason"]
                    ),
                }
            )

        df = pd.DataFrame(results, columns=columns)
        df.to_csv(f"{key}.csv", index=False, float_format="%f")


if __name__ == "__main__":
    fire.Fire(main)
