
#include <Math\Stat\Normal.mqh>
#include <Trade\AccountInfo.mqh>

CAccountInfo account;

bool flip = false;
double balance[];
int entry_bar = 0, limit = 20;

bool FilterModifyOrders(string Channel, OrderDef &currentOrders[]) {
  bool change = false;

  if (entry_bar != Bars(_Symbol, PERIOD_H1)) {
    double temp[];
    ArrayCopy(temp, balance);

    int size = ArraySize(temp);
    ArrayResize(temp, size + 1);
    temp[size] = account.Balance();

    if (size + 1 > limit)
      ArrayCopy(balance, temp, 0, 1);
    else
      ArrayCopy(balance, temp);

    size = ArraySize(balance);
    if (size > 0 && MathMean(balance) < balance[size - 1])
      flip = true;
    else
      flip = false;

    ArrayPrint(balance);

    entry_bar = Bars(_Symbol, PERIOD_H1);
  }

  for (int i = 0; i < ArraySize(currentOrders); i++) {
    if (flip) {
      int type = currentOrders[i].type;
      double sl = currentOrders[i].sl;
      double tp = currentOrders[i].tp;

      currentOrders[i].type = (type == 0) ? 1 : (type == 1) ? 0 : type;
      currentOrders[i].sl = tp;
      currentOrders[i].tp = sl;

      change = true;
    }
  }

  return (change);
}
