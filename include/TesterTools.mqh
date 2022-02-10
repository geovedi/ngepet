//+------------------------------------------------------------------+
//|                                                  TesterTools.mqh |
//|                                      Copyright 2021, Jim Geovedi |
//|                                          https://jim.geovedi.com |
//+------------------------------------------------------------------+

#include <Math\Stat\Normal.mqh>
#include <Math\Stat\Uniform.mqh>
#include <Trade\DealInfo.mqh>
#include <Trade\HistoryOrderInfo.mqh>

#include "TradeHistory.mqh"

double SymmetryTrades() {
  double longPL = TesterStatistics(STAT_PROFIT_LONGTRADES);
  double shortPL = TesterStatistics(STAT_PROFIT_SHORTTRADES);

  double maxProfit = 0;
  double smallerProfit = 0;

  if (longPL == shortPL) {
    return 1.0;
  } else if ((longPL > 0 && shortPL <= 0) || (longPL <= 0 && shortPL > 0)) {
    return 0.0;
  } else if (MathAbs(longPL) > MathAbs(shortPL)) {
    maxProfit = MathAbs(longPL);
    smallerProfit = MathAbs(shortPL);
  } else {
    maxProfit = MathAbs(shortPL);
    smallerProfit = MathAbs(longPL);
  }

  if (smallerProfit < 0 && maxProfit >= 0) {
    return 0;
  }

  return smallerProfit / maxProfit;
}

bool GetTrades(double &trades[], datetime start_date, datetime end_date) {
  CHistoryPositionInfo pos;

  if (!pos.HistorySelect(start_date, end_date)) {
    PrintFormat("[ERROR] %s(): Failed to select history from %s to %s",
                __FUNCTION__, TimeToString(start_date), TimeToString(end_date));
    return (false);
  }

  int total = pos.PositionsTotal();
  for (int i = 0; i < total; i++) {
    if (pos.SelectByIndex(i)) {
      int size = ArraySize(trades);
      ArrayResize(trades, size + 1);
      trades[size] = pos.Profit() + pos.Swap() + (2 * pos.Commission());
    }
  }

  return (true);
}

double RollingSQN(int period = 30, int gap = 15, bool overlap = false) {
  HistorySelect(INT_MIN, INT_MAX);
  deal_info.Ticket(HistoryDealGetTicket(0));
  datetime start_date = deal_info.Time();

  double returns[];
  ArrayInitialize(returns, 0);

  while (start_date < TimeCurrent()) {
    datetime end_date = start_date + (period * PeriodSeconds(PERIOD_D1));
    double pr[];
    if (!GetTrades(pr, start_date, end_date))
      break;

    // double sc = MathSum(pr);
    double sc =
        (MathSqrt(ArraySize(pr)) * MathMean(pr)) / MathStandardDeviation(pr);
    if (!MathIsValidNumber(sc))
      sc = 0;

    int size = ArraySize(returns);
    ArrayResize(returns, size + 1);
    returns[size] = sc;
    
    if (overlap)
      start_date = end_date - (gap * PeriodSeconds(PERIOD_D1));
    else
      start_date = end_date + (gap * PeriodSeconds(PERIOD_D1));
  }

  if (ArraySize(returns) == 0)
    return 0;

  double score = (MathSqrt(ArraySize(returns)) * MathMean(returns)) /
                 MathStandardDeviation(returns);
  if (!MathIsValidNumber(score))
    return 0;

  PrintFormat("%d days period, %d days gap:", period, gap);
  ArrayPrint(returns);

  return MathMax(score, 0);
}

double FilteredScore(int min_trades = 30) {
  double trades[], score = -1.0;

  datetime start_date = StringToTime("1970.01.01 00:00");
  datetime end_date = TimeCurrent();

  if (!GetTrades(trades, start_date, end_date))
    return (score);

  int n_trades = ArraySize(trades);

  if (n_trades < min_trades)
    return (score);

  double mean = MathMean(trades);
  double std = MathStandardDeviation(trades);

  score = MathSqrt(n_trades) * mean / std;

  if (!MathIsValidNumber(score))
    return (-1.0);

  return (score);
}

