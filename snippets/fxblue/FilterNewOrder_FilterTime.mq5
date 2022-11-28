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
   MqlDateTime now;
   TimeToStruct(TimeCurrent(), now);

   // XX:00
   if (now.min >= 58 || now.min <= 2)
      return 2;

   // XX:15
   if (now.min >= 13 && now.min <= 17)
      return 2;

   // XX:30
   if (now.min >= 28 && now.min <= 32)
      return 2;

   // XX:45
   if (now.min >= 43 && now.min <= 47)
      return 2;

   return 0;
}
