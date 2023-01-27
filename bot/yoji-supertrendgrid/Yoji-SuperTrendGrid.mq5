#property copyright "Copyright (c) 2023, Jim Geovedi."
#property link "https://jim.geovedi.com"
#property description "Yoji-SuperTrendGrid"

#define EA_NAME "Yoji-SuperTrendGrid"

#include <Yoji\Common.mqh> // https://github.com/geovedi/ngepet/blob/main/include/Yoji/Common.mqh

///

input group "General Setting";
sinput ulong magicNumber = 1000;            // Magic Number
sinput bool displayEmergencyButton = false; // Display Emergency Button

input group "Grid Risk Management";
input double gridRiskValue = 25.0;        // Grid Risk Value
input double gridProfitTarget = 50.0;     // Grid Profit Target
input double gridStopLoss = 0.0;          // Grid Stop Loss
input double gridATRMultiplier = 1.0;     // Grid ATR Multiplier
input double gridLotSizeMultiplier = 2.0; // Grid Lot Size Multiplier

input group "Entry Strategy";
input ENUM_TIMEFRAMES entryTimeframe = PERIOD_M5; // Entry Timeframe
input ENUM_TIMEFRAMES trendTimeframe = PERIOD_H4; // Trend Timeframe
input int stPeriod = 10;                          // SuperTrend Period
input double stMultiplier = 5.0;                  // SuperTrend Multiplier

///

int entryBar, atrHandle, strHandle;

int OnInit() {
  atrHandle = iATR(Symbol(), trendTimeframe, 20);
  strHandle = iCustom(Symbol(), trendTimeframe, "SqSuperTrend", 1, stPeriod,
                      stMultiplier);

  if (displayEmergencyButton)
    DisplayEmergencyButton();

  if (!EventSetTimer(10))
    return (INIT_FAILED);

  return (INIT_SUCCEEDED);
}

void OnDeinit(const int reason) {
  IndicatorRelease(atrHandle);
  IndicatorRelease(strHandle);
  ObjectsDeleteAll(0, "EmergencyStop", 0, -1);
  EventKillTimer();
}

void OnTimer() {
  string symbol = Symbol();
  if (entryBar == Bars(symbol, entryTimeframe))
    return;

  if (HasPosition(symbol, magicNumber)) {
    ManageGrid(symbol, magicNumber);
  } else {
    CreateNewGrid(symbol, magicNumber);
  }

  entryBar = Bars(symbol, entryTimeframe);
}

double OnTester() {
  double nt = TesterStatistics(STAT_TRADES);
  double np = TesterStatistics(STAT_PROFIT);
  double id = TesterStatistics(STAT_INITIAL_DEPOSIT);
  double dd = TesterStatistics(STAT_EQUITY_DD_RELATIVE);

  double score = np / dd;

  if (nt < 300 || np < id * 2 || !MathIsValidNumber(score))
    return (DBL_MIN);

  return (score);
}

///

bool ManageOpenPositions(string symbol, ulong magic) {
  double profit = 0.0;

  for (int i = PositionsTotal() - 1; i >= 0; i--) {
    if (positionInfo.SelectByIndex(i)) {
      if (positionInfo.Magic() == magic && //
          positionInfo.Symbol() == symbol) {
        profit += positionInfo.Profit();
        profit += positionInfo.Swap();
        profit += positionInfo.Commission() * 2;
      }
    }
  }

  if (profit > gridProfitTarget ||
      (profit < -gridStopLoss && gridStopLoss > 0)) {
    CloseAllPositions(symbol, magic);
    return (true);
  }

  return (false);
}

void ManageGrid(string symbol, ulong magic) {
  if (ManageOpenPositions(symbol, magic))
    return;

  double lastOpenPrice = 0.0, lastVolume = 0.0;
  ENUM_POSITION_TYPE lastPosition = WRONG_VALUE;
  string lastComment = "0";

  for (int i = PositionsTotal() - 1; i >= 0; i--) {
    if (positionInfo.SelectByIndex(i)) {
      if (positionInfo.Magic() == magic && positionInfo.Symbol() == symbol) {
        lastOpenPrice = positionInfo.PriceOpen();
        lastVolume = positionInfo.Volume();
        lastPosition = positionInfo.PositionType();
        lastComment = positionInfo.Comment();
        break;
      }
    }
  }

  if (lastOpenPrice == 0.0)
    return;

  symbolInfo.Name(symbol);
  symbolInfo.RefreshRates();
  double price = (lastPosition == POSITION_TYPE_BUY) //
                     ? symbolInfo.Ask()
                     : symbolInfo.Bid();

  double atr[];
  MqlRates rates[];

  if (!GetArray(atrHandle, 0, 0, 3, atr) || //
      !GetRates(symbol, entryTimeframe, 3, rates))
    return;

  if (MathAbs(lastOpenPrice - price) < atr[1] * gridATRMultiplier)
    return;

  double volume = NormalizeVolume(symbol, lastVolume * gridLotSizeMultiplier);
  string comment = IntegerToString(StringToInteger(lastComment) + 1);

  if (lastPosition == POSITION_TYPE_BUY && rates[1].open < rates[1].close)
    PrepareOrder(symbol, magic, ORDER_TYPE_BUY, volume, 0, 0, 0, comment);
  if (lastPosition == POSITION_TYPE_SELL && rates[1].open < rates[1].close)
    PrepareOrder(symbol, magic, ORDER_TYPE_SELL, volume, 0, 0, 0, comment);
}

void CreateNewGrid(string symbol, ulong magic) {
  double atr[], str[];
  MqlRates rates[];

  if (!GetArray(atrHandle, 0, 0, 3, atr) || //
      !GetArray(strHandle, 0, 0, 3, str) || //
      !GetRates(symbol, entryTimeframe, 3, rates))
    return;

  symbolInfo.Name(symbol);
  symbolInfo.RefreshRates();

  // entry logic
  bool buySignal = rates[1].close > str[1];
  bool sellSignal = rates[1].close < str[1];

  if (!buySignal && !sellSignal)
    return;

  double distance = atr[1] * gridATRMultiplier;
  double volume = GetBaseVolume(symbol, distance, gridRiskValue);

  if (buySignal)
    PrepareOrder(symbol, magic, ORDER_TYPE_BUY, volume, 0, 0, 0, "0");
  if (sellSignal)
    PrepareOrder(symbol, magic, ORDER_TYPE_SELL, volume, 0, 0, 0, "0");
}
