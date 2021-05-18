#property copyright "Copyright (c) 2021, Jim Geovedi."
#property link "https://jim.geovedi.com"
#property version "1.0"
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
input double trailing = 100.0;                          // Trailing Value
input ENUM_CLOSINGS closing_mode = CLOSING_NONE;        // Trade Closing Mode
input string closing_time = "22:00";                    // Trade Closing Time

CSortedMap<long, double> records;

int OnInit() {
  int tm = 15;
  if (!EventSetTimer(tm)) {
    PrintFormat("[ERROR]: Unable to activate timer. Error: %s", GetLastError());
    return (INIT_FAILED);
  } else {
    PrintFormat("Event timer set: %d seconds", tm);
  }

  return (0);
}

void OnDeinit(const int reason) {
  EventKillTimer();
}

void OnTimer() {
  Trailing();

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

    if (can_close) {
      for (int i = PositionsTotal() - 1; i >= 0; i--) {
        if (position_info.SelectByIndex(i)) {
          trade.PositionClose(position_info.Ticket());
        }
      }
    }
  }
}

void Trailing() {
  if (trailing <= 0)
    return;

  double trail_risk = (trailing_type == TRAIL_PERCENT_BALANCE)
                          ? (trailing / 100.0) * account.Balance()
                          : trailing;

  for (int i = PositionsTotal() - 1; i >= 0; i--) {
    if (position_info.SelectByIndex(i)) {
      ulong ticket = position_info.Ticket();
      double profit = position_info.Profit() + position_info.Swap() +
                      (position_info.Commission() * 2);

      if (records.ContainsKey(ticket)) {
        double max_profit = 0.0;
        records.TryGetValue(ticket, max_profit);

        if (max_profit < profit) {
          records.TrySetValue(ticket, profit);
          PrintFormat("Update max profit: %.2f for ticket #%d", max_profit,
                      ticket);
        } else if (profit > trail_risk) {
          if (max_profit - profit >= trail_risk) {
            trade.PositionClose(position_info.Ticket());
            PrintFormat("Closing ticket #%d with profit: %.2f (max: %.2f)",
                        ticket, profit, max_profit);
          }
        }
      } else if (profit > trail_risk) {
        records.Add(ticket, profit);
        PrintFormat("New max profit: %.2f for ticket #%d", profit, ticket);
      }
    }
  }

  ulong tickets[];
  double profits[];
  records.CopyTo(tickets, profits);

  for (int i = 0; i < ArraySize(tickets) - 1; i++) {
    if (!position_info.SelectByTicket(tickets[i])) {
      records.Remove(tickets[i]);
      PrintFormat("Remove unexisting ticket #%d", tickets[i]);
    }
  }
}
