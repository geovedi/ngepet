#property copyright "Copyright (c) 2021, Jim Geovedi."
#property link "https://jim.geovedi.com"
#property version "1.2"
#property description "Trail Master EA"

#include <Generic\SortedMap.mqh>
#include <Trade\AccountInfo.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\Trade.mqh>

CAccountInfo account;
CPositionInfo position_info;
CSymbolInfo symbol_info;
CTrade trade;

enum ENUM_TRAILING_TYPES {
  TRAIL_FIXED,            // Fixed Amount
  TRAIL_PERCENT_BALANCE,  // Balance Percentage
};

enum ENUM_CLOSINGS {
  CLOSING_NONE,    // None
  CLOSING_DAILY,   // Daily
  CLOSING_WEEKLY,  // Weekly
};

input ENUM_TRAILING_TYPES trailing_type = TRAIL_FIXED;  // Trailing Type
input double pos_trailing = 50.0;     // Position Trailing Value
input double min_pos_profit = 100.0;  // Min Position Profit Before Trailing
input double eq_trailing = 300.0;     // Equity Trailing Value
input double min_eq_profit = 500.0;   // Min Equity Profit Before Trailing
input ENUM_CLOSINGS closing_mode = CLOSING_NONE;  // Trade Closing Mode
input string closing_time = "22:00";              // Trade Closing Time

CSortedMap<long, double> pos_records;
double eq_max_profit;

int OnInit() {
  int tm = 15;
  if (!EventSetTimer(tm)) {
    PrintFormat("[ERROR]: Unable to activate timer. Error: %s", GetLastError());
    return (INIT_FAILED);
  } else {
    PrintFormat("Event timer set: %d seconds", tm);
  }

  eq_max_profit = account.Equity() - account.Balance();
  return (0);
}

void OnDeinit(const int reason) {
  EventKillTimer();
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
      CloseAllPositions();
  }
}

void CloseAllPositions() {
  for (int i = PositionsTotal() - 1; i >= 0; i--) {
    if (position_info.SelectByIndex(i)) {
      trade.PositionClose(position_info.Ticket());
    }
  }
}

void EquityTrailing() {
  if (eq_trailing <= 0)
    return;

  double trail_limit = (trailing_type == TRAIL_PERCENT_BALANCE)
                           ? (min_eq_profit / 100.0) * account.Balance()
                           : min_eq_profit;

  double trail_risk = (trailing_type == TRAIL_PERCENT_BALANCE)
                          ? (eq_trailing / 100.0) * account.Balance()
                          : eq_trailing;

  double profit = account.Equity() - account.Balance();

  if (eq_max_profit < profit)
    eq_max_profit = profit;
  else if (eq_max_profit > trail_limit && eq_max_profit - profit >= trail_risk)
    CloseAllPositions();
}

void PositionTrailing() {
  if (pos_trailing <= 0)
    return;

  double trail_limit = (trailing_type == TRAIL_PERCENT_BALANCE)
                           ? (min_pos_profit / 100.0) * account.Balance()
                           : min_pos_profit;

  double trail_risk = (trailing_type == TRAIL_PERCENT_BALANCE)
                          ? (pos_trailing / 100.0) * account.Balance()
                          : pos_trailing;

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
          PrintFormat("Update max profit: %.2f for ticket #%d", pos_max_profit,
                      ticket);
        } else if (pos_max_profit > min_pos_profit &&
                   pos_max_profit - profit >= trail_risk) {
          trade.PositionClose(position_info.Ticket());
          PrintFormat("Closing ticket #%d with profit: %.2f (max: %.2f)",
                      ticket, profit, pos_max_profit);
        }
      } else if (profit > trail_risk) {
        pos_records.Add(ticket, profit);
        PrintFormat("New max profit: %.2f for ticket #%d", profit, ticket);
      }
    }
  }

  ulong tickets[];
  double profits[];
  pos_records.CopyTo(tickets, profits);

  for (int i = 0; i < ArraySize(tickets) - 1; i++) {
    if (!position_info.SelectByTicket(tickets[i])) {
      pos_records.Remove(tickets[i]);
      PrintFormat("Remove unexisting ticket #%d", tickets[i]);
    }
  }
}
