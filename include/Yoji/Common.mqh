#include <Trade\AccountInfo.mqh>
#include <Trade\DealInfo.mqh>
#include <Trade\HistoryOrderInfo.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\Trade.mqh>

CAccountInfo accountInfo;
CDealInfo dealInfo;
COrderInfo orderInfo;
CPositionInfo positionInfo;
CSymbolInfo symbolInfo;
CTrade trade;

bool HasPosition(string symbol, ulong magic) {
  for (int i = PositionsTotal() - 1; i >= 0; i--) {
    if (positionInfo.SelectByIndex(i)) {
      if (positionInfo.Magic() == magic && positionInfo.Symbol() == symbol) {
        return (true);
      }
    }
  }
  return (false);
}

void PrepareOrder(string symbol, ulong magic, ENUM_ORDER_TYPE order,
                  double volume, double price = 0.0, double sl = 0.0,
                  double tp = 0.0, string comment = "") {
  symbolInfo.Name(symbol);
  double volumeTotal = GetVolumeTotal(symbol);
  double volumeLimit = symbolInfo.LotsLimit();

  if (volumeTotal + volume > volumeLimit && volumeLimit > 0)
    return;

  if (price == 0.0) {
    if (order == ORDER_TYPE_BUY)
      price = symbolInfo.Ask();
    if (order == ORDER_TYPE_SELL)
      price = symbolInfo.Bid();
  }

  price = symbolInfo.NormalizePrice(price);
  sl = symbolInfo.NormalizePrice(sl);
  tp = symbolInfo.NormalizePrice(tp);

  double freeMargin = accountInfo.FreeMarginCheck(symbol, order, volume, price);
  if (freeMargin <= 0.0)
    return;

  double maxVolume = symbolInfo.LotsMax();
  double minVolume = symbolInfo.LotsMin();
  double stepVolume = symbolInfo.LotsStep();

  if (volume > maxVolume) {
    double size = 0.0;
    for (int split = (int)MathCeil(volume / maxVolume); split > 0; split--) {
      if (split == 1) {
        size = volume;
      } else {
        size = MathCeil(volume / split / stepVolume) * stepVolume;
        volume -= size;
      }
      SendOrder(symbol, magic, order, size, price, sl, tp, comment);
    }
  } else {
    SendOrder(symbol, magic, order, volume, price, sl, tp, comment);
  }
}

bool SendOrder(string symbol, ulong magic, ENUM_ORDER_TYPE order, double volume,
               double price = 0.0, double sl = 0.0, double tp = 0.0,
               string comment = "") {
  trade.SetMarginMode();
  trade.SetDeviationInPoints(20);
  trade.SetTypeFillingBySymbol(symbol);
  trade.SetExpertMagicNumber(magic);
  symbolInfo.Name(symbol);

  bool success = false;

  switch (order) {
  case ORDER_TYPE_BUY:
    success = trade.Buy(volume, symbol, price, sl, tp, comment);
    break;
  case ORDER_TYPE_SELL:
    success = trade.Sell(volume, symbol, price, sl, tp, comment);
    break;
  case ORDER_TYPE_BUY_STOP:
    success = trade.BuyStop(volume, price, symbol, sl, tp, ORDER_TIME_GTC, 0,
                            comment);
    break;
  case ORDER_TYPE_SELL_STOP:
    success = trade.SellStop(volume, price, symbol, sl, tp, ORDER_TIME_GTC, 0,
                             comment);
    break;
  case ORDER_TYPE_BUY_LIMIT:
    success = trade.BuyLimit(volume, price, symbol, sl, tp, ORDER_TIME_GTC, 0,
                             comment);
    break;
  case ORDER_TYPE_SELL_LIMIT:
    success = trade.SellLimit(volume, price, symbol, sl, tp, ORDER_TIME_GTC, 0,
                              comment);
    break;
  default:
    break;
  }

  return (success);
}