double FilteredRMultiple(int min_trades = 30, double risk = 10.0) {
  double trades[], score = -1.0;

  datetime start_date = StringToTime("1970.01.01 00:00");
  datetime end_date = TimeCurrent();

  if (!GetTrades(trades, start_date, end_date))
    return (score);

  int n_trades = ArraySize(trades);

  if (n_trades < min_trades)
    return (score);

  double mean = MathMean(trades);
  double std = MathStandardDeviation(trades);

  double rr[];
  ArrayResize(rr, n_trades);

  int win = 0, loss = 0;
  for (int i = 0; i < n_trades; i++) {
    if (trades[i] > 0)
      win++;
    else
      loss++;
    rr[i] = (trades[i] / risk);
  }

  if (loss != 0)
    score = MathSqrt(n_trades) * MathMean(rr) / MathStandardDeviation(rr);
  else
    score = DBL_MAX;

  if (!MathIsValidNumber(score))
    return (-1.0);

  return (score);
}

double FilteredLR(int min_trades = 30) {
  double trades[], score = -1.0;

  datetime start_date = StringToTime("1970.01.01 00:00");
  datetime end_date = TimeCurrent();

  if (!GetTrades(trades, start_date, end_date))
    return (score);

  int n_trades = ArraySize(trades);

  if (n_trades < min_trades)
    return (score);

  // CRITERION_LR
  double a, b, std_error;
  double chart[];

  if (!CalculateLinearRegression(trades, chart, a, b))
    return (score);

  if (!CalculateStdError(chart, a, b, std_error))
    return (score);

  score = (std_error == 0.0) ? a * n_trades : a * n_trades / std_error;

  return (score);
}

double FilteredRollingLR(int min_trades = 30) {
  double trades[], score = -1.0;

  datetime start_date = StringToTime("1970.01.01 00:00");
  datetime end_date = TimeCurrent();

  if (!GetTrades(trades, start_date, end_date))
    return (score);

  int n_trades = ArraySize(trades);

  if (n_trades < min_trades)
    return (score);

  int chunk_size = 50;
  int n_chunks = (int)MathFloor(n_trades / chunk_size);

  double chunk_scores[];

  for (int i = 0; i < n_chunks; i++) {
    double chunk_score = 0;
    double chunk_trades[];

    int c_size = (i == n_chunks - 1) ? n_trades - (i * chunk_size) : chunk_size;

    ArrayResize(chunk_trades, c_size);
    ArrayCopy(chunk_trades, trades, 0, i * chunk_size, c_size);

    double a, b, std_error;
    double chart[];

    if (!CalculateLinearRegression(chunk_trades, chart, a, b))
      continue;

    if (!CalculateStdError(chart, a, b, std_error))
      continue;

    chunk_score = (std_error == 0.0) ? a * c_size : a * c_size / std_error;

    int size = ArraySize(chunk_scores);
    ArrayResize(chunk_scores, size + 1);
    chunk_scores[size] = chunk_score;
  }

  ArrayPrint(chunk_scores);

  score = (MathSqrt(ArraySize(chunk_scores)) * MathMean(chunk_scores) /
           MathStandardDeviation(chunk_scores));

  if (!MathIsValidNumber(score))
    return (-1.0);

  return (score);
}

bool CalculateLinearRegression(double &change[], double &chartline[],
                               double &a_coef, double &b_coef) {
  if (ArraySize(change) < 3)
    return (false);

  int N = ArraySize(change);
  ArrayResize(chartline, N);
  chartline[0] = change[0];
  for (int i = 1; i < N; i++)
    chartline[i] = chartline[i - 1] + change[i];

  double x = 0, y = 0, x2 = 0, xy = 0;
  for (int i = 0; i < N; i++) {
    x = x + i;
    y = y + chartline[i];
    xy = xy + i * chartline[i];
    x2 = x2 + i * i;
  }
  a_coef = (N * xy - x * y) / (N * x2 - x * x);
  b_coef = (y - a_coef * x) / N;

  return (true);
}

bool CalculateStdError(double &data[], double a_coef, double b_coef,
                       double &std_err) {
  double error = 0;
  int N = ArraySize(data);
  if (N <= 2)
    return (false);
  for (int i = 0; i < N; i++)
    error += MathPow(a_coef * i + b_coef - data[i], 2);
  std_err = MathSqrt(error / (N - 2));

  return (true);
}

