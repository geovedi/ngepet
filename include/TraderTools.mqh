//+------------------------------------------------------------------+
//|                                                   TradeTools.mqh |
//|                                      Copyright 2021, Jim Geovedi |
//|                                          https://jim.geovedi.com |
//+------------------------------------------------------------------+

#include <Trade\AccountInfo.mqh>
#include <Trade\OrderInfo.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\Trade.mqh>

CAccountInfo account;
COrderInfo order_info;
CPositionInfo position_info;
CSymbolInfo symbol_info;
CTrade trade;
CDealInfo deal_info;

void GetLastNDeals(double &trades[], ulong magic = 0, int limit = 20) {
  HistorySelect(INT_MIN, INT_MAX);

  for (int i = HistoryDealsTotal() - 1; i >= 0; i--) {
    deal_info.Ticket(HistoryDealGetTicket(i));

    if (magic > 0 && deal_info.Magic() != magic)
      continue;

    if (deal_info.Entry() == DEAL_ENTRY_OUT) {
      double profit = deal_info.Profit() //
                      + deal_info.Swap() //
                      + (2 * deal_info.Commission());

      int size = ArraySize(trades);
      ArrayResize(trades, size + 1);
      trades[size] = profit;
      if (size + 1 > limit)
        break;
    }
  }
}

void GetLastDeals(double &trades[], datetime start, datetime end, string symbol,
                  ulong magic_number) {
  HistorySelect(start, end);

  for (int i = HistoryDealsTotal() - 1; i >= 0; i--) {
    deal_info.Ticket(HistoryDealGetTicket(i));

    if (magic_number > 0 && deal_info.Magic() != magic_number)
      continue;

    if (symbol != deal_info.Symbol())
      continue;

    if (deal_info.Entry() == DEAL_ENTRY_OUT) {
      double profit = deal_info.Profit() //
                      + deal_info.Swap() //
                      + (2 * deal_info.Commission());

      int size = ArraySize(trades);
      ArrayResize(trades, size + 1);
      trades[size] = profit;
    }
  }
}

double GetLastPositionPrice(string symbol, ulong magic_number,
                            ENUM_POSITION_TYPE pos) {
  double price = 0;

  for (int i = PositionsTotal() - 1; i >= 0; i--) {
    if (position_info.SelectByIndex(i)) {
      if ((position_info.Magic() == magic_number) &&
          (position_info.Symbol() == symbol) &&
          position_info.PositionType() == pos) {
        price = position_info.PriceOpen();
        break;
      }
    }
  }

  return (price);
}

void ExpirePositions(string symbol, ulong magic_number, int days) {
  if (days <= 0)
    return;

  int limit = days * PeriodSeconds(PERIOD_D1);

  for (int i = PositionsTotal() - 1; i >= 0; i--) {
    if (position_info.SelectByIndex(i)) {
      if ((position_info.Magic() == magic_number) &&
          (position_info.Symbol() == symbol)) {
        datetime pos_open = position_info.Time();
        if (TimeCurrent() - pos_open >= limit)
          trade.PositionClose(position_info.Ticket());
      }
    }
  }
}

int CountPositionsByType(string symbol, ulong magic_number,
                         ENUM_POSITION_TYPE pos) {
  int count = 0;

  for (int i = PositionsTotal() - 1; i >= 0; i--) {
    if (position_info.SelectByIndex(i)) {
      if ((position_info.Magic() == magic_number) &&
          (position_info.Symbol() == symbol) &&
          (position_info.PositionType() == pos)) {
        count++;
      }
    }
  }

  return (count);
}

void CloseOrdersByType(string symbol, ulong magic_number,
                       ENUM_ORDER_TYPE order) {
  for (int i = OrdersTotal() - 1; i >= 0; i--) {
    if (order_info.SelectByIndex(i)) {
      if ((order_info.Magic() == magic_number) &&
          (order_info.Symbol() == symbol) &&
          (order_info.OrderType() == order)) {
        trade.OrderDelete(order_info.Ticket());
      }
    }
  }
}

void ClosePositionsByType(string symbol, ulong magic_number,
                          ENUM_POSITION_TYPE pos) {
  for (int i = PositionsTotal() - 1; i >= 0; i--) {
    if (position_info.SelectByIndex(i)) {
      if ((position_info.Magic() == magic_number) &&
          (position_info.Symbol() == symbol) &&
          position_info.PositionType() == pos) {
        trade.PositionClose(position_info.Ticket());
      }
    }
  }
}