double GetBaseVolume(string symbol, double distance, double risk) {
  symbolInfo.Name(symbol);
  double loss = accountInfo.OrderProfitCheck(symbol, ORDER_TYPE_BUY, 1.0,
                                             symbolInfo.Ask(),
                                             symbolInfo.Ask() - distance);
  if (!MathIsValidNumber(loss) || loss >= 0)
    return (0.0);
  double volume = MathMax(risk / MathAbs(loss), 0.0);
  return NormalizeVolume(symbol, volume);
}

double GetVolumeTotal(string symbol) {
  double count = 0;

  for (int i = PositionsTotal() - 1; i >= 0; i--) {
    if (positionInfo.SelectByIndex(i)) {
      if (positionInfo.Symbol() == symbol) {
        count += positionInfo.Volume();
      }
    }
  }
  return (count);
}

double NormalizeVolume(string symbol, double volume) {
  symbolInfo.Name(symbol);
  double maxVolume = symbolInfo.LotsMax();
  double minVolume = symbolInfo.LotsMin();
  double stepVolume = symbolInfo.LotsStep();
  int volumeDigits = GetDigits(stepVolume);

  volume = MathCeil(volume / stepVolume) * stepVolume;
  volume = MathMax(MathMin(volume, maxVolume), minVolume);

  return NormalizeDouble(volume, volumeDigits);
}

void CloseAllPositions(string symbol, ulong magic) {
  for (int i = PositionsTotal() - 1; i >= 0; i--) {
    if (positionInfo.SelectByIndex(i)) {
      if (positionInfo.Magic() == magic && positionInfo.Symbol() == symbol) {
        trade.PositionClose(positionInfo.Ticket());
      }
    }
  }
}

void CloseAllPositions() {
  for (int i = PositionsTotal() - 1; i >= 0; i--) {
    if (positionInfo.SelectByIndex(i)) {
      trade.PositionClose(positionInfo.Ticket());
    }
  }
}

int GetDigits(double var, int digits = 8) {
  string value = DoubleToString(var, digits); // 0.01000000
  int pad = StringLen(value) - 1;
  while (StringGetCharacter(value, pad) == '0') {
    digits--;
    pad--;
  }                // 0.01
  return (digits); // 2
}

bool GetArray(const int handle, const int buffer, const int start_pos,
              const int count, double &array[]) {
  if (!ArrayIsDynamic(array))
    return (false);
  ArrayFree(array);
  ResetLastError();
  if (CopyBuffer(handle, buffer, start_pos, count, array) <= 0)
    return (false);
  return (true);
}

bool GetRates(string symbol, ENUM_TIMEFRAMES timeframe, int count,
              MqlRates &rates[]) {
  ArraySetAsSeries(rates, true);
  if (CopyRates(symbol, timeframe, 0, count, rates) <= 0)
    return (false);
  return (true);
}

void DisplayEmergencyButton() {
  ObjectCreate(0, "EmergencyStop", OBJ_BUTTON, 0, 0, 0);
  ObjectSetString(0, "EmergencyStop", OBJPROP_TEXT, "Emergency Stop");
  ObjectSetInteger(0, "EmergencyStop", OBJPROP_XDISTANCE, 25);
  ObjectSetInteger(0, "EmergencyStop", OBJPROP_YDISTANCE, 50);
  ObjectSetInteger(0, "EmergencyStop", OBJPROP_XSIZE, 125);
  ObjectSetInteger(0, "EmergencyStop", OBJPROP_YSIZE, 25);
  ObjectSetInteger(0, "EmergencyStop", OBJPROP_COLOR, White);
  ObjectSetInteger(0, "EmergencyStop", OBJPROP_BGCOLOR, Red);
  ObjectSetInteger(0, "EmergencyStop", OBJPROP_BORDER_COLOR, Red);
  ObjectSetInteger(0, "EmergencyStop", OBJPROP_BORDER_TYPE, BORDER_FLAT);
  ObjectSetInteger(0, "EmergencyStop", OBJPROP_HIDDEN, true);
  ObjectSetInteger(0, "EmergencyStop", OBJPROP_STATE, false);
  ObjectSetInteger(0, "EmergencyStop", OBJPROP_FONTSIZE, 9);
  ObjectSetInteger(0, "EmergencyStop", OBJPROP_CORNER, CORNER_LEFT_LOWER);
  ObjectSetInteger(0, "EmergencyStop", OBJPROP_ANCHOR, ANCHOR_LEFT_LOWER);
}

