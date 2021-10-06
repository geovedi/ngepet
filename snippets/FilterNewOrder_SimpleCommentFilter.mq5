int FilterNewOrder(string Channel, OrderDef& senderOrder)
{   
   int min_level = 2;
 
   if ((int)senderOrder.comment >= min_level)
      return 0;

   return 1;
}