bool InSession(int session_start, int session_length, bool day_filter = false) {
  if (session_length == 0)
    return (true);

  int end = session_start + session_length;
  bool wrap = (end > 23) ? true : false;
  end = int(MathMod(end, 24));

  MqlDateTime now;
  TimeToStruct(TimeTradeServer(), now);

  if (day_filter) {
    /*
    if (!_sunday && now.day_of_week == SUNDAY)
      return (false);

    if (!_monday && now.day_of_week == MONDAY)
      return (false);

    if (!_tuesday && now.day_of_week == TUESDAY)
      return (false);

    if (!_wednesday && now.day_of_week == WEDNESDAY)
      return (false);

    if (!_thursday && now.day_of_week == THURSDAY)
      return (false);

    if (!_friday && now.day_of_week == FRIDAY)
      return (false);

    if (!_saturday && now.day_of_week == SATURDAY)
      return (false);
    */
  }

  if (wrap && (now.hour < session_start && now.hour > end))
    return (false);

  if (!wrap && (now.hour < session_start || now.hour > end))
    return (false);

  return (true);
}

bool GetArray(const int handle, const int buffer, const int start_pos,
              const int count, double &array[]) {
  if (!ArrayIsDynamic(array)) {
    PrintFormat("[DEBUG] %s: Not a dynamic array!", __FUNCTION__);
    return (false);
  }

  ArrayFree(array);

  ResetLastError();

  if (CopyBuffer(handle, buffer, start_pos, count, array) <= 0) {
    PrintFormat("[ERROR] %s: Failed to copy data from the indicator. "
                "Error code: %d",
                __FUNCTION__, GetLastError());
    return (false);
  }

  return (true);
}

double CalculateVolume(string symbol, double distance, double risk) {
  double volume = 0.0;

  symbol_info.Name(symbol);
  symbol_info.RefreshRates();

  double sl = symbol_info.Ask() - distance;
  double loss = account.OrderProfitCheck(symbol, ORDER_TYPE_BUY, //
                                         1.0, symbol_info.Ask(), sl);

  if (!MathIsValidNumber(loss) || loss >= 0) {
    PrintFormat("[DEBUG] %s: Distance=%f, Risk=%.2f, SL=%f, Loss=%.2f",
                __FUNCTION__, distance, risk, sl, loss);
    return (volume);
  }

  volume = MathMax(risk / MathAbs(loss), 0.0);
  volume = NormalizeVolume(symbol, volume);

  return (volume);
}