void OnChartEvent(const int id, const long &lparam, const double &dparam,
                  const string &sparam) {
  if (id == CHARTEVENT_OBJECT_CLICK && sparam == "EmergencyStop") {
    CloseAllPositions();
    ObjectSetInteger(0, "EmergencyStop", OBJPROP_STATE, false);
    ExpertRemove();
  }
}

double CalculateLinearRegressionRatio() {
  double ret = 0.0;

  double array[];
  double trades_volume;
  GetTradeResultsToArray(array, trades_volume);
  int trades = ArraySize(array);

  if (trades < 10)
    return (0);

  double average_pl = 0;
  for (int i = 0; i < ArraySize(array); i++)
    average_pl += array[i];
  average_pl /= trades;

  if (MQLInfoInteger(MQL_TESTER) && !MQLInfoInteger(MQL_OPTIMIZATION))
    PrintFormat("%s: Trades=%d, Average profit=%.2f", __FUNCTION__, trades,
                average_pl);

  double a, b, std_error;
  double chart[];
  if (!CalculateLinearRegression(array, chart, a, b))
    return (0);

  if (!CalculateStdError(chart, a, b, std_error))
    return (0);

  ret = (std_error == 0.0) ? a * trades : a * trades / std_error;

  return (ret);
}

bool GetTradeResultsToArray(double &pl_results[], double &volume) {
  if (!HistorySelect(0, TimeCurrent()))
    return (false);
  uint total_deals = HistoryDealsTotal();
  volume = 0;

  ArrayResize(pl_results, total_deals);

  int counter = 0;
  ulong ticket_history_deal = 0;

  for (uint i = 0; i < total_deals; i++) {
    if ((ticket_history_deal = HistoryDealGetTicket(i)) > 0) {
      ENUM_DEAL_ENTRY deal_entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(
          ticket_history_deal, DEAL_ENTRY);
      long deal_type = HistoryDealGetInteger(ticket_history_deal, DEAL_TYPE);
      double deal_profit =
          HistoryDealGetDouble(ticket_history_deal, DEAL_PROFIT);
      double deal_volume =
          HistoryDealGetDouble(ticket_history_deal, DEAL_VOLUME);
      if ((deal_type != DEAL_TYPE_BUY) && (deal_type != DEAL_TYPE_SELL))
        continue;
      if (deal_entry != DEAL_ENTRY_IN) {
        pl_results[counter] = deal_profit;
        volume += deal_volume;
        counter++;
      }
    }
  }
  ArrayResize(pl_results, counter);
  return (true);
}

bool CalculateLinearRegression(double &change[], double &chartline[],
                               double &a_coef, double &b_coef) {
  if (ArraySize(change) < 3)
    return (false);

  int N = ArraySize(change);
  ArrayResize(chartline, N);
  chartline[0] = change[0];
  for (int i = 1; i < N; i++)
    chartline[i] = chartline[i - 1] + change[i];
  double x = 0, y = 0, x2 = 0, xy = 0;
  for (int i = 0; i < N; i++) {
    x = x + i;
    y = y + chartline[i];
    xy = xy + i * chartline[i];
    x2 = x2 + i * i;
  }
  a_coef = (N * xy - x * y) / (N * x2 - x * x);
  b_coef = (y - a_coef * x) / N;

  return (true);
}

bool CalculateStdError(double &data[], double a_coef, double b_coef,
                       double &std_err) {
  double error = 0;
  int N = ArraySize(data);
  if (N <= 2)
    return (false);
  for (int i = 0; i < N; i++)
    error += MathPow(a_coef * i + b_coef - data[i], 2);
  std_err = MathSqrt(error / (N - 2));
  return (true);
}
