#property copyright "Copyright (c) 2021, Jim Geovedi."
#property link "https://jim.geovedi.com"
#property version "1.1"
#property description "Yoji-Survive"
#property script_show_inputs

#define EA_NAME "Yoji-Survive"

#include <Arrays\ArrayLong.mqh>
#include <Generic\HashSet.mqh>
#include <Generic\SortedMap.mqh>
#include <Math\Stat\Normal.mqh>
#include <Trade\AccountInfo.mqh>
#include <Trade\DealInfo.mqh>
#include <Trade\HistoryOrderInfo.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\Trade.mqh>

CAccountInfo account;
CDealInfo deal_info;
COrderInfo order_info;
CPositionInfo position_info;
CSymbolInfo symbol_info;
CTrade trade;

enum ENUM_RECOVERY_TARGET {
  ALL_POSITIONS,
  LARGE_LOSS,
};

enum ENUM_DISTANCE_TARGET {
  TARGET_ATR,
  TARGET_PRICE,
  TARGET_FRACTION,
};

input ulong _magic_number = 0;                             // Magic Number
input ENUM_RECOVERY_TARGET _recovery_type = ALL_POSITIONS; // Recovery Type
input ENUM_POSITION_TYPE _pos_type = POSITION_TYPE_BUY;    // Position Type
input double _distance_value = 1.0;                        // Distance Value
input ENUM_DISTANCE_TARGET _distance_type = TARGET_ATR;    // Distance Type
input double _profit_target = 10;                          // Profit Target ($)

int atr_handle;
int volume_digits;
string comment_string = "RECOVERY";

/*
 * Core Strategy
 */

void TryToSurvive() {
  symbol_info.Name(_Symbol);
  symbol_info.RefreshRates();

  ENUM_ORDER_TYPE order_type = (_pos_type == POSITION_TYPE_BUY)
                                   ? ORDER_TYPE_BUY //
                                   : ORDER_TYPE_SELL;
  double price_current = (_pos_type == POSITION_TYPE_BUY) ? symbol_info.Ask() //
                                                          : symbol_info.Bid();
  double large_loss = 0;
  ulong tickets[];
  double volumes[], prices[];

  int size = 0;
  double price_target = 0;

  for (int i = PositionsTotal() - 1; i >= 0; i--) {
    if (position_info.SelectByIndex(i)) {
      if (_magic_number > 0 && position_info.Magic() != _magic_number)
        continue;

      if ((position_info.Symbol() == _Symbol) &&
          position_info.PositionType() == _pos_type) {

        ulong pos_ticket = position_info.Ticket();
        double pos_price = position_info.PriceOpen();
        double pos_volume = position_info.Volume();
        double pos_profit = position_info.Profit() + position_info.Swap() +
                            (2 * position_info.Commission());

        size = ArraySize(tickets);

        if (_recovery_type == LARGE_LOSS) {
          if (large_loss == 0 || large_loss > pos_profit) {
            large_loss = pos_profit;
            price_target = pos_price;

            if (size == 0) {
              ArrayResize(tickets, size + 1);
              ArrayResize(volumes, size + 1);
              ArrayResize(prices, size + 1);
            }
            tickets[0] = pos_ticket;
            volumes[0] = pos_volume;
            prices[0] = pos_price;
          }
        }

        if (_recovery_type == ALL_POSITIONS) {
          ArrayResize(tickets, size + 1);
          ArrayResize(volumes, size + 1);
          ArrayResize(prices, size + 1);
          tickets[size] = pos_ticket;
          volumes[size] = pos_volume;
          prices[size] = pos_price;
        }
      }
    }
  }

  Print("Tickets:");
  ArrayPrint(tickets);

  Print("Volumes:");
  ArrayPrint(volumes);

  Print("Prices:");
  ArrayPrint(prices);


  // recovery target price
  if (_distance_type == TARGET_PRICE) {
    price_target = _distance_value;
  } else if (_distance_type == TARGET_FRACTION) {
    if (_pos_type == POSITION_TYPE_BUY) {
      double dist = MathMax(prices) - price_current;
      price_target = price_current + (_distance_value * dist);
    } else {
      double dist = price_current - MathMin(prices);
      price_target = price_current - (_distance_value * dist);
    }
  } else {
    double atr[];

    if (!GetArray(atr_handle, 0, 0, 1, atr)) {
      PrintFormat("[ERROR] %s(%I64d): Unable to read ATR data from indicator!",
                  __FUNCTION__, _magic_number);
      return;
    }

    double multiplier = _distance_value;
    double distance = atr[0] * multiplier;
    price_target = (_pos_type == POSITION_TYPE_BUY)
                       ? symbol_info.Ask() + distance
                       : symbol_info.Bid() - distance;
  }

  price_target = symbol_info.NormalizePrice(price_target);

  // sanity checks
  if (price_target == 0) {
    PrintFormat("[DEBUG] %s(%I64d): Target price is ZERO!", __FUNCTION__,
                _magic_number);
    return;
  }

  if (_pos_type == POSITION_TYPE_BUY && price_target <= price_current) {
    PrintFormat("[DEBUG] %s(%I64d): Target price (%f) is equal or below "
                "current price (%f)!",
                __FUNCTION__, _magic_number, price_target, price_current);
    return;
  }

  if (_pos_type == POSITION_TYPE_SELL && price_target >= price_current) {
    PrintFormat("[DEBUG] %s(%I64d): Target price (%f) is equal or above "
                "current price (%f)!",
                __FUNCTION__, _magic_number, price_target, price_current);
    return;
  }

  // recovery target profit
  double profit_target = 0;

  for (int i = 0; i < ArraySize(volumes); i++) {
    profit_target += account.OrderProfitCheck(_Symbol, order_type,   //
                                              volumes[i], prices[i], //
                                              price_target);
  }

  if (profit_target >= 0) {
    PrintFormat("[DEBUG] %s(%I64d): Profit target (%f) is equal or above ZERO!",
                __FUNCTION__, _magic_number, profit_target);
    return;
  }

  profit_target = MathAbs(profit_target) + _profit_target;

  double volume = 0;

  double loss = account.OrderProfitCheck(_Symbol, order_type, 1.0,
                                         price_current, price_target);

  volume = MathMax(profit_target / MathAbs(loss), 0.0);
  volume = NormalizeVolume(_Symbol, volume);

  if (volume <= 0) {
    PrintFormat("[DEBUG] %s(%I64d): Volume (%f) is equal or below ZERO!",
                __FUNCTION__, _magic_number, volume);
    return;
  }

  bool success = false;
  success = PrepareOrder(_Symbol, _magic_number, order_type, volume, price_current, 0,
            price_target, comment_string);

  if (!success) {
    PrintFormat("[ERROR] %s(%I64d): Unable to open recovery position!",
                __FUNCTION__, _magic_number);
    return;
  } else {
    for (int i = 0; i < ArraySize(tickets); i++) {
      success = trade.PositionModify(tickets[i], 0, price_target);
    }
  }
}

