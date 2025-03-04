import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from scipy import stats
import talib as ta
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')


class MomentumReversalTracker:
    """
    Class to track momentum and detect bullish trend reversals for LONG positions.
    
    This class analyzes stock data to identify potential reversal candidates based on
    technical indicators including RSI, MACD, Bollinger Bands, and moving averages.
    It calculates momentum scores, detects reversal signals, and generates
    visualization charts for the most promising candidates.
    
    Attributes:
        data_folder (str): Directory containing stock data CSV files
        start_date (datetime): Starting date for analysis
        output_dir (str): Directory for storing output files and charts
        stock_data (dict): Dictionary storing processed stock data
        reversal_candidates (DataFrame): Stocks showing potential reversal signals
        market_regimes (DataFrame): Market regime classification data (if available)
    """
    
    def __init__(self, data_folder="Nasdaq/Stock", start_date="2019-06-02", output_dir="momentum_output"):
        """
        Initialize the MomentumReversalTracker.
        
        Args:
            data_folder (str): Directory containing stock data CSV files
            start_date (str): Starting date for analysis in YYYY-MM-DD format
            output_dir (str): Directory for storing output files and charts
        """
        self.data_folder = data_folder
        self.start_date = pd.to_datetime(start_date)
        self.output_dir = output_dir
        self.stock_data = {}
        self.reversal_candidates = None
        self.market_regimes = None
        
        # Create output directory if it doesn't exist
        self._setup_output_directory()
    
    def _setup_output_directory(self):
        """
        Create output directory structure and clean previous output files.
        """
        # Create main output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # Create plots directory within output directory
        plots_dir = os.path.join(self.output_dir, "reversal_plots")
        if not os.path.exists(plots_dir):
            os.makedirs(plots_dir)
        else:
            # Clean existing plot files
            for file in os.listdir(plots_dir):
                try:
                    os.remove(os.path.join(plots_dir, file))
                except Exception as e:
                    print(f"Could not remove plot file: {e}")
        
        # Clean previous CSV reports in the output directory
        for file in ['reversal_candidates.csv', 'reversal_signals.csv', 'reversal_candidates_summary.csv']:
            file_path = os.path.join(self.output_dir, file)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Could not remove {file}: {e}")
    
    def load_stock_data(self):
        """
        Load all stock data from CSV files in the specified directory.
        
        Returns:
            dict: Dictionary of processed stock data frames
        """
        # Find all CSV files
        file_paths = []
        for root, dirs, files in os.walk(self.data_folder):
            for file in files:
                if file.endswith(('.csv', '.txt')):
                    file_paths.append(os.path.join(root, file))
        
        # Load and process each file
        for file_path in file_paths:
            try:
                stock_name = os.path.basename(file_path).split('.')[0]
                df = pd.read_csv(file_path, sep='\t')
                
                # Process MetaTrader format
                if '<DATE>' in df.columns:
                    df['DATETIME'] = pd.to_datetime(df['<DATE>'] + ' ' + df['<TIME>'], 
                                                  format='%Y.%m.%d %H:%M:%S')
                    df = df.rename(columns={
                        '<CLOSE>': 'CLOSE', '<OPEN>': 'OPEN',
                        '<HIGH>': 'HIGH', '<LOW>': 'LOW', '<VOL>': 'VOL'
                    })
                    df = df[['DATETIME', 'CLOSE', 'OPEN', 'HIGH', 'LOW', 'VOL']]
                    
                    # Filter by date and ensure enough data points
                    if len(df[df['DATETIME'] < self.start_date]) == 0:
                        continue
                    df = df[df['DATETIME'] >= self.start_date]
                    
                    if len(df) >= 60:
                        df = df.sort_values('DATETIME').reset_index(drop=True)
                        df = df.astype({'CLOSE': float, 'OPEN': float, 'HIGH': float, 
                                      'LOW': float, 'VOL': float})
                        
                        # Calculate ATR
                        df['TR'] = ta.ATR(df['HIGH'].values, df['LOW'].values, 
                                         df['CLOSE'].values, timeperiod=14)
                        df['ATR_pct'] = df['TR'] / df['CLOSE'] * 100
                        
                        self.stock_data[stock_name] = df
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
        
        print(f"Loaded data for {len(self.stock_data)} stocks")
        return self.stock_data
    
    def calculate_momentum_scores(self):
        """
        Calculate momentum scores for all stocks based on technical indicators.
        
        Returns:
            DataFrame: DataFrame containing momentum metrics for all analyzed stocks
        """
        momentum_data = []
        
        for symbol, df in self.stock_data.items():
            try:
                if len(df) < 60:  # Need enough data for reliable analysis
                    continue
                
                metrics = {'Symbol': symbol}
                
                # Add technical indicators
                df['rsi'] = ta.RSI(df['CLOSE'].values, timeperiod=14)
                
                macd, signal, hist = ta.MACD(df['CLOSE'].values)
                df['macd'], df['macd_signal'], df['macd_hist'] = macd, signal, hist
                
                upper, middle, lower = ta.BBANDS(df['CLOSE'].values)
                df['bb_upper'], df['bb_middle'], df['bb_lower'] = upper, middle, lower
                df['bb_position'] = (df['CLOSE'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
                
                # Moving Averages
                for ma_period in [20, 50, 200]:
                    if len(df) >= ma_period:
                        df[f'sma_{ma_period}'] = ta.SMA(df['CLOSE'].values, timeperiod=ma_period)
                
                # Calculate daily price returns
                df['returns'] = df['CLOSE'].pct_change()
                
                # Add ATR values to metrics
                if 'ATR_pct' in df.columns and not df['ATR_pct'].isna().all():
                    metrics['latest_atr_pct'] = df['ATR_pct'].iloc[-1]
                    metrics['avg_atr_pct'] = df['ATR_pct'].iloc[-10:].mean()
                
                # Calculate daily momentum scores
                self._calculate_daily_momentum_scores(df)
                
                # Check for reversal signals
                self._check_for_reversal_signals(df, metrics)
                
                # Calculate long tradability score
                self._calculate_long_tradability(df, metrics)
                
                # Add to momentum data
                momentum_data.append(metrics)
                
            except Exception as e:
                print(f"Error processing {symbol}: {e}")
        
        return pd.DataFrame(momentum_data)
    
    def _calculate_daily_momentum_scores(self, df):
        """
        Calculate daily momentum scores for a single stock.
        
        The momentum score (0-100) is composed of 5 equally weighted components:
        1. Short-term return (5-day)
        2. RSI indicator
        3. MACD momentum
        4. Price relative to moving averages
        5. Bollinger Band position
        
        Args:
            df (DataFrame): Stock data with technical indicators
        """
        # Create empty momentum score column
        df['momentum_score'] = np.nan
        
        # For each day (starting from day 20 to have enough history)
        for i in range(20, len(df)):
            # Component 1: Short-term return (5-day)
            ret_5d = df['CLOSE'].iloc[i] / df['CLOSE'].iloc[i-5] - 1
            ret_5d_score = ret_5d * 20  # Scale: 20% weight
            
            # Component 2: RSI
            rsi_score = 0
            if pd.notnull(df['rsi'].iloc[i]):
                rsi = df['rsi'].iloc[i]
                if 60 <= rsi <= 70: rsi_score = 1.0
                elif 50 <= rsi < 60: rsi_score = 0.8
                elif 70 < rsi <= 80: rsi_score = 0.6
                elif 40 <= rsi < 50: rsi_score = 0.5
                elif 30 <= rsi < 40: rsi_score = 0.3
                elif 80 < rsi <= 90: rsi_score = 0.2
                rsi_score *= 20  # Scale: 20% weight
            
            # Component 3: MACD
            macd_score = 0
            if pd.notnull(df['macd_hist'].iloc[i]) and pd.notnull(df['macd_hist'].iloc[i-1]):
                macd_hist = df['macd_hist'].iloc[i]
                macd_hist_prev = df['macd_hist'].iloc[i-1]
                
                if macd_hist > 0 and macd_hist > macd_hist_prev: macd_score = 1.0
                elif macd_hist > 0: macd_score = 0.7
                elif macd_hist < 0 and macd_hist > macd_hist_prev: macd_score = 0.4
                else: macd_score = 0.0
                
                macd_score *= 20  # Scale: 20% weight
            
            # Component 4: Price relative to moving averages
            ma_score = 0
            if pd.notnull(df['sma_20'].iloc[i]) and pd.notnull(df['sma_50'].iloc[i]):
                price = df['CLOSE'].iloc[i]
                sma20 = df['sma_20'].iloc[i]
                sma50 = df['sma_50'].iloc[i]
                
                if price > sma20 and price > sma50: ma_score = 1.0
                elif price > sma20: ma_score = 0.7
                elif price > sma50: ma_score = 0.5
                else: ma_score = 0.2
                
                ma_score *= 20  # Scale: 20% weight
            
            # Component 5: Bollinger Band position
            bb_score = 0
            if pd.notnull(df['bb_position'].iloc[i]):
                bb_pos = df['bb_position'].iloc[i]
                
                if 0.6 <= bb_pos <= 0.8: bb_score = 1.0
                elif 0.8 < bb_pos <= 1.0: bb_score = 0.7
                elif 0.4 <= bb_pos < 0.6: bb_score = 0.6
                elif 0.2 <= bb_pos < 0.4: bb_score = 0.3
                else: bb_score = 0.2
                
                bb_score *= 20  # Scale: 20% weight
            
            # Combine and scale to 0-100
            daily_score = ret_5d_score + rsi_score + macd_score + ma_score + bb_score
            daily_score = max(0, min(100, daily_score))
            
            # Store the momentum score
            df.loc[df.index[i], 'momentum_score'] = daily_score
            
            # Store recent momentum scores and changes
            if i == len(df) - 1:  # Last day
                mom_scores = df['momentum_score'].dropna()
                for j in range(1, min(11, len(mom_scores) + 1)):
                    if len(mom_scores) >= j:
                        metrics = getattr(df, 'metrics', {})
                        metrics[f'momentum_score_day_minus_{j}'] = mom_scores.iloc[-j]
                        df.metrics = metrics
                        
                # Calculate momentum score changes
                if len(mom_scores) >= 5:
                    metrics = getattr(df, 'metrics', {})
                    metrics['momentum_score_5d_change'] = mom_scores.iloc[-1] - mom_scores.iloc[-5]
                    df.metrics = metrics
    
    def _check_for_reversal_signals(self, df, metrics):
        """
        Check for potential trend reversal signals in a stock.
        
        Analyzes various technical indicators to identify bullish reversal patterns:
        1. RSI oversold bounce
        2. MACD crossovers and zero-line crosses
        3. Bollinger Band bounces
        4. Moving average crosses
        5. Higher low pattern
        6. Volume spike with positive price movement
        7. Price position relative to key moving averages
        
        Args:
            df (DataFrame): Stock data with technical indicators
            metrics (dict): Dictionary to store detected signals and metrics
        """
        try:
            if len(df) < 20:
                return
            
            # 1. RSI oversold bounce
            if 'rsi' in df.columns and len(df['rsi']) >= 10:
                min_rsi_5d = min(df['rsi'].iloc[-5:])
                current_rsi = df['rsi'].iloc[-1]
                if min_rsi_5d < 30 and current_rsi > df['rsi'].iloc[-3] and current_rsi < 50:
                    metrics['reversal_signal_rsi_bounce'] = True
            
            # 2. MACD signals
            if all(col in df.columns for col in ['macd', 'macd_signal']):
                # MACD zero line crossover
                if df['macd'].iloc[-2] < 0 and df['macd'].iloc[-1] > 0:
                    metrics['reversal_signal_macd_zero_cross'] = True
                
                # MACD signal line crossover
                if df['macd'].iloc[-2] < df['macd_signal'].iloc[-2] and df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]:
                    metrics['reversal_signal_macd_signal_cross'] = True
            
            # 3. Bollinger Band bounce
            if 'bb_position' in df.columns:
                min_bb_position = min(df['bb_position'].iloc[-5:])
                current_bb_position = df['bb_position'].iloc[-1]
                if min_bb_position < 0.2 and current_bb_position > 0.3 and current_bb_position < 0.5:
                    metrics['reversal_signal_bb_bounce'] = True
            
            # 4. MA cross
            if 'sma_20' in df.columns:
                if (df['CLOSE'].iloc[-3] < df['sma_20'].iloc[-3] and 
                    df['CLOSE'].iloc[-2] < df['sma_20'].iloc[-2] and 
                    df['CLOSE'].iloc[-1] > df['sma_20'].iloc[-1]):
                    metrics['reversal_signal_ma_cross'] = True
            
            # 5. Higher low pattern
            if len(df) >= 20:
                recent_lows = []
                for i in range(5, 20):
                    if (df['CLOSE'].iloc[-i] < df['CLOSE'].iloc[-i-1] and 
                        df['CLOSE'].iloc[-i] < df['CLOSE'].iloc[-i+1]):
                        recent_lows.append((len(df)-i, df['CLOSE'].iloc[-i]))
                
                if len(recent_lows) >= 2:
                    recent_lows.sort()
                    if recent_lows[-1][1] > recent_lows[-2][1]:
                        metrics['reversal_signal_higher_low'] = True
            
            # 6. Volume spike with price increase
            if 'VOL' in df.columns:
                avg_volume = df['VOL'].iloc[-10:-1].mean()
                if df['VOL'].iloc[-1] > 2 * avg_volume and df['returns'].iloc[-1] > 0:
                    metrics['reversal_signal_volume_spike'] = True
            
            # 7. Price above key MAs
            if 'sma_50' in df.columns and 'sma_200' in df.columns:
                price = df['CLOSE'].iloc[-1]
                sma50 = df['sma_50'].iloc[-1]
                sma200 = df['sma_200'].iloc[-1]
                
                metrics['price_above_sma50'] = price > sma50
                metrics['price_above_sma200'] = price > sma200
                metrics['golden_cross_condition'] = sma50 > sma200
                
                if metrics.get('price_above_sma50', False) and metrics.get('price_above_sma200', False) and metrics.get('golden_cross_condition', False):
                    metrics['strong_uptrend_bonus'] = True
            
            # Calculate reversal score
            reversal_score = 0
            # Count triggered signals
            signal_count = sum(1 for key in metrics if key.startswith('reversal_signal_') 
                              and key != 'reversal_signal_strength' and metrics.get(key, False))
            
            reversal_score = signal_count * 15  # Each signal adds 15 points
            
            # Add bonus points
            if metrics.get('strong_uptrend_bonus', False):
                reversal_score += 15
            if metrics.get('price_above_sma50', False):
                reversal_score += 5
            if metrics.get('price_above_sma200', False):
                reversal_score += 5
            
            # Set final score
            if reversal_score > 0:
                metrics['reversal_score'] = min(100, reversal_score)
                
                # Label for potential
                if reversal_score >= 70:
                    metrics['reversal_potential'] = 'Very Strong'
                elif reversal_score >= 50:
                    metrics['reversal_potential'] = 'Strong'
                elif reversal_score >= 30:
                    metrics['reversal_potential'] = 'Moderate'
                else:
                    metrics['reversal_potential'] = 'Weak'
                    
        except Exception as e:
            print(f"Error checking for reversal signals: {e}")
            # Ensure we have a default reversal score even on error
            if 'reversal_score' not in metrics:
                metrics['reversal_score'] = 0
    
    def _calculate_long_tradability(self, df, metrics):
        """
        Calculate long tradability score based on reversal signals and trend strength.
        
        Args:
            df (DataFrame): Stock data with technical indicators
            metrics (dict): Dictionary containing reversal metrics
            
        Returns:
            dict: Updated metrics dictionary with long tradability score
        """
        tradability_score = 0
        
        # Base score from reversal score if available
        if 'reversal_score' in metrics:
            tradability_score = metrics['reversal_score'] * 0.5  # 50% weight
            
        # Add points for being in an uptrend
        if metrics.get('price_above_sma50', False):
            tradability_score += 10
        if metrics.get('price_above_sma200', False):
            tradability_score += 15
        if metrics.get('golden_cross_condition', False):
            tradability_score += 10
            
        # Add points for momentum factors
        if 'momentum_score_day_minus_1' in metrics:
            mom_score = metrics['momentum_score_day_minus_1']
            if isinstance(mom_score, (int, float)) and mom_score > 60:
                tradability_score += 10
                
        if 'momentum_score_5d_change' in metrics:
            mom_change = metrics['momentum_score_5d_change']
            if isinstance(mom_change, (int, float)) and mom_change > 0:
                tradability_score += mom_change * 2  # 2 points for each point of momentum increase
                
        # Cap at 100
        metrics['long_tradability'] = min(100, tradability_score)
        return metrics
    
    def find_reversal_candidates(self, min_reversal_score=30, min_atr_pct=1.0, max_atr_pct=None):
        """
        Find stocks showing potential reversal signals.
        
        Args:
            min_reversal_score (float): Minimum reversal score to consider (0-100)
            min_atr_pct (float): Minimum Average True Range percentage for volatility
            max_atr_pct (float, optional): Maximum ATR percentage to consider
        
        Returns:
            DataFrame: Filtered and sorted reversal candidates
        """
        # Calculate momentum metrics for all stocks
        momentum_df = self.calculate_momentum_scores()
        
        if momentum_df.empty:
            print("No stock data available.")
            return pd.DataFrame()
        
        # Filter by reversal score
        reversal_candidates = momentum_df[momentum_df.get('reversal_score', 0) >= min_reversal_score].copy()
        
        # Apply ATR filter
        if 'avg_atr_pct' in reversal_candidates.columns:
            reversal_candidates = reversal_candidates[reversal_candidates['avg_atr_pct'] >= min_atr_pct]
            if max_atr_pct is not None:
                reversal_candidates = reversal_candidates[reversal_candidates['avg_atr_pct'] <= max_atr_pct]
        
        if len(reversal_candidates) > 0:
            # Sort by long_tradability if available, otherwise by reversal_score
            if 'long_tradability' in reversal_candidates.columns:
                reversal_candidates = reversal_candidates.sort_values('long_tradability', ascending=False)
            else:
                reversal_candidates = reversal_candidates.sort_values('reversal_score', ascending=False)
            
            # Save to CSV in output directory
            reversal_candidates.to_csv(os.path.join(self.output_dir, "reversal_candidates.csv"), index=False)
            
            self.reversal_candidates = reversal_candidates
            return reversal_candidates
        else:
            print("No reversal candidates found.")
            return pd.DataFrame()

    def generate_consolidated_charts(self, top_n=10):
        """
        Generate consolidated charts for top reversal candidates for LONG positions.
        
        Creates comprehensive visual analysis charts combining price action,
        technical indicators, and detected reversal signals for each candidate.
        
        Args:
            top_n (int): Number of top candidates to chart
        """
        if self.reversal_candidates is None or self.reversal_candidates.empty:
            print("No reversal candidates available. Run find_reversal_candidates() first.")
            return
        
        # Create directory for plots
        plots_dir = os.path.join(self.output_dir, "reversal_plots")
        if not os.path.exists(plots_dir):
            os.makedirs(plots_dir)
        
        # Select top candidates to chart - prioritize by long_tradability if available
        if 'long_tradability' in self.reversal_candidates.columns:
            top_candidates = self.reversal_candidates.sort_values('long_tradability', ascending=False).head(top_n)
        else:
            top_candidates = self.reversal_candidates.head(top_n)
        
        # Generate summary comparison chart of all top candidates
        self._generate_summary_comparison(top_candidates, plots_dir)
        
        # Generate market regime chart if available
        if self.market_regimes is not None:
            self._generate_market_regime_chart(plots_dir)
        
        # Generate individual stock charts for top candidates
        for _, row in top_candidates.iterrows():
            symbol = row['Symbol']
            
            if symbol in self.stock_data:
                df = self.stock_data[symbol].copy()
                
                if 'momentum_score' not in df.columns or df['momentum_score'].isna().all():
                    continue  # Skip if no momentum score data
                
                try:
                    # Only use recent data for clarity (last 120 days or less)
                    plot_days = 120
                    recent_df = df.iloc[-plot_days:].copy() if len(df) > plot_days else df.copy()
                    
                    # Create a consolidated analysis chart with all key metrics
                    plt.figure(figsize=(14, 16))
                    
                    # Add a title with key metrics
                    reversal_score = row.get("reversal_score", 0)
                    reversal_potential = row.get("reversal_potential", "N/A")
                    long_tradability = row.get("long_tradability", 0)
                    latest_atr_pct = row.get("latest_atr_pct", 0)
                    
                    plt.suptitle(f"{symbol} - Comprehensive Reversal Analysis\n" + 
                               f"Reversal Score: {reversal_score:.1f} | Potential: {reversal_potential} | " +
                               f"LONG Tradability: {long_tradability:.1f} | ATR: {latest_atr_pct:.2f}%",
                               fontsize=16, y=0.995)
                    
                    # 1. Price chart with moving averages, Bollinger Bands and entry/exit points
                    ax1 = plt.subplot2grid((4, 2), (0, 0), colspan=2, rowspan=1)
                    
                    # Price and Bollinger Bands
                    ax1.plot(recent_df['DATETIME'], recent_df['CLOSE'], color='black', linewidth=2, label='Price')
                    
                    if all(col in recent_df.columns for col in ['bb_upper', 'bb_middle', 'bb_lower']):
                        ax1.plot(recent_df['DATETIME'], recent_df['bb_upper'], 'r--', alpha=0.5, label='Upper BB')
                        ax1.plot(recent_df['DATETIME'], recent_df['bb_middle'], 'g--', alpha=0.5, label='Middle BB')
                        ax1.plot(recent_df['DATETIME'], recent_df['bb_lower'], 'r--', alpha=0.5, label='Lower BB')
                    
                    # Add moving averages
                    for ma_period, color, alpha in [(20, 'blue', 0.8), (50, 'green', 0.7), (200, 'red', 0.6)]:
                        if f'sma_{ma_period}' in recent_df.columns:
                            ax1.plot(recent_df['DATETIME'], recent_df[f'sma_{ma_period}'], 
                                    color=color, alpha=alpha, linewidth=1.5, label=f'{ma_period}-day MA')
                    
                    # Calculate potential LONG entry and stop levels based on ATR
                    if 'TR' in recent_df.columns and len(recent_df) > 0:
                        latest_price = recent_df['CLOSE'].iloc[-1]
                        latest_atr = recent_df['TR'].iloc[-1]
                        
                        # Add potential entry and stop-loss levels
                        entry = latest_price
                        stop_loss = entry - (2.5 * latest_atr)  # 2.5x ATR for stop loss
                        profit_target_1 = entry + (2 * latest_atr)  # 2x ATR for first target
                        profit_target_2 = entry + (5 * latest_atr)  # 5x ATR for second target
                        
                        # Draw horizontal lines for entry, stop and targets
                        ax1.axhline(y=entry, color='black', linestyle='--', alpha=0.6, 
                                  label=f'Entry: {entry:.2f}')
                        ax1.axhline(y=stop_loss, color='red', linestyle='--', alpha=0.6, 
                                  label=f'Stop: {stop_loss:.2f} (-{100*(entry-stop_loss)/entry:.1f}%)')
                        ax1.axhline(y=profit_target_1, color='green', linestyle='--', alpha=0.6,
                                  label=f'Target 1: {profit_target_1:.2f} (+{100*(profit_target_1-entry)/entry:.1f}%)')
                        ax1.axhline(y=profit_target_2, color='darkgreen', linestyle='--', alpha=0.6,
                                  label=f'Target 2: {profit_target_2:.2f} (+{100*(profit_target_2-entry)/entry:.1f}%)')
                    
                    # Mark potential entry zones (price bouncing off lower BB)
                    if 'bb_lower' in recent_df.columns:
                        for i in range(5, len(recent_df)):
                            # Check for price bouncing off lower BB
                            if (recent_df['CLOSE'].iloc[i-1] <= recent_df['bb_lower'].iloc[i-1] * 1.01 and 
                                recent_df['CLOSE'].iloc[i] > recent_df['bb_lower'].iloc[i] * 1.02 and
                                recent_df['CLOSE'].iloc[i] > recent_df['CLOSE'].iloc[i-1]):
                                
                                # Mark entry signal
                                ax1.scatter(recent_df['DATETIME'].iloc[i], recent_df['CLOSE'].iloc[i], 
                                           color='green', s=80, marker='^', label='_BB Bounce Signal')
                    
                    ax1.set_title('Price Chart with Moving Averages and Bollinger Bands')
                    ax1.legend(loc='upper left', fontsize=8)
                    ax1.grid(True, alpha=0.3)
                    
                    # 2. Volume with trend analysis
                    ax2 = plt.subplot2grid((4, 2), (1, 0), colspan=1, rowspan=1)
                    if 'VOL' in recent_df.columns:
                        # Calculate rolling average volume
                        recent_df['vol_ma'] = recent_df['VOL'].rolling(window=20).mean()
                        
                        # Plot volume bars (green for up days, red for down days)
                        colors = ['green' if recent_df['CLOSE'].iloc[i] >= recent_df['OPEN'].iloc[i] else 'red' 
                                 for i in range(len(recent_df))]
                        
                        ax2.bar(recent_df['DATETIME'], recent_df['VOL'], color=colors, alpha=0.6, label='Volume')
                        ax2.plot(recent_df['DATETIME'], recent_df['vol_ma'], color='blue', linewidth=1.5, label='20-day Avg Vol')
                        
                        # Mark volume spikes (2x average)
                        for i in range(20, len(recent_df)):
                            if recent_df['VOL'].iloc[i] > 2 * recent_df['vol_ma'].iloc[i]:
                                ax2.scatter(recent_df['DATETIME'].iloc[i], recent_df['VOL'].iloc[i], 
                                          color='purple', s=40, marker='*', label='_Volume Spike')
                        
                        ax2.set_title('Volume Analysis')
                        ax2.legend(fontsize=8)
                        ax2.grid(True, alpha=0.3)
                    
                    # 3. Momentum Score with trend
                    ax3 = plt.subplot2grid((4, 2), (1, 1), colspan=1, rowspan=1)
                    valid_idx = recent_df['momentum_score'].notna()
                    ax3.plot(recent_df.loc[valid_idx, 'DATETIME'], recent_df.loc[valid_idx, 'momentum_score'], 
                           color='blue', linewidth=2, label='Momentum Score')
                    
                    # Add reference lines
                    ax3.axhline(y=50, color='gray', linestyle='--', alpha=0.7)
                    ax3.axhline(y=70, color='green', linestyle='--', alpha=0.7, label='Strong Momentum')
                    ax3.axhline(y=30, color='red', linestyle='--', alpha=0.7, label='Weak Momentum')
                    
                    # Add momentum score trend (regression line)
                    if sum(valid_idx) > 5:
                        dates = recent_df.loc[valid_idx, 'DATETIME']
                        scores = recent_df.loc[valid_idx, 'momentum_score']
                        
                        # Get x values for trend line (days from start)
                        x = np.arange(len(scores))
                        
                        # Linear regression for trend line
                        slope, intercept, _, _, _ = stats.linregress(x, scores)
                        trend_line = intercept + slope * x
                        
                        # Plot trend line
                        ax3.plot(dates, trend_line, 'r--', linewidth=1.5, 
                               label=f'Trend: {slope:.2f}/day')
                        
                        # Add momentum change annotations
                        if 'momentum_score_5d_change' in row and not pd.isna(row['momentum_score_5d_change']):
                            change_5d = row['momentum_score_5d_change']
                            change_color = 'green' if change_5d > 0 else 'red'
                            ax3.text(0.05, 0.05, f'5-day Δ: {change_5d:.1f}', transform=ax3.transAxes, 
                                   color=change_color, fontweight='bold')
                    
                    ax3.set_title('Momentum Score Analysis')
                    ax3.set_ylim(0, 100)
                    ax3.legend(fontsize=8)
                    ax3.grid(True, alpha=0.3)
                    
                    # 4. ATR Analysis
                    ax4 = plt.subplot2grid((4, 2), (2, 0), colspan=1, rowspan=1)
                    if 'ATR_pct' in recent_df.columns:
                        ax4.plot(recent_df['DATETIME'], recent_df['ATR_pct'], 'r-', linewidth=2, label='ATR %')
                        ax4.plot(recent_df['DATETIME'], recent_df['ATR_pct'].rolling(window=20).mean(), 
                               'b--', linewidth=1.5, label='20-day Avg ATR')
                        
                        # Add ATR volatility reference lines
                        avg_atr = recent_df['ATR_pct'].mean()
                        ax4.axhline(y=avg_atr, color='gray', linestyle='--', 
                                  label=f'Avg: {avg_atr:.2f}%')
                        
                        ax4.set_title('ATR (Average True Range) Analysis')
                        ax4.set_ylabel('ATR %')
                        ax4.legend(fontsize=8)
                        ax4.grid(True, alpha=0.3)
                    
                    # 5. RSI Analysis
                    ax5 = plt.subplot2grid((4, 2), (2, 1), colspan=1, rowspan=1)
                    if 'rsi' in recent_df.columns:
                        ax5.plot(recent_df['DATETIME'], recent_df['rsi'], color='purple', 
                               linewidth=2, label='RSI(14)')
                        
                        # Add reference lines
                        ax5.axhline(y=70, color='red', linestyle='--', alpha=0.7, label='Overbought')
                        ax5.axhline(y=30, color='green', linestyle='--', alpha=0.7, label='Oversold')
                        ax5.axhline(y=50, color='gray', linestyle='-', alpha=0.3)
                        
                        # Mark potential entry points (RSI crossing above 30 from below)
                        for i in range(5, len(recent_df)):
                            if recent_df['rsi'].iloc[i-1] < 30 and recent_df['rsi'].iloc[i] > 30:
                                ax5.scatter(recent_df['DATETIME'].iloc[i], recent_df['rsi'].iloc[i], 
                                          color='green', s=60, marker='^', label='_RSI Buy Signal')
                        
                        # Mark potential exit points (RSI crossing above 70)
                        for i in range(5, len(recent_df)):
                            if recent_df['rsi'].iloc[i-1] < 70 and recent_df['rsi'].iloc[i] > 70:
                                ax5.scatter(recent_df['DATETIME'].iloc[i], recent_df['rsi'].iloc[i], 
                                          color='red', s=60, marker='v', label='_RSI Sell Signal')
                        
                        ax5.set_title('RSI (Relative Strength Index) Analysis')
                        ax5.set_ylim(0, 100)
                        ax5.legend(fontsize=8, loc='upper left')
                        ax5.grid(True, alpha=0.3)
                    
                    # 6. MACD Analysis
                    ax6 = plt.subplot2grid((4, 2), (3, 0), colspan=2, rowspan=1)
                    if all(col in recent_df.columns for col in ['macd', 'macd_signal', 'macd_hist']):
                        ax6.bar(recent_df['DATETIME'], recent_df['macd_hist'], 
                              color=['green' if x > 0 else 'red' for x in recent_df['macd_hist']], 
                              alpha=0.5, label='MACD Histogram')
                        ax6.plot(recent_df['DATETIME'], recent_df['macd'], color='blue', 
                               linewidth=1.5, label='MACD')
                        ax6.plot(recent_df['DATETIME'], recent_df['macd_signal'], color='red', 
                               linewidth=1.5, label='Signal')
                        ax6.axhline(y=0, color='black', linestyle='-', alpha=0.3)
                        
                        # Mark MACD crossovers (bullish: MACD crosses above signal)
                        for i in range(1, len(recent_df)):
                            if (recent_df['macd'].iloc[i-1] < recent_df['macd_signal'].iloc[i-1] and 
                                recent_df['macd'].iloc[i] > recent_df['macd_signal'].iloc[i]):
                                
                                ax6.scatter(recent_df['DATETIME'].iloc[i], recent_df['macd'].iloc[i], 
                                          color='green', s=60, marker='^', label='_MACD Buy Signal')
                        
                        # Mark MACD bearish crossovers
                        for i in range(1, len(recent_df)):
                            if (recent_df['macd'].iloc[i-1] > recent_df['macd_signal'].iloc[i-1] and 
                                recent_df['macd'].iloc[i] < recent_df['macd_signal'].iloc[i]):
                                
                                ax6.scatter(recent_df['DATETIME'].iloc[i], recent_df['macd'].iloc[i], 
                                          color='red', s=60, marker='v', label='_MACD Sell Signal')
                        
                        ax6.set_title('MACD (Moving Average Convergence Divergence) Analysis')
                        ax6.legend(fontsize=8)
                        ax6.grid(True, alpha=0.3)
                    
                    # Add reversal signals annotation
                    reversal_signals = []
                    for key in row.keys():
                        if key.startswith('reversal_signal_') and row[key]:
                            signal_name = key.replace('reversal_signal_', '').replace('_', ' ').title()
                            reversal_signals.append(signal_name)
                    
                    if reversal_signals:
                        signals_text = "Detected Reversal Signals:\n• " + "\n• ".join(reversal_signals)
                        plt.figtext(0.02, 0.02, signals_text, fontsize=10, 
                                  bbox=dict(facecolor='white', alpha=0.8, boxstyle='round'))
                    
                    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
                    plt.savefig(os.path.join(plots_dir, f"{symbol}_consolidated_analysis.png"), dpi=150)
                    plt.close()
                    
                except Exception as e:
                    print(f"Error plotting {symbol}: {e}")
        
        print(f"Generated consolidated charts for {min(len(top_candidates), top_n)} reversal candidates")
    
    def _generate_summary_comparison(self, top_candidates, plots_dir):
        """
        Generate a summary comparison chart of all top candidates.
        
        Args:
            top_candidates (DataFrame): DataFrame containing top reversal candidates
            plots_dir (str): Directory to save the output chart
        """
        if len(top_candidates) > 0:
            plt.figure(figsize=(12, 8))
            symbols = top_candidates['Symbol'].tolist()
            
            # Use long_tradability score if available, otherwise use reversal_score
            if 'long_tradability' in top_candidates.columns:
                scores = top_candidates['long_tradability'].tolist()
                title = 'Top LONG Tradability Candidates'
                xlabel = 'LONG Tradability Score'
            else:
                scores = top_candidates['reversal_score'].tolist()
                title = 'Top Reversal Candidates'
                xlabel = 'Reversal Score'
            
            # Create horizontal bar chart with color-coded bars
            bars = plt.barh(symbols, scores, color='steelblue')
            
            # Color code by reversal potential
            for i, bar in enumerate(bars):
                potential = top_candidates['reversal_potential'].iloc[i]
                if potential == 'Very Strong':
                    bar.set_color('darkgreen')
                elif potential == 'Strong':
                    bar.set_color('forestgreen')
                elif potential == 'Moderate':
                    bar.set_color('orange')
                else:
                    bar.set_color('gray')
                    
            # Add a legend for color coding
            from matplotlib.patches import Patch
            legend_elements = [
                Patch(facecolor='darkgreen', label='Very Strong'),
                Patch(facecolor='forestgreen', label='Strong'),
                Patch(facecolor='orange', label='Moderate'),
                Patch(facecolor='gray', label='Weak')
            ]
            plt.legend(handles=legend_elements, title='Reversal Potential', 
                      loc='lower right')
            
            # Add ATR annotations
            if 'avg_atr_pct' in top_candidates.columns:
                for i, (symbol, score) in enumerate(zip(symbols, scores)):
                    atr = top_candidates[top_candidates['Symbol'] == symbol]['avg_atr_pct'].values[0]
                    plt.text(score + 1, i, f"ATR: {atr:.1f}%", va='center')
            
            plt.xlabel(xlabel)
            plt.title(title)
            plt.xlim(0, 100)
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(os.path.join(plots_dir, "top_long_candidates_summary.png"))
            plt.close()
    
    def _generate_market_regime_chart(self, plots_dir):
        """
        Generate market regime analysis chart showing trend strength and volatility.
        
        Args:
            plots_dir (str): Directory to save the output chart
        """
        plt.figure(figsize=(14, 8))
        regimes = self.market_regimes.copy()
        
        # Define colors for regimes
        regime_colors = {
            'strong_uptrend': 'darkgreen',
            'uptrend': 'green',
            'neutral': 'gray',
            'downtrend': 'red',
            'strong_downtrend': 'darkred',
            'choppy': 'orange',
            'range_bound': 'blue'
        }
        
        # Plot trend percentage and moving averages
        ax1 = plt.subplot(2, 1, 1)
        ax1.plot(regimes['DATETIME'], regimes['trend_60d'], label='60-day Trend (%)', 
               color='blue', linewidth=2)
        
        if 'trend_20d' in regimes.columns:
            ax1.plot(regimes['DATETIME'], regimes['trend_20d'], label='20-day Trend (%)', 
                   color='green', linewidth=1.5, alpha=0.8)
        
        ax1.axhline(y=0, color='gray', linestyle='--')
        ax1.set_title('Market Regime Analysis: Trend Strength', fontsize=12)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot volatility and regimes
        ax2 = plt.subplot(2, 1, 2)
        if 'volatility_20d' in regimes.columns:
            ax2.plot(regimes['DATETIME'], regimes['volatility_20d'], color='red', 
                   label='20-day Volatility', alpha=0.7, linewidth=2)
        
        # Add a secondary y-axis for volume if available
        if 'volume_ratio' in regimes.columns:
            ax3 = ax2.twinx()
            ax3.plot(regimes['DATETIME'], regimes['volume_ratio'], color='purple', 
                   label='Volume Ratio', alpha=0.5, linewidth=1.5)
            ax3.set_ylabel('Volume Ratio')
            ax3.legend(loc='upper right')
        
        # Color background by regime
        if 'market_regime' in regimes.columns:
            # Create colored background segments for different regimes
            unique_regimes = regimes['market_regime'].unique()
            regime_labels = []
            
            # Process each regime transition
            current_regime = None
            start_idx = 0
            
            for i, regime in enumerate(regimes['market_regime']):
                if regime != current_regime:
                    if current_regime is not None:
                        # Color previous regime segment
                        ax2.axvspan(regimes['DATETIME'].iloc[start_idx], 
                                  regimes['DATETIME'].iloc[i-1], 
                                  alpha=0.2, 
                                  color=regime_colors.get(current_regime, 'gray'))
                        
                        if current_regime not in regime_labels:
                            regime_labels.append(current_regime)
                    
                    current_regime = regime
                    start_idx = i
            
            # Color the last regime segment
            if current_regime is not None:
                ax2.axvspan(regimes['DATETIME'].iloc[start_idx], 
                          regimes['DATETIME'].iloc[-1], 
                          alpha=0.2, 
                          color=regime_colors.get(current_regime, 'gray'))
                
                if current_regime not in regime_labels:
                    regime_labels.append(current_regime)
            
            # Create a custom legend for regimes
            from matplotlib.patches import Patch
            legend_elements = [Patch(facecolor=regime_colors.get(regime, 'gray'), 
                                   alpha=0.2, 
                                   label=regime.replace('_', ' ').title())
                             for regime in regime_labels]
            
            ax2.legend(handles=legend_elements, loc='upper left')
        
        ax2.set_title('Market Volatility and Regime Classification', fontsize=12)
        ax2.set_ylabel('Volatility')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, "market_regime_analysis.png"), dpi=150)
        plt.close()
    
    def run_analysis(self, min_reversal_score=30, min_atr_pct=1.0, max_atr_pct=None, top_n=10):
        """
        Run the complete analysis pipeline.
        
        Args:
            min_reversal_score (float): Minimum reversal score to consider (0-100)
            min_atr_pct (float): Minimum Average True Range percentage for volatility
            max_atr_pct (float, optional): Maximum ATR percentage to consider
            top_n (int): Number of top candidates to chart
            
        Returns:
            DataFrame: Filtered and sorted reversal candidates
        """
        print("Loading stock data...")
        self.load_stock_data()
        
        print("Finding reversal candidates...")
        candidates = self.find_reversal_candidates(
            min_reversal_score=min_reversal_score,
            min_atr_pct=min_atr_pct,
            max_atr_pct=max_atr_pct
        )
        
        if not candidates.empty:
            print(f"Found {len(candidates)} reversal candidates.")
            print("Generating charts for top candidates...")
            self.generate_consolidated_charts(top_n=top_n)
            
            # Create analysis summary
            self._generate_analysis_summary(candidates, top_n)
        else:
            print("No candidates found matching the criteria.")
        
        return candidates
    
    def _generate_analysis_summary(self, candidates, top_n):
        """
        Generate analysis summary file with key metrics.
        
        Args:
            candidates (DataFrame): Candidate stocks
            top_n (int): Number of top candidates to summarize
        """
        summary_file = os.path.join(self.output_dir, "analysis_summary.txt")
        with open(summary_file, "w") as f:
            f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Candidates: {len(candidates)}\n")
            f.write(f"Data Range: {self.start_date.strftime('%Y-%m-%d')} to present\n")
            
            # Add top candidates
            f.write(f"\nTop {min(top_n, len(candidates))} Candidates:\n")
            for i, (_, row) in enumerate(candidates.head(top_n).iterrows()):
                symbol = row['Symbol']
                score = row.get('long_tradability', row.get('reversal_score', 0))
                potential = row.get('reversal_potential', 'N/A')
                atr = row.get('avg_atr_pct', 0)
                f.write(f"{i+1}. {symbol}: Score {score:.1f}, Potential: {potential}, ATR: {atr:.2f}%\n")
        
        print(f"Analysis summary saved to {summary_file}")


