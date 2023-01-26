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
