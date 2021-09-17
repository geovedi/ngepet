double min_profit = 25.0;

int FilterNewOrder(string Channel, OrderDef& senderOrder)
{
   double order_profit = senderOrder.profit + senderOrder.swap + (2 * senderOrder.commission);

   if (order_profit < min_profit) return 2;
   
   return 0;
}

bool FilterModifyOrders(string Channel, OrderDef& currentOrders[])
{
   bool change = false;

   for (int i = 0; i < ArraySize(currentOrders); i++) {
      double order_profit = currentOrders[i].profit + currentOrders[i].swap + (2 * currentOrders[i].commission);

      if (order_profit > min_profit) {
         currentOrders[i].sl = currentOrders[i].openprice;
         change = true;
      }
   }
      
   return change;
}