def main():
    """
    Main function to run the momentum reversal tracker.
    
    Sets configuration parameters and executes the analysis pipeline.
    Provides a command-line interface with configurable parameters.
    """
    import argparse
    
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Momentum Reversal Tracker for Long Positions')
    parser.add_argument('--data_folder', type=str, default="Nasdaq/Stock-W1-TECH",
                        help='Directory containing stock data CSV files')
    parser.add_argument('--start_date', type=str, default="2020-01-01",
                        help='Start date for analysis in YYYY-MM-DD format')
    parser.add_argument('--output_dir', type=str, default="momentum_output",
                        help='Directory for storing output files and charts')
    parser.add_argument('--min_score', type=float, default=20,
                        help='Minimum reversal score threshold (0-100)')
    parser.add_argument('--min_atr', type=float, default=3.0,
                        help='Minimum volatility (ATR %%) for candidate stocks')
    parser.add_argument('--max_atr', type=float, default=30.0,
                        help='Maximum volatility (ATR %%) for candidate stocks')
    parser.add_argument('--top_n', type=int, default=15,
                        help='Number of top candidates to chart')
    
    args = parser.parse_args()
    
    print("Starting Momentum Reversal Tracker for LONG Positions...")
    print(f"Data folder: {args.data_folder}")
    print(f"Analysis start date: {args.start_date}")
    print(f"Output directory: {args.output_dir}")
    print(f"Score threshold: {args.min_score}")
    print(f"ATR range: {args.min_atr}% - {args.max_atr}%")
    
    # Initialize and run analysis
    tracker = MomentumReversalTracker(
        data_folder=args.data_folder,
        start_date=args.start_date,
        output_dir=args.output_dir
    )
    
    candidates = tracker.run_analysis(
        min_reversal_score=args.min_score,
        min_atr_pct=args.min_atr,
        max_atr_pct=args.max_atr,
        top_n=args.top_n
    )
    
    print("\nAnalysis complete. Results saved to output files.")


if __name__ == "__main__":
    main()
