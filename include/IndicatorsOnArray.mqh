//+------------------------------------------------------------------+
//|                                            IndicatorsOnArray.mqh |
//|                                                        Max Lapan |
//|                                                   blog.shmuma.ru |
//+------------------------------------------------------------------+

#property copyright "Max Lapan"
#property link      "http://blog.shmuma.ru"

double iRSIOnArray(double& data[], int period)
{
   if (period <= 0) {
      Alert("iRSIOnArray: invalid argument for period");
      return 0.0;
   }
   if (ArraySize(data) < period) {
      Alert("iRSIOnArray: to little data to calculate");
      return 0.0;
   }
   
   int i;
   double psum = 0.0, nsum = 0.0;
   double pos, neg, prev_pos, prev_neg;
   double delta;
   
   // initial accumulation
   for (i = 1; i < period; i++) {
      delta = data[i] - data[i-1];
      if (delta > 0)
         psum += delta;
      else
         nsum -= delta;
   }
   
   pos = psum / period;
   neg = psum / period;
   
   for (i = period; i < ArraySize(data); i++) {
      psum = 0.0;
      nsum = 0.0;
      prev_pos = pos;
      prev_neg = neg;
      delta = data[i] - data[i-1];
      if (delta > 0)
         psum = delta;
      else
         nsum = -delta;
         
      pos = (prev_pos * (period-1) + psum) / period;
      neg = (prev_neg * (period-1) + nsum) / period;
   }
   
   double rsi = 0.0;
   
   if (neg > 1e-5)
      rsi = 100.0 - 100.0 / (1 + pos / neg);
   return rsi;
}


bool test_iRSIOnArray()
{
/*
   double data[];
   int size = 40;
   int count = CopyClose("EURUSD", PERIOD_H1, 1, size, data);
   
   PrintFormat("Got %d data items", count);
  
   if (count == 40) {
      string str = "";
      for (int i = 0; i < 40; i++)
         str += StringFormat("%.5f, ", data[i]);
      Print("Data: " + str);
      
      int handle = iRSI("EURUSD", PERIOD_H1, 14, PRICE_CLOSE);
      double res[];
      if (CopyBuffer(handle, 0, 1, 1, res) == 1)
         PrintFormat("RSI = %.2f", res[0]);
      IndicatorRelease(handle);
   }

*/
   double vals[] = {1.38972, 1.38970, 1.38948, 1.38866, 1.38823, 1.38845, 1.38598, 1.38438, 1.38469, 1.38479,
                    1.38514, 1.38502, 1.38531, 1.38560, 1.38515, 1.38395, 1.38521, 1.38201, 1.38228, 1.38314,
                    1.38280, 1.38161, 1.38239, 1.38151, 1.38239, 1.38278, 1.38240, 1.38207, 1.38172, 1.38205,
                    1.38181, 1.38162, 1.38153, 1.38162, 1.38173, 1.38159, 1.38142, 1.38160, 1.38158, 1.38130};

   double rsi = iRSIOnArray(vals, 14);
   double expected = 37.171869;

   if (MathAbs(rsi - expected) < 1e-3)
      return true;
   else
      PrintFormat("Result mismatch, expected %f, got %f", expected, rsi);
   return false;
}


double iMAOnArray(double& array[], int period, int ma_shift, ENUM_MA_METHOD ma_method, int shift)
{
   double buf[], arr[];
   int total = ArraySize(array);
   
   if(total <= period)
      return 0;
      
   if(shift > total - period - ma_shift)
      return 0;
      
   switch(ma_method)
   {
   case MODE_SMA: {
      total = ArrayCopy(arr, array, 0, shift + ma_shift, period);
      if (ArrayResize(buf, total) < 0)
         return 0;
      double sum = 0;
      int i, pos = total-1;
      
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
            buf[pos+1] = array[pos+1];
         buf[pos] = array[pos] * pr + buf[pos+1] * (1-pr);
         pos--;
      }
      return buf[shift+ma_shift];
   }
   
   case MODE_SMMA: {
      if (ArrayResize (buf, total) < 0)
         return(0);
      double sum = 0;
      int i, k, pos;
      
      pos = total - period;
      while (pos >= 0) {
         if (pos == total - period) {
            for (i = 0, k = pos; i < period; i++, k++) {
               sum += array[k];
               buf[k] = 0;
            }
         }
         else
            sum = buf[pos+1] * (period-1) + array[pos];
         buf[pos]=sum/period;
         pos--;
      }
      return buf[shift+ma_shift];
   }
   
   case MODE_LWMA: {
         if (ArrayResize (buf, total) < 0)
            return 0;
         double sum = 0.0, lsum = 0.0;
         double price;
         int i, weight = 0, pos = total-1;
         
         for(i = 1; i <= period; i++, pos--) {
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
         
         return buf[shift+ma_shift];
      }
   }
   return 0;
}


// Calculates bollinger bands indicator from array data
bool iBBOnArray(double& data[], int period, double deviations, double& dnBand, double& ma, double& upBand)
{
   int size = ArraySize(data);
   if (size < period)
      return false;
   if (period <= 0)
      return false;
      
   ma = iMAOnArray(data, period, 0, MODE_SMA, 0);
   
   double sum = 0.0, val;
   int i;
   
   for (i = 0; i < period; i++) {
      val = data[size - i - 1] - ma;
      sum += val * val;
   }
   
   double dev = deviations * MathSqrt(sum / period);
   dnBand = ma - dev;
   upBand = ma + dev;
   return true;
}


bool test_IndicatorsOnArray()
{
   Print("Start IndicatorsOnArray test suite...");
   
   bool res = true;
   string prefix = "1. iRSIOnArray: ";
   Print(prefix + "run...");
   if (test_iRSIOnArray())
      Print(prefix + "PASSED");
   else {
      res = false;
      Print(prefix + "_FAILED_");  
   }
   
   return res;
}
