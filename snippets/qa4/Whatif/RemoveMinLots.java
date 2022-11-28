package com.strategyquant.extend.WhatIf;

import java.util.Iterator;
import com.strategyquant.lib.language.L;
import com.strategyquant.lib.snippets.WhatIf;
import com.strategyquant.lib.results.SQOrderList;
import com.strategyquant.lib.results.SQOrder;

public class RemoveMinLots extends WhatIf {

   public RemoveMinLots() {
      setName(L.t("Remove min lots"));
        
      addDoubleParameter("maxLots", L.t("maxLots"), 0.01d, 0.001d, 1d, 0.001d);

      setFormatedName(L.t("Remove min lots <= {maxLots}"));
   }
   
   /**
    * Function receives list of all orders sorted by open time and it could manipulate 
    * the list and remove any order that matches certain filter from the list.     
    * 
    * Order structure is available in the documentation here:
    * http://www.strategyquant.com/doc/api/com/strategyquant/lib/results/SQOrder.html
    *
    * @param originalOrders - list of original orders that can be changed. Each order has the order properties specified above
    */    
   @Override
   public void filter(SQOrderList originalOrders) throws Exception {
      double maxLots = getDoubleParameterValue("maxLots");
   
      for(Iterator<SQOrder> i = originalOrders.listIterator(); i.hasNext();) {
         SQOrder order = i.next();
         //double orderRisk = Math.abs(order.OpenPrice - order.ClosePrice) * order.Size;
         if (order.Size <= maxLots) {
            i.remove();
         }
         
         // todo - your custom action
         // orders can be skipped or manipulated here
      }        
   }
}
