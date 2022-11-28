package com.strategyquant.extend.WhatIf;

import java.util.Iterator;
import com.strategyquant.lib.language.L;
import com.strategyquant.lib.snippets.WhatIf;
import com.strategyquant.lib.results.SQOrderList;
import com.strategyquant.lib.results.SQOrder;

public class RemoveMinRisks extends WhatIf {

	public RemoveMinRisks() {
      setName(L.t("Remove min risks"));
        
      addDoubleParameter("maxRisk", L.t("maxRisk"), 100.0d, 0.0d, 10000d, 10.0d);

      setFormatedName(L.t("Remove min risk <= {maxRisk}"));
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
		double maxRisk = getDoubleParameterValue("maxRisk");
	
		for(Iterator<SQOrder> i = originalOrders.listIterator(); i.hasNext();) {
			SQOrder order = i.next();
         double orderRisk = Math.abs(order.OpenPrice - order.ClosePrice) * order.Size;
         if (orderRisk <= maxRisk) {
            i.remove();
         }
			
			// todo - your custom action
			// orders can be skipped or manipulated here
		}			
	}
}
