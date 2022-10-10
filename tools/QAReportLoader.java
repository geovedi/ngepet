import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.strategyquant.lib.databank.DatabanksRegistry;
import com.strategyquant.lib.results.SQResult;
import com.strategyquant.lib.results.SQResultsGroup;
import com.strategyquant.lib.results.SQStats;
import com.strategyquant.lib.results.StatsConst;
import com.strategyquant.lib.scripter.Program;
import com.strategyquant.lib.settings.SQConst;
import com.strategyquant.lib.settings.SQCoreConst;
import com.strategyquant.lib.utils.FlexibleSettings;
import java.io.File;

public class ReportLoader implements Runnable {
   public static final Logger Log = LoggerFactory.getLogger("ReportLoader");
   
   public void listFilesForFolder(final File folder) {
    for (final File fileEntry : folder.listFiles()) {
        if (fileEntry.isDirectory()) {
            listFilesForFolder(fileEntry);
        } else {
            process(fileEntry);
        }
    }
   }

   @Override
   public void run() {
      String basePath = "C:/Users/__USER__/AppData/Roaming/MetaQuotes/Terminal/__TERMINAL_ID__/reports";
      String symbolName = "eurusd";
      
      listFilesForFolder(new File(basePath + "/fx/m5/" + symbolName));
      listFilesForFolder(new File(basePath + "/fx/m15/" + symbolName));
      listFilesForFolder(new File(basePath + "/fx/m30/" + symbolName));
      listFilesForFolder(new File(basePath + "/fx/h1/" + symbolName));
   }
   
   public void process(File fileEntry) {
      double minProfitFactor = 1.3;
      double minRetDDRatio = 3.0;
      int minNumTrades = 200;
      
      try {
         SQResultsGroup strategyResults = (SQResultsGroup) Program.get("Loader").call("loadFile", fileEntry.getAbsolutePath());
         SQResult result = strategyResults.getResult(SQConst.SYMBOL_PORTFOLIO);
         SQStats stats = result.getStats(SQConst.DIRECTION_ALL, SQConst.PL_IN_MONEY, SQConst.KEY_SAMPLE_ALL);
         double retDDRatio = stats.getDouble(StatsConst.RETURN_DD_RATIO);
         double profitFactor = stats.getDouble(StatsConst.PROFIT_FACTOR);
         int numTrades = stats.getInt(StatsConst.NUMBER_OF_TRADES);
          
         if (retDDRatio > minRetDDRatio && profitFactor > minProfitFactor && numTrades > minNumTrades) {
            DatabanksRegistry.get(SQCoreConst.EAA_DATABANK_SIMPLE_STR).add(strategyResults);
         }
      } catch(Exception e) {
         e.printStackTrace();
         Log.error("Exception :", e);
      }     
   }
}
