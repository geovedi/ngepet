#define MAX_WAITING_TIME 10000

uint StartTickCount = 0;

bool CheckLoadHistory(const string symbol,
                      const ENUM_TIMEFRAMES period,
                      const int size,
                      bool print_info = true) {
  if (MQL5InfoInteger(MQL5_PROGRAM_TYPE) == PROGRAM_INDICATOR &&
      Period() == period && Symbol() == symbol)
    return (true);

  if (size > TerminalInfoInteger(TERMINAL_MAXBARS)) {
    printf(__FUNCTION__ + ": requested too much data (%d)", size);
    return (false);
  }

  StartTickCount = GetTickCount();
  if (CheckTerminalHistory(symbol, period, size) ||
      CheckServerHistory(symbol, period, size)) {
    if (print_info) {
      double length = (GetTickCount() - StartTickCount) / 1000.0;
      if (length > 0.1)
        Print(symbol, ", ", EnumToString(period),
              ": history synchronized within ", DoubleToString(length, 1),
              " sec");
    }
    return (true);
  }

  if (print_info)
    Print(symbol, ", ", EnumToString(period),
          ": ERROR synchronizing history!!!");

  return (false);
}

bool CheckTerminalHistory(const string symbol,
                          const ENUM_TIMEFRAMES period,
                          const int size) {
  if (Bars(symbol, period) >= size)
    return (true);
  datetime times[1];
  long bars = 0;

  if (SeriesInfoInteger(symbol, PERIOD_M1, SERIES_BARS_COUNT, bars)) {
    if (bars > size * PeriodSeconds(period) / 60) {
      CopyTime(symbol, period, size - 1, 1, times);
      if (SeriesInfoInteger(symbol, period, SERIES_BARS_COUNT, bars)) {
        if (bars >= size)
          return (true);
      }
    }
  }

  return (false);
}

bool CheckServerHistory(const string symbol,
                        const ENUM_TIMEFRAMES period,
                        const int size) {
  datetime first_server_date = 0;
  while (!SeriesInfoInteger(symbol, PERIOD_M1, SERIES_SERVER_FIRSTDATE,
                            first_server_date) &&
         !IsStoppedExt())
    Sleep(5);

  if (first_server_date > TimeCurrent() - size * PeriodSeconds(period))
    return (false);

  int fail_cnt = 0;
  datetime times[1];
  while (!IsStoppedExt()) {
    while (!SeriesInfoInteger(symbol, period, SERIES_SYNCHRONIZED) &&
           !IsStoppedExt())
      Sleep(5);
    int bars = Bars(symbol, period);
    if (bars > size)
      return (true);
    if (CopyTime(symbol, period, size - 1, 1, times) == 1) {
      return (true);
    } else {
      if (++fail_cnt >= 100)
        return (false);
      Sleep(10);
    }
  }

  return (false);
}

bool IsStoppedExt() {
  if (IsStopped())
    return (true);

  if (GetTickCount() - StartTickCount > MAX_WAITING_TIME)
    return (true);

  return (false);
}
