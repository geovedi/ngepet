package SQ.Columns.Databanks;

import com.strategyquant.lib.*;
import com.strategyquant.datalib.*;
import com.strategyquant.tradinglib.*;

public
class AboveAvgProfit extends DatabankColumn {
 public
  AboveAvgProfit() {
    super("AboveAvgProfit", DatabankColumn.Decimal2, ValueTypes.Maximize, 0, -1, 1);

    setTooltip("Above Average Profit");
    setDependencies("AvgWin", "GrossProfit", "StandardDev");
  }

  //------------------------------------------------------------------------

  @Override public double compute(SQStats stats,
                                  StatsTypeCombination combination,
                                  OrdersList ordersList, SettingsMap settings,
                                  SQStats statsLong,
                                  SQStats statsShort) throws Exception {
    double avgWin = stats.getDouble("AvgWin");
    double grossProfit = stats.getDouble("GrossProfit");
    double stdDev = stats.getDouble("StandardDev");

    double totalProfit = 0;

    for (int i = 0; i < ordersList.size(); i++) {
      Order order = ordersList.get(i);

      if (order.isBalanceOrder()) {
        continue;
      }

      double PL = getPLByStatsType(order, combination);

      if (PL > avgWin + stdDev) {
        totalProfit += PL;
      }
    }

    return round2(safeDivide(totalProfit, grossProfit));
  }
}
