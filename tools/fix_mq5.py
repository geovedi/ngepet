import fire
import re
import os
from glob import glob


def main(input_dir, output_dir):

    for fname in glob(f'{input_dir}/*.mq5'):
        fn = os.path.normpath(fname).split(os.sep)[-1]
        print(fname, fn)
        with open(fname, 'r') as infile:
            with open(f'{output_dir}/{fn}', 'w') as outfile:
                outfile.write(block_replace(infile.read()))
                print(fn)

def block_replace(m):
    p9 = r"""input """
    s9 = r""""""
    m = re.sub(p9, s9, m)

    p0 = r"""bool IndicatorLoadedWithoutError = true;"""
    s0 = r"""input int baseMagicNumber = 1000;
bool IndicatorLoadedWithoutError = true;"""
    m = re.sub(p0, s0, m, flags=re.MULTILINE)
    
    p1 = r"""int MagicNumber = (\d+);"""
    s1 = r"""int MagicNumber = baseMagicNumber;"""
    m = re.sub(p1, s1, m)

    p2 = r"""int MagicNumber(\d+) = (\d+);"""
    s2 = r"""int MagicNumber\1 = baseMagicNumber + \1;"""
    m = re.sub(p2, s2, m)

    p3 = r"""string smm = "----------- Money Management - Fixed size -----------";
double mmLots = 0.1;
double mmMultiplier = 1.0;"""
    s3 = r"""string smm = "----------- Money Management - Geovedi Amount -----------";
input double mmRiskedMoney = 500.0;
input double mmRiskPercent = 0;

double sqMMGeovediAmount(string symbol, ENUM_ORDER_TYPE orderType, double price, double sl, double RiskedMoney, double RiskPercent) {
    Verbose("Computing Money Management for order - Geovedi amount");

    string correctedSymbol = correctSymbol(symbol);
    sl = NormalizeDouble(sl, (int) SymbolInfoInteger(correctedSymbol, SYMBOL_DIGITS));

    double openPrice = price > 0 ? price : SymbolInfoDouble(correctedSymbol, isLongOrder(orderType) ? SYMBOL_ASK : SYMBOL_BID);
    double LotSize = 0;

    if (RiskPercent > 0) {
        double RiskedBalanceMoney = RiskPercent * (AccountInfoDouble(ACCOUNT_BALANCE) / 100.0);
        RiskedMoney = MathMax(RiskedMoney, RiskedBalanceMoney);
    }

    if (RiskedMoney <= 0 ) {
      Verbose("Computing Money Management - Incorrect RiskedMoney value, it must be above 0");
      return (0);
    }

    double PointValue = SymbolInfoDouble(correctedSymbol, SYMBOL_TRADE_TICK_VALUE) / SymbolInfoDouble(correctedSymbol, SYMBOL_TRADE_TICK_SIZE); 
    double SmallestLot = SymbolInfoDouble(correctedSymbol, SYMBOL_VOLUME_MIN);
    double LargestLot = SymbolInfoDouble(correctedSymbol, SYMBOL_VOLUME_MAX);    
    double LotStep = SymbolInfoDouble(correctedSymbol, SYMBOL_VOLUME_STEP);
    int LotDigits = GetDigits(LotStep);

    double oneLotSLDrawdown = PointValue * MathAbs(openPrice - sl);
        
   if(oneLotSLDrawdown > 0) {
      LotSize = RiskedMoney / oneLotSLDrawdown;
   }
   else {
      return (0);
   }

    //SmallestLot = (SmallestLot * 2) * 2; // ATM multi PT exit
    LotSize = MathMin(MathMax(LotSize, SmallestLot), LargestLot);
    LotSize = MathCeil(LotSize / LotStep) * LotStep;

    Verbose("Computing Money Management - SmallestLot: ", DoubleToString(SmallestLot, LotDigits), ", LargestLot: ", DoubleToString(LargestLot, LotDigits), ", Computed LotSize: ", DoubleToString(LotSize, LotDigits));
    Verbose("Money to risk: ", DoubleToString(RiskedMoney, 2), ", Max 1 lot trade drawdown: ", DoubleToString(oneLotSLDrawdown, 2), ", Point value: ", DoubleToString(PointValue, 2));

    return (NormalizeDouble(LotSize, LotDigits));
}
"""
    m = re.sub(p3, s3, m, flags=re.MULTILINE)
    
    if "VIX" in m:
    	p4 = r"""string Subchart(\d+)Symbol = "VIX(\d+)";"""
    	s4 = r"""string Subchart\1Symbol = "Volatility \2 Index";"""
    	m = re.sub(p4, s4, m)
	else:
	    p4a = """bool UseSQTickSize = false;"""
	    s4a = """input string SymbolPrefix = "";
input string SymbolSuffix = "";
bool UseSQTickSize = false;"""
		m = re.sub(p4a, s4a, m)

	    p4b = r"""string Subchart(\d+)Symbol = "(\w+).mt";"""
	    s4b = r"""string Subchart\1Symbol = symbolPrefix + "\2" + symbolSuffix;"""
	    m = re.sub(p4b, s4b, m)

    p5 = """// -- Functions"""
    s5 = """// -- Functions
//+------------------------------------------------------------------+

#include <TradeHistory.mqh>

double OnTester() {
    ExportTradeHistory(sqStrategyName + ".csv");
    return TesterStatistics(STAT_SHARPE_RATIO);
}

input int tradeDuration = 120;

void closeExpiredPositions(int hours) {
    if (hours <= 0)
        return;

    for (int i = PositionsTotal() - 1; i >= 0; i--) {
        ulong ticket = PositionGetTicket(i);
        datetime tradeOpening = (datetime)PositionGetInteger(POSITION_TIME);
        int tradeTime = (int)((TimeCurrent() - tradeOpening) / 60);
        if (tradeTime > hours * 60) {
            Verbose("Closing trade with ticket: ", IntegerToString(ticket), " after ", IntegerToString(hours), " hours"); 
            sqClosePositionAtMarket(ticket);
        }
    }
}"""
    m = re.sub(p5, s5, m, flags=re.MULTILINE)
    
    p6 = """sqManagePositions\(MagicNumber\);"""
    s6 = """closeExpiredPositions(tradeDuration);

   sqManagePositions(MagicNumber);"""
    m = re.sub(p6, s6, m)
    
    p7 = """mmLots \* mmMultiplier / 100.0"""
    s7 = """size / 100.0"""
    m = re.sub(p7, s7, m)
        
    p8 = r"""pt = sqFixMarketPrice\(sqGetPTLevel\("(.*)", (.*?), openPrice, (.*?);
\s+size = mmLots \* mmMultiplier;"""
    s8 = r"""pt = sqFixMarketPrice(sqGetPTLevel("\1", \2, openPrice, \3;
      size = sqMMGeovediAmount("\1", \2, openPrice, sl, mmRiskedMoney, mmRiskPercent);"""
    m = re.sub(p8, s8, m, flags=re.MULTILINE)
    
    p9 = """   sqManagePositions(MagicNumber2);
   sqManagePositions(MagicNumber3);
   sqManagePositions(MagicNumber4);
   sqManagePositions(MagicNumber5);
   sqManagePositions(MagicNumber6);
   sqManagePositions(MagicNumber7);
   sqManagePositions(MagicNumber8);
   sqManagePositions(MagicNumber9);
   sqManagePositions(MagicNumber10);
   sqManagePositions(MagicNumber11);
   sqManagePositions(MagicNumber12);
   sqManagePositions(MagicNumber13);
   sqManagePositions(MagicNumber14);"""
    m = m.replace(p9, "")

    p10 = """void sqManagePositions(int magicNo) {
   if(_sqIsBarOpen){
     for (int cc = PositionsTotal() - 1; cc >= 0; cc--) {
        ulong positionTicket = PositionGetTicket(cc);
     
        if (PositionSelectByTicket(positionTicket)) {
           if(PositionGetInteger(POSITION_MAGIC) != magicNo || !IsMarketOpen(PositionGetString(POSITION_SYMBOL))) {      
              continue;
           }
           
           sqManageSL2BE(positionTicket);
           sqManageTrailingStop(positionTicket);
           sqManageExitAfterXBars(positionTicket);
        }
        
        if(PositionsTotal() <= 0) break;
     }
     
     sqManageOrderExpirations(magicNo);
   }
}"""
    s10 = """input double sizeMultiplier = 2.00;
input double distMultiplier = 0.30;

void sqManagePositions(int magicNo) {
   double minPriceOpen = 0, minSL = 0, minTP = 0, minVolume = 0;
   double maxPriceOpen = 0, maxSL = 0, maxTP = 0, maxVolume = 0;
   double priceCurrent = 0;
   int posCount = 0;
   ENUM_POSITION_TYPE posType = WRONG_VALUE;
   string symbol = "";

   if(_sqIsBarOpen){
     for (int cc = PositionsTotal() - 1; cc >= 0; cc--) {
        ulong positionTicket = PositionGetTicket(cc);
     
        if (PositionSelectByTicket(positionTicket)) {
           if(PositionGetInteger(POSITION_MAGIC) != magicNo || !IsMarketOpen(PositionGetString(POSITION_SYMBOL))) {      
              continue;
           }

           posCount++;

           double priceOpen = PositionGetDouble(POSITION_PRICE_OPEN);
           if (minPriceOpen == 0 || minPriceOpen > priceOpen) { minPriceOpen = priceOpen; }
           if (maxPriceOpen == 0 || maxPriceOpen < priceOpen) { maxPriceOpen = priceOpen; }

           double posSL = PositionGetDouble(POSITION_SL);
           if (minSL == 0 || minSL > posSL) { minSL = posSL; }
           if (maxSL == 0 || maxSL < posSL) { maxSL = posSL; }

           double posTP = PositionGetDouble(POSITION_TP);
           if (minTP == 0 || minTP > posTP) { minTP = posTP; }
           if (maxTP == 0 || maxTP < posTP) { maxTP = posTP; }

           double posVolume = PositionGetDouble(POSITION_VOLUME);
           if (maxVolume == 0 || maxVolume < posVolume) { maxVolume = posVolume; }

           posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
           priceCurrent = PositionGetDouble(POSITION_PRICE_CURRENT);
           symbol = PositionGetString(POSITION_SYMBOL);
           
           sqManageSL2BE(positionTicket);
           sqManageTrailingStop(positionTicket);
           sqManageExitAfterXBars(positionTicket);
        }
        
        if(PositionsTotal() <= 0) break;
     }

     if (posCount > 0) {
        Print("> Symbol=", symbol, " position=", EnumToString(posType));
        Print("> minVolume=", DoubleToString(minVolume), " maxVolume=", DoubleToString(maxVolume));
        Print("> minPriceOpen=", DoubleToString(minPriceOpen), " maxPriceOpen=", DoubleToString(maxPriceOpen));
        Print("> minSL=", DoubleToString(minSL), " maxSL=", DoubleToString(maxSL));

        Verbose("Deleting existing orders");
        // Delete existing orders
        for (int i = OrdersTotal() - 1; i >= 0; i--) {
            ulong orderTicket = OrderGetTicket(i);
            ENUM_ORDER_TYPE orderType = (ENUM_ORDER_TYPE) OrderGetInteger(ORDER_TYPE);
            if(!OrderSelect(orderTicket)) continue;
            if(orderType != ORDER_TYPE_BUY && orderType != ORDER_TYPE_SELL) {
                sqDeletePendingOrder(orderTicket);
            }
        }

        double LotStep = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
        int LotDigits = GetDigits(LotStep);

        if (posType == POSITION_TYPE_BUY) {
            double sl = MathAbs(maxPriceOpen - maxSL);
            double newSL = priceCurrent - sl;

            if (priceCurrent - maxPriceOpen > sl * distMultiplier) {
                double size = NormalizeDouble(maxVolume * sizeMultiplier, LotDigits);
                Verbose("Adding new BUY position... ", "size=", DoubleToString(size), " newSL=", DoubleToString(newSL));
                ulong ticket = openPosition(ORDER_TYPE_BUY, symbol, size, 0, newSL, maxTP, correctSlippage(sqMaxEntrySlippage, symbol), "R", magicNo, ExpirationTime, true, false);
                if (ticket > 0) {
                    Verbose("New BUY position with ticket=", IntegerToString(ticket));
                    for (int cc = PositionsTotal() - 1; cc >= 0; cc--) {
                        ulong positionTicket = PositionGetTicket(cc);
                        OrderModify(positionTicket, newSL, maxTP);
                    }
                } else {
                    Verbose("Cannot place new BUY position!");                    
                }
            }
        }

        if (posType == POSITION_TYPE_SELL) {
            double sl = MathAbs(minPriceOpen - minSL);
            double newSL = priceCurrent + sl;

            if (minPriceOpen - priceCurrent > sl * distMultiplier) {
                double size = NormalizeDouble(maxVolume * sizeMultiplier, LotDigits);
                Verbose("Adding new SELL position... ", "size=", DoubleToString(size), " newSL=", DoubleToString(newSL));
                ulong ticket = openPosition(ORDER_TYPE_SELL, symbol, size, 0, newSL, minTP, correctSlippage(sqMaxEntrySlippage, symbol), "R", magicNo, ExpirationTime, true, false);
                if (ticket > 0) {
                    Verbose("New SELL position with ticket=", IntegerToString(ticket));
                    for (int cc = PositionsTotal() - 1; cc >= 0; cc--) {
                        ulong positionTicket = PositionGetTicket(cc);
                        OrderModify(positionTicket, newSL, minTP);
                    }
                } else {
                    Verbose("Cannot place new SELL position!");                    
                }
            }
        }

     }
     
     sqManageOrderExpirations(magicNo);
   }
}"""
    m = m.replace(p10, s10)

    return m


if __name__ == '__main__':
	fire.Fire(main)
