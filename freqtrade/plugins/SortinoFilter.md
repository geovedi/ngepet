# Experimental Plugins: Sortino Filter


Requires patching:

```diff
diff --git a/freqtrade/constants.py b/freqtrade/constants.py
index 37e2d849c..2ae810472 100644
--- a/freqtrade/constants.py
+++ b/freqtrade/constants.py
@@ -35,7 +35,7 @@ HYPEROPT_LOSS_BUILTIN = ['ShortTradeDurHyperOptLoss', 'OnlyProfitHyperOptLoss',
 AVAILABLE_PAIRLISTS = ['StaticPairList', 'VolumePairList', 'ProducerPairList', 'RemotePairList',
                        'MarketCapPairList', 'AgeFilter', "FullTradesFilter", 'OffsetFilter',
                        'PerformanceFilter', 'PrecisionFilter', 'PriceFilter',
-                       'RangeStabilityFilter', 'ShuffleFilter', 'SpreadFilter',
+                       'RangeStabilityFilter', 'ShuffleFilter', 'SpreadFilter', 'SortinoFilter',
                        'VolatilityFilter']
 AVAILABLE_PROTECTIONS = ['CooldownPeriod',
                          'LowProfitPairs', 'MaxDrawdown', 'StoplossGuard']
```

Default configuration

```json
  "pairlists": [
    // ...
    {
      "method": "SortinoFilter",
      "lookback_days": 10,
      "min_sortino_ratio": 0.0,
      "refresh_period": 86400
    }
```
