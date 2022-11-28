package SQ.MoneyManagement;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.strategyquant.lib.*;
import com.strategyquant.datalib.*;
import com.strategyquant.tradinglib.*;

@ClassConfig(name="Geovedi Martingale MM", display="Geovedi Martingale MM, $#RiskedMoney#, Multiplier: #RiskMultiplier#, Max: #MaxMMSeq#")
@Help("<b>Geovedi Martingale Money Management</b>")
@SortOrder(400)
@Description("Geovedi Martingale MM, $#RiskedMoney#, Multiplier: #RiskMultiplier#, Max: #MaxMMSeq#")

public class GeovediMartingale extends MoneyManagementMethod {

    public static final Logger Log = LoggerFactory.getLogger("GeovediMartingale");

    @Parameter(name="Risked Money", defaultValue="100", minValue=1d, maxValue=1000000d, step=10d)
    @Help("Risk in $")
    public double RiskedMoney;

    @Parameter(name="Risk Multiplier", defaultValue="0.5", minValue=0, maxValue=1000000d, step=0.1)
    @Help("Risk Multiplier.")
    public double RiskMultiplier;

    @Parameter(name="Maximum MM Sequence", defaultValue="5", minValue=1d, maxValue=100d)
    @Help("Maximum MM Sequence.")
    public int MaxMMSeq;
        
    @Parameter(name="Min Lots", category="Lots", defaultValue="0.01", minValue=0, maxValue=1000000000, step=0.01)
    @Help("Min Lots.")
    public double MinLots;

    @Parameter(name="Max Lots", category="Lots", defaultValue="100.0", minValue=0, maxValue=1000000000, step=0.01)
    @Help("Max Lots.")
    public double MaxLots;

    @Parameter(name="Size Decimals", category="Lots", defaultValue="1", minValue=0d, maxValue=6d, step=1d)
    @Help("Order size will be rounded to the selected number of decimal places.")
    public int Decimals;

    public GeovediMartingale() {}
    
    @Override
    public double computeTradeSize(StrategyBase strategy, String symbol, byte orderType, 
                                   double price, double sl, double tickSize, 
                                   double pointValue) throws Exception {
        if(RiskedMoney < 0) {
            throw new Exception("Money management wasn't properly initialized!");
        }
        

        double openPrice = price > 0 ? price 
            : (OrderTypes.isLongOrder(orderType) 
                ? strategy.MarketData.Chart(symbol).Ask() 
                : strategy.MarketData.Chart(symbol).Bid());
           
        double orderSL;
        
        if(sl != 0) {
            orderSL = Math.abs(openPrice - sl) / tickSize; 
        } else {
            return MinLots;
        }

        double slInMoney = orderSL * tickSize * pointValue;

        int lossCount = getRecentLossCount(strategy);
        lossCount = (lossCount > MaxMMSeq) ? 0 : lossCount;
        double coef = Math.pow(RiskMultiplier, lossCount);
        double risk = Math.max(RiskedMoney * coef, RiskedMoney);
        double tradeSize = SQUtils.roundDown(risk / slInMoney, Decimals);
        tradeSize = Math.max(MinLots, Math.min(MaxLots, tradeSize));
                
        return tradeSize;
    }

    private double getPL(Order order) {
        if(order.isLong()) {
            return order.ClosePrice - order.OpenPrice;          
        }
        
        return order.OpenPrice - order.ClosePrice;
    }

    
    protected int getRecentLossCount(StrategyBase Strategy) {
        String strategyName = Strategy.getStrategyName();
        int count = 0;

        for(int i=Strategy.Trader.getHistoryOrdersCount() - 1; i >= 0; i--) {
            Order order = Strategy.Trader.getHistoryOrder(i);
            
            if(!order.StrategyName.equals(strategyName)) {
                continue;
            }
            
            if(!order.Symbol.equals(Strategy.MarketData.Chart(0).Symbol)) {
                continue;
            } 
            
            if(order.OpenPrice == order.ClosePrice) {
                continue;
            }

            if(getPL(order) > 0) {
                return count;
            }

            count++;
        }
        
        return count;
    }
    
}
