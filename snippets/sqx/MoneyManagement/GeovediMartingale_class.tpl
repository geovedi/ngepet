#include <Trade\AccountInfo.mqh>

CAccountInfo m_account;
CDealInfo m_deal;

double sqGeovediMartingale(string symbol, ENUM_ORDER_TYPE orderType, double price, double sl, 
                           double riskedMoney, double riskMultiplier,
                           double minLots, double maxLots, 
                           int maxMMSeq, int decimals,
                           int magicNo) {
  Verbose("Computing Money Management for order - Martingale MM");

  if (riskedMoney <= 0) {
    Verbose("Computing Money Management - Incorrect RiskedMoney value, it must "
            "be above 0");
    return (0);
  }

  if (UseMoneyManagement == false) {
    Verbose("Use Money Management = false, MM not used");
    return (minLots);
  }

  string correctedSymbol = correctSymbol(symbol);
  sl = NormalizeDouble(sl, (int)SymbolInfoInteger(correctedSymbol, SYMBOL_DIGITS));

  double openPrice = price > 0 ? price : SymbolInfoDouble(correctedSymbol, isLongOrder(orderType) ? SYMBOL_ASK : SYMBOL_BID);

  double pointValue = SymbolInfoDouble(correctedSymbol, SYMBOL_TRADE_TICK_VALUE) / SymbolInfoDouble(correctedSymbol, SYMBOL_TRADE_TICK_SIZE);
  double symbolMinLot = SymbolInfoDouble(correctedSymbol, SYMBOL_VOLUME_MIN);
  double symbolMaxLot = SymbolInfoDouble(correctedSymbol, SYMBOL_VOLUME_MAX);
  double symbolLotStep = SymbolInfoDouble(correctedSymbol, SYMBOL_VOLUME_STEP);

  double slInMoney = MathAbs(m_account.OrderProfitCheck(correctedSymbol, orderType, 1.0, openPrice, sl));

  if (!HistorySelect(0, TimeTradeServer())) {
    return (minLots);
  }

  int lossCount = 0;
  for (int i = HistoryDealsTotal() - 1; i >= 0; i--) {
    if (m_deal.SelectByIndex(i)) {
      if ((m_deal.Magic() == magicNo) &&
          (m_deal.Symbol() == correctedSymbol)) {
        if (m_deal.Entry() == DEAL_ENTRY_OUT ||
            m_deal.Entry() == DEAL_ENTRY_OUT_BY) {
          double profit = m_deal.Profit();
          if (profit > 0)
            break;
          lossCount++;          
        }
      }
    }
  }

  lossCount = (lossCount > maxMMSeq) ? 0 : lossCount;
  double coef = MathPow(riskMultiplier, lossCount);
  double risk = MathMax(riskedMoney * coef, riskedMoney);
  double lotSize = roundDown(risk / slInMoney, decimals);
  lotSize = MathMax(minLots, MathMax(maxLots, lotSize));

  Verbose("Computing Money Management ",
          "- Loss Count: ", IntegerToString(lossCount),
          ", Coefficient: ", DoubleToString(coef, 2),
          ", Computed LotSize: ", DoubleToString(lotSize, decimals));
  Verbose("Money to risk: ", DoubleToString(riskedMoney, 2),
          ", Max 1 lot trade drawdown: ", DoubleToString(slInMoney, 2),
          ", Point value: ", DoubleToString(pointValue, 2));

  if (lotSize < symbolMinLot) {
    Verbose("Calculated LotSize is too small. "
            "Minimal allowed lot size from the broker is: ", DoubleToString(symbolMinLot, decimals),
            ". Please, increase your risk or set fixed LotSize.");
    lotSize = 0;
  } else if (lotSize > symbolMaxLot) {
    Verbose("LotSize is too big. "
            "LotSize set to maximal allowed market value: ", DoubleToString(symbolMaxLot, decimals));
    lotSize = symbolMaxLot;
  }

  //--------------------------------------------

  return (lotSize);
}
