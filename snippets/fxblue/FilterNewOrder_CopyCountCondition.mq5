#include <Trade\PositionInfo.mqh>
CPositionInfo position_info;

int PositionCount(ulong magic, string symbol, ENUM_POSITION_TYPE pos) {
  int count = 0;
  for (int i = PositionsTotal() - 1; i >= 0; i--) {
    if (position_info.SelectByIndex(i)) {
      if ((position_info.Magic() == magic) &&
          (position_info.Symbol() == symbol) &&
          (position_info.PositionType() == pos)) {
        count++;
      }
    }
  }
  return count;
}

int FilterNewOrder(string Channel, OrderDef& senderOrder)
{
   int opp_count = 0;

   if (senderOrder.comment == "0") {
      switch (senderOrder.type) {
         case 0:
            opp_count = PositionCount(senderOrder.magic, senderOrder.symbol, 
                                      POSITION_TYPE_SELL);
         case 1: 
            opp_count = PositionCount(senderOrder.magic, senderOrder.symbol, 
                                      POSITION_TYPE_BUY);
         default:
            opp_count = 0;
      }

      if (opp_count >= 2 && opp_count <= 5)
         return 0;
   }

   return 1;
}
