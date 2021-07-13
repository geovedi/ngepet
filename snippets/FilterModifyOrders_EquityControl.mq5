/* *************************************************************************************
Receives the list of orders currently open on the account, and can make *any* changes 
to what the copier sees and subsequently processes. If the array is modified in any way 
then the function must return true, or else it will have no effect.

For example, the function can do the following:
  * Change the s/l, t/p, volume, or even symbol name on an order
  * Remove an order from the array, preventing it being copied (temporarily or permanently).
    Orders can also be suppressed by setting their symbol to "", or their ticket or volume to <= 0
  * Add "virtual" orders which do not actually exist on the account. All such orders
    need to be given unique ticket numbers.
************************************************************************************* */

#include <Math\Stat\Normal.mqh>
#include <Trade\SymbolInfo.mqh>

CSymbolInfo symbol_info;

double pnl[];
double pnl_ma = 0;
int deal_period = 20;
datetime deal_update;
datetime one_hour = 60 * 60;

bool FilterModifyOrders(string Channel, OrderDef& currentOrders[]) {
  if ((TimeCurrent() - deal_update) > one_hour || ArraySize(pnl) == 0) {
    PrintFormat("%s: updating pnl database...", __FUNCTION__);
    if (!GetTradeResultsToArray(pnl, deal_period))
      return (false);

    ArraySetAsSeries(pnl, false);
    ArrayPrint(pnl);

    pnl_ma = iMAOnArray(pnl, deal_period, 0, MODE_LWMA, 0);
    deal_update = TimeCurrent();

    PrintFormat("pnl[0]=%f, pnl_ma=%f", pnl[0], pnl_ma);
  }

  if ((pnl[0] > pnl_ma) || pnl_ma == 0)
    return (false);

  for (int i = 0; i < ArraySize(currentOrders); i++) {
    currentOrders[i].lots =
        NormalizeVolume(currentOrders[i].symbol, 2.0 * currentOrders[i].lots);
  }

  return (true);
}

double NormalizeVolume(string symbol, double volume) {
  symbol_info.Name(symbol);
  symbol_info.RefreshRates();

  double max_volume = symbol_info.LotsMax();
  double min_volume = symbol_info.LotsMin();
  double step_volume = symbol_info.LotsStep();
  int volume_digits = GetDigits(symbol_info.LotsMin());

  volume = MathMin(MathMax(volume, min_volume), max_volume);
  volume = MathFloor(volume / step_volume) * step_volume;

  return (NormalizeDouble(volume, volume_digits));
}

int GetDigits(double var, int digits = 8) {
  string value = DoubleToString(var, digits);  // 0.01000000
  int pad = StringLen(value) - 1;
  while (StringGetCharacter(value, pad) == '0') {
    digits--;
    pad--;
  }                 // 0.01
  return (digits);  // 2
}

bool GetTradeResultsToArray(double& trades[], int period = 100) {
  if (!HistorySelect(0, TimeCurrent()))
    return (false);

  uint total_deals = HistoryDealsTotal();
  ulong ticket = 0;
  double prev_profit = 0.0;

  for (uint i = total_deals - period; i < total_deals; i--) {
    if ((ticket = HistoryDealGetTicket(i)) > 0) {
      ENUM_DEAL_ENTRY deal_entry =
          (ENUM_DEAL_ENTRY)HistoryDealGetInteger(ticket, DEAL_ENTRY);

      double deal_profit = HistoryDealGetDouble(ticket, DEAL_PROFIT);
      long deal_type = HistoryDealGetInteger(ticket, DEAL_TYPE);

      if ((deal_type != DEAL_TYPE_BUY) && (deal_type != DEAL_TYPE_SELL))
        continue;

      if (deal_entry != DEAL_ENTRY_IN) {
        int size = ArraySize(trades);
        ArrayResize(trades, size + 1);
        trades[size] = deal_profit + prev_profit;
        prev_profit = deal_profit;
        if (size > period)
          break;
      }
    }
  }

  return (true);
}

double iMAOnArray(double& array[],
                  int period,
                  int ma_shift,
                  ENUM_MA_METHOD ma_method,
                  int shift) {
  double buf[], arr[];
  int total = ArraySize(array);

  if (total <= period)
    return 0;

  if (shift > total - period - ma_shift)
    return 0;

  switch (ma_method) {
    case MODE_SMA: {
      total = ArrayCopy(arr, array, 0, shift + ma_shift, period);
      if (ArrayResize(buf, total) < 0)
        return 0;
      double sum = 0;
      int i, pos = total - 1;

      for (i = 1; i < period; i++, pos--)
        sum += arr[pos];
      while (pos >= 0) {
        sum += arr[pos];
        buf[pos] = sum / period;
        sum -= arr[pos + period - 1];
        pos--;
      }
      return buf[0];
    }

    case MODE_EMA: {
      if (ArrayResize(buf, total) < 0)
        return 0;
      double pr = 2.0 / (period + 1);
      int pos = total - 2;

      while (pos >= 0) {
        if (pos == total - 2)
          buf[pos + 1] = array[pos + 1];
        buf[pos] = array[pos] * pr + buf[pos + 1] * (1 - pr);
        pos--;
      }
      return buf[shift + ma_shift];
    }

    case MODE_SMMA: {
      if (ArrayResize(buf, total) < 0)
        return (0);
      double sum = 0;
      int i, k, pos;

      pos = total - period;
      while (pos >= 0) {
        if (pos == total - period) {
          for (i = 0, k = pos; i < period; i++, k++) {
            sum += array[k];
            buf[k] = 0;
          }
        } else
          sum = buf[pos + 1] * (period - 1) + array[pos];
        buf[pos] = sum / period;
        pos--;
      }
      return buf[shift + ma_shift];
    }

    case MODE_LWMA: {
      if (ArrayResize(buf, total) < 0)
        return 0;
      double sum = 0.0, lsum = 0.0;
      double price;
      int i, weight = 0, pos = total - 1;

      for (i = 1; i <= period; i++, pos--) {
        price = array[pos];
        sum += price * i;
        lsum += price;
        weight += i;
      }
      pos++;
      i = pos + period;
      while (pos >= 0) {
        buf[pos] = sum / weight;
        if (pos == 0)
          break;
        pos--;
        i--;
        price = array[pos];
        sum = sum - lsum + price * period;
        lsum -= array[i];
        lsum += price;
      }

      return buf[shift + ma_shift];
    }
  }

  return 0;
}