/*
 * Aux
 */

bool GetArray(const int handle, const int buffer, const int start_pos,
              const int count, double &array[]) {
  if (!ArrayIsDynamic(array)) {
    PrintFormat("[DEBUG] %s(%I64d): Not a dynamic array!", __FUNCTION__,
                _magic_number);
    return (false);
  }

  ArrayFree(array);

  ResetLastError();

  if (CopyBuffer(handle, buffer, start_pos, count, array) <= 0) {
    PrintFormat("[ERROR] %s(%I64d): Failed to copy data from the indicator. "
                "Error code: %d",
                __FUNCTION__, _magic_number, GetLastError());
    return (false);
  }

  return (true);
}

double NormalizeVolume(string symbol, double volume) {
  symbol_info.Name(symbol);
  symbol_info.RefreshRates();

  double max_volume = symbol_info.LotsMax();
  double min_volume = symbol_info.LotsMin();
  double step_volume = symbol_info.LotsStep();

  volume = MathMin(MathMax(volume, min_volume), max_volume);
  volume = MathCeil(volume / step_volume) * step_volume;

  return (NormalizeDouble(volume, volume_digits));
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

double GetVolumeTotal(string symbol) {
  double count = 0;

  for (int i = PositionsTotal() - 1; i >= 0; i--) {
    if (position_info.SelectByIndex(i)) {
      if (position_info.Symbol() == symbol) {
        count += position_info.Volume();
      }
    }
  }
  return (count);
}

bool PrepareOrder(string symbol, ulong magic_number, ENUM_ORDER_TYPE order,
               double volume, double price = 0.0, double sl = 0.0,
               double tp = 0.0, string comment = "") {
  bool success = false;

  if (volume == 0.0) {
    PrintFormat("[ERROR] %s(%I64d): Unable to send order=%s for symbol=%s "
                "with volume=%f and SL=%f",
                __FUNCTION__, _magic_number, EnumToString(order), symbol,
                volume, sl);
    return (success);
  }

  symbol_info.Name(symbol);
  symbol_info.RefreshRates();

  double volume_total = GetVolumeTotal(symbol);
  double volume_limit = symbol_info.LotsLimit();

  if (volume_total + volume > volume_limit && volume_limit > 0) {
    PrintFormat(
        "[WARNING] %s(%I64d): Total volume=%s is larger than volume limt=%s",
        __FUNCTION__, _magic_number,
        DoubleToString(volume + volume_total, volume_digits),
        DoubleToString(volume_limit, volume_digits));
  }

  if (price == 0.0 && order == ORDER_TYPE_BUY) {
    price = symbol_info.Ask();
  } else if (price == 0.0 && order == ORDER_TYPE_SELL) {
    price = symbol_info.Bid();
  }

  price = symbol_info.NormalizePrice(price);
  sl = symbol_info.NormalizePrice(sl);
  tp = symbol_info.NormalizePrice(tp);

  double free_margin = account.FreeMarginCheck(symbol, order, //
                                               volume, price);
  if (free_margin <= 0.0) {
    PrintFormat(
        "[DEBUG] %s(%I64d): Order=%s, Symbol=%s, Volume=%s, Price=%f. Free "
        "margin=%.2f",
        __FUNCTION__, _magic_number, EnumToString(order), symbol,
        DoubleToString(volume, volume_digits), price, free_margin);
    return (success);
  }

  double max_volume = symbol_info.LotsMax();
  double step_volume = symbol_info.LotsStep();

  if (volume > max_volume) {
    double size = 0.0;
    for (int split = (int)MathCeil(volume / max_volume); split > 0; split--) {
      if (split == 1)
        size = volume;
      else {
        size = MathCeil(volume / split / step_volume) * step_volume;
        volume -= size;
      }
      success = SendOrder(symbol, magic_number, order, size, price, sl, tp, comment);
    }
  } else {
    success = SendOrder(symbol, magic_number, order, volume, price, sl, tp, comment);
  }

  return (success);
}

bool SendOrder(string symbol, ulong magic_number, ENUM_ORDER_TYPE order,
                   double volume, double price = 0.0, double sl = 0.0,
                   double tp = 0.0, string comment = "") {
  bool success = false;

  trade.SetMarginMode();
  trade.SetDeviationInPoints(20);
  trade.SetExpertMagicNumber(magic_number);
  trade.SetTypeFillingBySymbol(symbol);

  switch (order) {
  case ORDER_TYPE_BUY:
    success = trade.Buy(volume, symbol, price, sl, tp, comment);
    break;
  case ORDER_TYPE_SELL:
    success = trade.Sell(volume, symbol, price, sl, tp, comment);
    break;
  case ORDER_TYPE_BUY_STOP:
    success = trade.BuyStop(volume, price, symbol, sl, tp, //
                            ORDER_TIME_GTC, 0, comment);
    break;
  case ORDER_TYPE_SELL_STOP:
    success = trade.SellStop(volume, price, symbol, sl, tp, //
                             ORDER_TIME_GTC, 0, comment);
    break;
  case ORDER_TYPE_BUY_LIMIT:
    success = trade.BuyLimit(volume, price, symbol, sl, tp, //
                             ORDER_TIME_GTC, 0, comment);
    break;
  case ORDER_TYPE_SELL_LIMIT:
    success = trade.SellLimit(volume, price, symbol, sl, tp, //
                              ORDER_TIME_GTC, 0, comment);
    break;
  default:
    break;
  }

  if (success) {
    PrintFormat(
        "[DEBUG] %s(%I64d): %s - %s (%d) at %f. Volume: %s, SL: %f, TP: %f",
        __FUNCTION__, magic_number, EnumToString(order), symbol, //
        magic_number, price, DoubleToString(volume, volume_digits), sl, tp);
  } else {
    PrintFormat("[ERROR] %s(%I64d): Unable to submit %s order. Error: %s", //
                __FUNCTION__, magic_number, EnumToString(order),
                trade.ResultRetcodeDescription());
  }

  return (success);
}

void OnStart() {
  atr_handle = iMA(_Symbol, PERIOD_CURRENT, 50, //
                   0, MODE_EMA, iATR(_Symbol, PERIOD_CURRENT, 14));
  if (atr_handle == INVALID_HANDLE) {
    Alert("[WARNING] Unable to initiate ATR indicator!");
    return;
  }

  symbol_info.Name(_Symbol);
  volume_digits = GetDigits(symbol_info.LotsStep());

  TryToSurvive();
}
