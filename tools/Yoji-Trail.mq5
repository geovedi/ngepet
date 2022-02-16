#property copyright "Copyright (c) 2021, Jim Geovedi."
#property link "https://jim.geovedi.com"
#property version "1.0"
#property description "Yoji-Trail"

#include <Generic\SortedMap.mqh>
#include <Trade\AccountInfo.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\Trade.mqh>

CAccountInfo account;
COrderInfo order_info;
CPositionInfo position_info;
CSymbolInfo symbol_info;
CTrade trade;

enum ENUM_TRAILING_TYPES {
  TRAIL_FIXED,           // Fixed Amount
  TRAIL_PERCENT_BALANCE, // Balance Percentage
};

enum ENUM_CLOSINGS {
  CLOSING_NONE,   // None
  CLOSING_DAILY,  // Daily
  CLOSING_WEEKLY, // Weekly
};

input ENUM_TRAILING_TYPES trailing_type = TRAIL_FIXED; // Trailing Type
input group "Position Trailing";
input double pos_step = 0.0;  // Step
input double pos_start = 0.0; // Start
input group "Equity Trailing";
input double eq_step = 0.0;  // Step
input double eq_start = 0.0; // Start
input group "Trade Closing";
input ENUM_CLOSINGS closing_mode = CLOSING_NONE; // Closing Mode
input string closing_time = "23:59";             // Closing Time
sinput bool emergency_button = true;             // Display Emergency Button

CSortedMap<long, double> pos_records;
double eq_max_profit;

int OnInit() {
  int tm = 15;
  if (!EventSetTimer(tm)) {
    PrintFormat("[ERROR] %s: Unable to activate timer. Error: %s", __FUNCTION__,
                GetLastError());
    return (INIT_FAILED);
  } else {
    PrintFormat("[DEBUG] %s: Event timer set: %d seconds", __FUNCTION__, tm);
  }

  if (emergency_button)
    DisplayEmergencyCloseButtons();

  eq_max_profit = 0;
  return (0);
}

void OnDeinit(const int reason) {
  EventKillTimer();
  ObjectsDeleteAll(0, "EmergencyStop", -1, -1);
  ChartRedraw(0);
}

void OnTimer() {
  EquityTrailing();
  PositionTrailing();

  bool past_closing_time = false;

  if (closing_mode != CLOSING_NONE) {
    MqlDateTime now;
    TimeToStruct(TimeCurrent(), now);

    bool is_friday = now.day_of_week == 5;
    datetime end_time = StringToTime(StringFormat(
        "%s %s", TimeToString(TimeCurrent(), TIME_DATE), closing_time));
    past_closing_time = TimeCurrent() >= end_time;

    bool can_close = false;

    if (closing_mode == CLOSING_DAILY && past_closing_time)
      can_close = true;

    if (closing_mode == CLOSING_WEEKLY && past_closing_time && is_friday)
      can_close = true;

    if (can_close)
      CloseAllPositionsAndOrders();
  }
}

void CloseAllPositionsAndOrders() {
  for (int i = PositionsTotal() - 1; i >= 0; i--) {
    if (position_info.SelectByIndex(i)) {
      trade.PositionClose(position_info.Ticket());
    }
  }

  for (int i = OrdersTotal() - 1; i >= 0; i--) {
    if (order_info.SelectByIndex(i)) {
      trade.OrderDelete(order_info.Ticket());
    }
  }
}

void EquityTrailing() {
  if (eq_step <= 0)
    return;

  double trail_start = (trailing_type == TRAIL_PERCENT_BALANCE)
                           ? (eq_start / 100.0) * account.Balance()
                           : eq_start;

  double trail_risk = (trailing_type == TRAIL_PERCENT_BALANCE)
                          ? (eq_step / 100.0) * account.Balance()
                          : eq_step;

  double profit = account.Equity() - account.Balance();

  if (eq_max_profit < profit) {
    eq_max_profit = profit;
    PrintFormat("[DEBUG] %s: New max equity profit: %.2f", __FUNCTION__,
                eq_max_profit);
  } else if (eq_max_profit > trail_start &&
             eq_max_profit - profit >= trail_risk) {
    CloseAllPositionsAndOrders();
    eq_max_profit = 0.0;
  }
}

void PositionTrailing() {
  if (pos_step <= 0)
    return;

  double trail_start = (trailing_type == TRAIL_PERCENT_BALANCE)
                           ? (pos_start / 100.0) * account.Balance()
                           : pos_start;

  double trail_risk = (trailing_type == TRAIL_PERCENT_BALANCE)
                          ? (pos_step / 100.0) * account.Balance()
                          : pos_step;

  for (int i = PositionsTotal() - 1; i >= 0; i--) {
    if (position_info.SelectByIndex(i)) {
      ulong ticket = position_info.Ticket();
      double profit = position_info.Profit() + position_info.Swap() +
                      (position_info.Commission() * 2);

      if (pos_records.ContainsKey(ticket)) {
        double pos_max_profit = 0.0;
        pos_records.TryGetValue(ticket, pos_max_profit);

        if (pos_max_profit < profit) {
          pos_records.TrySetValue(ticket, profit);
          PrintFormat("[DEBUG] %s: Update max profit: %.2f for ticket #%d",
                      __FUNCTION__, pos_max_profit, ticket);
        } else if (pos_max_profit > pos_start &&
                   pos_max_profit - profit >= pos_step) {
          trade.PositionClose(position_info.Ticket());
          PrintFormat(
              "[DEBUG] %s: Closing ticket #%d with profit: %.2f (max: %.2f)",
              __FUNCTION__, ticket, profit, pos_max_profit);
        }
      } else if (profit > trail_risk) {
        pos_records.Add(ticket, profit);
        PrintFormat("[DEBUG] %s: New max profit: %.2f for ticket #%d",
                    __FUNCTION__, profit, ticket);
      }
    }
  }

  ulong tickets[];
  double profits[];
  pos_records.CopyTo(tickets, profits);

  for (int i = 0; i < ArraySize(tickets) - 1; i++) {
    if (!position_info.SelectByTicket(tickets[i])) {
      pos_records.Remove(tickets[i]);
      PrintFormat("[DEBUG] %s: Remove unexisting ticket #%d", __FUNCTION__,
                  tickets[i]);
    }
  }
}

void DisplayEmergencyCloseButtons() {
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
    CloseAllPositionsAndOrders();
    ObjectSetInteger(0, "EmergencyStop", OBJPROP_STATE, false);
  }
}
