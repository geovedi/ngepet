# DERIV

## Symbols

| Symbols | Last Spread | Mean Spread | Max Spread | Slippage | Stops Level | Min Lot | Max Lot | Lot Step | Volume Limit |
|---------|-------------|-------------|------------|----------|-------------|---------|---------|----------|--------------|
| VIX10   | 136         | 520         | 1000       | 20       | 500         | 0.3     | 100     | 0.01     | 500          |
| VIX25   | 111         | 304         | 600        | 20       | 600         | 0.5     | 100     | 0.01     | 600          |
| VIX50   | 202         | 1791        | 4000       | 20       | 700         | 3.0     | 1000    | 0.01     | 3000         |
| VIX75   | 15900       | 8231        | 60000      | 20       | 50000       | 0.001   | 1       | 0.001    | 2            |
| VIX100  | 240         | 236         | 2000       | 20       | 120         | 0.2     | 50      | 0.01     | 100          |

Last update: 14 March 2022

---

## Hacks

### VIX75 wrong volume size calculation

There is an issue with VIX75 symbol where `sqMMFixedAmount()` in the exported MQL5 code gives wrong volume size. Current workaround is by multiplying `oneLotSLDrawdown` value by 100. 

Affected template (SQX Build 135.868): `...\StrategyQuantX\internal\extend\Code\MetaTrader5\MoneyManagement\FixedAmount_class.tpl`

```mql5
   double oneLotSLDrawdown = PointValue * MathAbs(openPrice - sl) * ((correctedSymbol == "Volatility 75 Index") ? 100 : 1);
```

