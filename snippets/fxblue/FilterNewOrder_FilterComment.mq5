/* *************************************************************************************
Called when the sender EA is about to issue a new message to the receiver(s), for 
the order identified by senderOrder. This function can return one of the following 
values:

   0 = Allow order to be sent to receivers
   1 = Permanently suppress the order. Receivers will not know about and copy this trade.
   2 = Temporarily suppress the order.

If this function returns 2, then the sender EA will keep calling it periodically until 
it finally returns 0 or 1 (or until the order is closed). The purpose of return value #2
is to let this code implement a time-based or profit-based condition before 
a trade is copied.

This function is called before applying restrictions such as IncludeSymbols and 
IncludeOrderComments. If this function receives a notification and returns 0, the trade
is not necessarily copied.

(Note: trades can also be suppressed using FilterModifyOrders.)
************************************************************************************* */

int FilterNewOrder(string Channel, OrderDef& senderOrder)
{   
   string level = senderOrder.comment;
   StringReplace(level, "B", "");
   StringReplace(level, "S", "");

   int min_level = 9;
   int max_level = 17;
 
   if ((int)level >= min_level && (int)level <= max_level)
      return 0;

   return 1;
}
