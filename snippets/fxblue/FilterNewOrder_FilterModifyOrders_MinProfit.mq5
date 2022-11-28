double min_profit = 50.0;

int FilterNewOrder(string Channel, OrderDef &senderOrder) {
  double order_profit =
      senderOrder.profit + senderOrder.swap + (2 * senderOrder.commission);

  if (order_profit < min_profit)
    return 2;

  return 0;
}

bool FilterModifyOrders(string Channel, OrderDef &currentOrders[]) {
  bool change = false;

  for (int i = 0; i < ArraySize(currentOrders); i++) {
    double order_profit = currentOrders[i].profit + currentOrders[i].swap +
                          (2 * currentOrders[i].commission);
    double order_openprice = currentOrders[i].openprice;
    double order_sl = currentOrders[i].sl;
    double order_tp = currentOrders[i].tp;
    int order_type = currentOrders[i].type;

    if (order_profit > min_profit) {
      currentOrders[i].sl = order_openprice;
      change = true;
    } else if (order_profit < -min_profit) {
      currentOrders[i].sl = order_openprice;
      currentOrders[i].tp = order_sl;
      currentOrders[i].type = (order_type == 0) ? 1 : 0;
      change = true;
    }
  }

  return change;
}