double NormalizeVolume(string symbol, double volume) {
  symbol_info.Name(symbol);
  symbol_info.RefreshRates();

  double max_volume = symbol_info.LotsMax();
  double min_volume = symbol_info.LotsMin();
  double step_volume = symbol_info.LotsStep();
  int volume_digits = GetDigits(step_volume);

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

bool PrepareOrder(string symbol, ulong magic_number, ENUM_ORDER_TYPE order,
                  double volume, double price = 0.0, double sl = 0.0,
                  double tp = 0.0, string comment = "") {
  bool success = false;

  if (volume == 0.0) {
    PrintFormat("[ERROR] %s: Unable to send order=%s for symbol=%s "
                "with volume=%f and SL=%f",
                __FUNCTION__, EnumToString(order), symbol, volume, sl);
    return (success);
  }

  symbol_info.Name(symbol);
  symbol_info.RefreshRates();

  double volume_total = GetVolumeTotal(symbol);
  double volume_limit = symbol_info.LotsLimit();
  int volume_digits = GetDigits(symbol_info.LotsMin());

  volume = NormalizeDouble(volume, volume_digits);

  if (volume_total + volume > volume_limit && volume_limit > 0) {
    PrintFormat("[WARNING] %s: Total volume=%s is larger than volume limit=%s",
                __FUNCTION__,
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
    PrintFormat("[DEBUG] %s: Order=%s, Symbol=%s, Volume=%s, Price=%f. Free "
                "margin=%.2f",
                __FUNCTION__, EnumToString(order), symbol,
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
      success =
          SendOrder(symbol, magic_number, order, size, price, sl, tp, comment);
    }
  } else {
    success =
        SendOrder(symbol, magic_number, order, volume, price, sl, tp, comment);
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

  datetime expiration = TimeCurrent() + PeriodSeconds(PERIOD_D1);

  switch (order) {
  case ORDER_TYPE_BUY:
    success = trade.Buy(volume, symbol, price, sl, tp, comment);
    break;
  case ORDER_TYPE_SELL:
    success = trade.Sell(volume, symbol, price, sl, tp, comment);
    break;
  case ORDER_TYPE_BUY_STOP:
    success = trade.BuyStop(volume, price, symbol, sl, tp, //
                            ORDER_TIME_SPECIFIED, expiration, comment);
    break;
  case ORDER_TYPE_SELL_STOP:
    success = trade.SellStop(volume, price, symbol, sl, tp, //
                             ORDER_TIME_SPECIFIED, expiration, comment);
    break;
  case ORDER_TYPE_BUY_LIMIT:
    success = trade.BuyLimit(volume, price, symbol, sl, tp, //
                             ORDER_TIME_SPECIFIED, expiration, comment);
    break;
  case ORDER_TYPE_SELL_LIMIT:
    success = trade.SellLimit(volume, price, symbol, sl, tp, //
                              ORDER_TIME_SPECIFIED, expiration, comment);
    break;
  default:
    break;
  }

  if (success) {
    int volume_digits = GetDigits(symbol_info.LotsMin());
    PrintFormat("[DEBUG] %s: %s - %s (%d) at %f. Volume: %s, SL: %f, TP: %f",
                __FUNCTION__, EnumToString(order), symbol, //
                magic_number, price, DoubleToString(volume, volume_digits), sl,
                tp);
  } else {
    PrintFormat("[ERROR] %s: Unable to submit %s order. Error: %s", //
                __FUNCTION__, EnumToString(order),
                trade.ResultRetcodeDescription());
  }

  return (success);
}

void ModifySLTP(string symbol, ulong magic_number, ENUM_POSITION_TYPE position,
                double sl, double tp) {
  symbol_info.Name(symbol);
  symbol_info.RefreshRates();

  double stop_level = symbol_info.StopsLevel() * symbol_info.Point();
  double spread = symbol_info.Ask() - symbol_info.Bid();

  sl = symbol_info.NormalizePrice(sl);
  tp = symbol_info.NormalizePrice(tp);

  for (int i = PositionsTotal() - 1; i >= 0; i--) {
    if (position_info.SelectByIndex(i)) {
      if ((position_info.Magic() == magic_number) &&
          (position_info.Symbol() == symbol)) {
        ENUM_POSITION_TYPE pos_type = position_info.PositionType();
        double pos_sl = position_info.StopLoss();
        double pos_tp = position_info.TakeProfit();
        double pos_price = position_info.PriceCurrent();

        if ((pos_sl != sl) && (pos_type == POSITION_TYPE_BUY) &&
            (position == POSITION_TYPE_BUY)) {
          if (sl < pos_price - stop_level - spread && sl > pos_sl) {
            trade.PositionModify(position_info.Ticket(), sl, tp);
          }
        }

        if ((pos_sl != sl) && (pos_type == POSITION_TYPE_SELL) &&
            (position == POSITION_TYPE_SELL)) {
          if (sl > pos_price + stop_level + spread && sl < pos_sl) {
            trade.PositionModify(position_info.Ticket(), sl, tp);
          }
        }
      }
    }
  }
}

void ModifySL(string symbol, ulong magic_number, ENUM_POSITION_TYPE position,
              double sl) {
  symbol_info.Name(symbol);
  symbol_info.RefreshRates();

  double stop_level = symbol_info.StopsLevel() * symbol_info.Point();
  double spread = symbol_info.Ask() - symbol_info.Bid();

  sl = symbol_info.NormalizePrice(sl);

  for (int i = PositionsTotal() - 1; i >= 0; i--) {
    if (position_info.SelectByIndex(i)) {
      if ((position_info.Magic() == magic_number) &&
          (position_info.Symbol() == symbol)) {
        ENUM_POSITION_TYPE pos_type = position_info.PositionType();
        double pos_sl = position_info.StopLoss();
        double pos_tp = position_info.TakeProfit();
        double pos_price = position_info.PriceCurrent();

        if ((pos_sl != sl) && (pos_type == POSITION_TYPE_BUY) &&
            (position == POSITION_TYPE_BUY)) {
          if (sl < pos_price - stop_level - spread && sl > pos_sl) {
            trade.PositionModify(position_info.Ticket(), sl, pos_tp);
          }
        }

        if ((pos_sl != sl) && (pos_type == POSITION_TYPE_SELL) &&
            (position == POSITION_TYPE_SELL)) {
          if (sl > pos_price + stop_level + spread && sl < pos_sl) {
            trade.PositionModify(position_info.Ticket(), sl, pos_tp);
          }
        }
      }
    }
  }
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

string BooleanToString(bool value) { return (value ? "true" : "false"); }

void CommentLabel(string comment_text) {
  string comment_label;
  int comment_index = 0;

  if (comment_text == "") {
    return;
  }

  long chart_id = ChartID();

  while (ObjectFind(chart_id, StringFormat("label%d", comment_index)) >= 0) {
    comment_index++;
  }

  comment_label = StringFormat("label%d", comment_index);

  ObjectCreate(chart_id, comment_label, OBJ_LABEL, 0, 0, 0);
  ObjectSetInteger(chart_id, comment_label, OBJPROP_CORNER, 0);
  ObjectSetInteger(chart_id, comment_label, OBJPROP_XDISTANCE, 18);
  ObjectSetInteger(chart_id, comment_label, OBJPROP_YDISTANCE,
                   25 + (comment_index * 18));
  ObjectSetInteger(chart_id, comment_label, OBJPROP_COLOR, clrWhite);
  ObjectSetString(chart_id, comment_label, OBJPROP_TEXT, comment_text);
  ObjectSetString(chart_id, comment_label, OBJPROP_FONT, "Courier");
  ObjectSetInteger(chart_id, comment_label, OBJPROP_FONTSIZE, 7);
  ChartRedraw(chart_id);
}
