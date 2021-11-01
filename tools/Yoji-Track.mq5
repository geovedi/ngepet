//+------------------------------------------------------------------+
//|                                                       Yoji-Track |
//|                                      Copyright 2021, Jim Geovedi |
//|                                          https://jim.geovedi.com |
//+------------------------------------------------------------------+

#property copyright "Copyright (c) 2021, Jim Geovedi."
#property link "https://jim.geovedi.com"
#property description "Yoji-Track"

#include <Trade\AccountInfo.mqh>

CAccountInfo account;

input ENUM_TIMEFRAMES _tf = PERIOD_H1; // Timeframe

int entry_bar;

int OnInit() {
  if (!EventSetTimer(10)) {
    PrintFormat("[ERROR]: %s: Unable to activate timer. Error: %s",
                __FUNCTION__, GetLastError());
    return (INIT_FAILED);
  }

  return (INIT_SUCCEEDED);
}

void OnDeinit(const int reason) {}

void OnTimer() {
  if (entry_bar != Bars(_Symbol, _tf)) {
    WriteEquity();
    entry_bar = Bars(_Symbol, _tf);
  }
}

void WriteEquity() {
  int bar_index = 0;
  datetime bar_time = iTime(_Symbol, _tf, bar_index);
  double equity = account.Equity();

  string fname = StringFormat("%s\\%I64d.csv",                   //
                              AccountInfoString(ACCOUNT_SERVER), //
                              account.Login());

  // https://www.mql5.com/en/forum/128204#comment_3315295
  int handle = FileOpen(fname, FILE_WRITE | FILE_READ | FILE_SHARE_READ |
                                   FILE_COMMON | FILE_TXT);
  if (handle == INVALID_HANDLE) {
    PrintFormat("[ERROR] %s: Unable to open file %s", __FUNCTION__, fname);
    return;
  }

  FileSeek(handle, 0, SEEK_END);

  string line = StringFormat("%s;%s",                //
                             TimeToString(bar_time), //
                             DoubleToString(equity, 2));

  FileWrite(handle, line);
  FileFlush(handle);

  Comment(line);

  FileClose(handle);
}
