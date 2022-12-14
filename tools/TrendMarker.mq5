

int bar;
int supertrend_handle;
bool is_trending;
bool is_trending_prev = WRONG_VALUE;
ulong magic_number = 1000;
ENUM_TIMEFRAMES timeframe = PERIOD_D1;

int OnInit() {
  supertrend_handle = iCustom(NULL, timeframe, "SqSuperTrend", 1, 50, 10.0);

  if (!EventSetTimer(30)) {
    PrintFormat("[ERROR] %I64d/%s: Unable to activate timer. Error: %s",
                magic_number, __FUNCTION__, GetLastError());
    return (INIT_FAILED);
  }

  return (INIT_SUCCEEDED);
}

void OnTimer() {
  if (bar == Bars(_Symbol, timeframe))
    return;

  double supertrend[];
  GetArray(supertrend_handle, 0, 0, 2, supertrend);

  MqlRates rates[];
  ArraySetAsSeries(rates, true);
  int copied = CopyRates(_Symbol, timeframe, 0, 2, rates);

  if (copied <= 0) {
    PrintFormat("[DEBUG] %I64d/%s: Could not get last candle", magic_number,
                __FUNCTION__);
    return;
  }

  if (rates[1].close > supertrend[1])
    is_trending = true;
  else
    is_trending = false;

  if (is_trending_prev != is_trending) {
    is_trending_prev = is_trending;
    PrintFormat("%s: %s", TimeToString(TimeTradeServer()),
                is_trending ? "UPTREND" : "DOWNTREND");
  }

  bar = Bars(_Symbol, timeframe);
}

bool GetArray(const int handle, const int buffer, const int start_pos,
              const int count, double &array[]) {
  if (!ArrayIsDynamic(array)) {
    PrintFormat("[DEBUG] %I64d/%s: Not a dynamic array!", magic_number,
                __FUNCTION__);
    return (false);
  }

  ArrayFree(array);

  ResetLastError();

  if (CopyBuffer(handle, buffer, start_pos, count, array) <= 0) {
    PrintFormat("[ERROR] %I64d/%s: Failed to copy data from the indicator. "
                "Error code: %d",
                magic_number, __FUNCTION__, GetLastError());
    return (false);
  }

  return (true);
}
