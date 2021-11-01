//+------------------------------------------------------------------+
//|                                                  TesterTools.mqh |
//|                                      Copyright 2021, Jim Geovedi |
//|                                          https://jim.geovedi.com |
//+------------------------------------------------------------------+

#include <Math\Stat\Normal.mqh>
#include <Trade\DealInfo.mqh>
#include <Trade\HistoryOrderInfo.mqh>

#include "TradeHistory.mqh"

CDealInfo deal_info;

bool GetTrades(double &trades[], int min_level = 0) {
  CHistoryPositionInfo pos;

  datetime start_date = StringToTime("1970.01.01 00:00");
  datetime end_date = TimeCurrent();

  if (!pos.HistorySelect(start_date, end_date)) {
    PrintFormat("[ERROR] %s(): Failed to select history from %s to %s",
                __FUNCTION__, TimeToString(start_date), TimeToString(end_date));
    return (false);
  }

  int total = pos.PositionsTotal();
  for (int i = 0; i < total; i++) {
    if (pos.SelectByIndex(i)) {
      if ((int)pos.OpenComment() >= min_level) {
        int size = ArraySize(trades);
        ArrayResize(trades, size + 1);
        trades[size] = pos.Profit() + pos.Swap() + (2 * pos.Commission());
      }
    }
  }

  return (true);
}

double FilteredScore(int min_level = 0, int min_trades = 30) {
  double trades[], score = -1.0;

  if (!GetTrades(trades, min_level))
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

double FilteredRMultiple(int min_level = 0, int min_trades = 30,
                         double risk = 10.0) {
  double trades[], score = -1.0;

  if (!GetTrades(trades, min_level))
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

double FilteredLR(int min_level = 0, int min_trades = 30) {
  double trades[], score = -1.0;

  if (!GetTrades(trades, min_level))
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

double FilteredRollingLR(int min_level = 0, int min_trades = 30) {
  double trades[], score = -1.0;

  if (!GetTrades(trades, min_level))
    return (score);

  int n_trades = ArraySize(trades);

  if (n_trades < min_trades)
    return (score);

  int chunk_size = 100;
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

  if (!GetTrades(trades))
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