double NormalizedProfitFactor() {
  double trades[], score = -1.0;

  datetime start_date = StringToTime("1970.01.01 00:00");
  datetime end_date = TimeCurrent();

  if (!GetTrades(trades, start_date, end_date))
    return (score);

  int n_trades = ArraySize(trades);

  double mean = MathMean(trades);
  double std = MathStandardDeviation(trades);
  double max_limit = mean + (2 * std);
  double min_limit = mean - (2 * std);

  double gross_profit = 0, gross_loss = 0;

  for (int i = 0; i < n_trades; i++) {
    double profit = 0;

    if (trades[i] >= max_limit) {
      profit = max_limit;
    } else {
      profit = trades[i];
    }

    if (profit > 0)
      gross_profit += profit;
    else if (profit < 0)
      gross_loss += profit;
  }

  if ((gross_profit + gross_loss <= 0) || gross_loss >= 0)
    return (score);

  score = gross_profit / -gross_loss;

  PrintFormat("[DEBUG] %s: Gross profit=%f, gross loss=%f, score=%f",
              __FUNCTION__, gross_profit, gross_loss, score);

  return (score);
}

#define NSAMPLES 10000 // number of samples in Monte Carlo method
#define NADD 30

double MonteCarloScore() {
  double k[];

  if (!MCSetKS(k))
    return -1.0;

  if (ArraySize(k) < 30)
    return -1.0;

  MathSrand(GetTickCount());

  // total profit median + interquartile range parameter
  double km[], cn[NSAMPLES];
  int nk = ArraySize(k);
  ArrayResize(km, nk);

  for (int n = 0; n < NSAMPLES; ++n) {
    MCSample(k, km);
    cn[n] = 1.0;
    for (int i = 0; i < nk; ++i)
      cn[n] *= km[i];
    cn[n] -= 1.0;
  }

  ArraySort(cn);

  return cn[(int)(0.5 * NSAMPLES)] /
         (cn[(int)(0.75 * NSAMPLES)] - cn[(int)(0.25 * NSAMPLES)]);
}

void MCSample(double &a[], double &b[]) {
  int ner;
  double dnc;
  int na = ArraySize(a);

  for (int i = 0; i < na; ++i) {
    dnc = MathRandomUniform(0, na, ner);
    if (!MathIsValidNumber(dnc)) {
      Print("MathIsValidNumber(dnc) error ", ner);
      return;
    }

    int nc = (int)dnc;
    if (nc == na)
      nc = na - 1;

    b[i] = a[nc];
  }
}

bool MCSetKS(double &k[]) {
  if (!HistorySelect(0, TimeCurrent()))
    return false;
  uint nhd = HistoryDealsTotal();
  int nk = 0;
  ulong hdticket;
  double capital = TesterStatistics(STAT_INITIAL_DEPOSIT);
  long hdtype;
  double hdcommission, hdswap, hdprofit, hdprofit_full;
  for (uint n = 0; n < nhd; ++n) {
    hdticket = HistoryDealGetTicket(n);
    if (hdticket == 0)
      continue;

    if (!HistoryDealGetInteger(hdticket, DEAL_TYPE, hdtype))
      return false;
    if (hdtype != DEAL_TYPE_BUY && hdtype != DEAL_TYPE_SELL)
      continue;

    hdcommission = HistoryDealGetDouble(hdticket, DEAL_COMMISSION);
    hdswap = HistoryDealGetDouble(hdticket, DEAL_SWAP);
    hdprofit = HistoryDealGetDouble(hdticket, DEAL_PROFIT);
    if (hdcommission == 0.0 && hdswap == 0.0 && hdprofit == 0.0)
      continue;

    ++nk;
    ArrayResize(k, nk, NADD);
    hdprofit_full = hdcommission + hdswap + hdprofit;
    k[nk - 1] = 1.0 + hdprofit_full / capital;
    capital += hdprofit_full;
  }
  return true;
}

double CSTS() {
  double avg_win = TesterStatistics(STAT_GROSS_PROFIT) /
                   TesterStatistics(STAT_PROFIT_TRADES);
  double avg_loss =
      -TesterStatistics(STAT_GROSS_LOSS) / TesterStatistics(STAT_LOSS_TRADES);
  double win_perc = 100.0 * TesterStatistics(STAT_PROFIT_TRADES) /
                    TesterStatistics(STAT_TRADES);

  //  Calculated safe ratio for this percentage of profitable deals:
  double teor = (110.0 - win_perc) / (win_perc - 10.0) + 1.0;

  //  Calculate real ratio:
  double real = avg_win / avg_loss;

  //  CSTS:
  double tssf = real / teor;

  return (tssf);
}
