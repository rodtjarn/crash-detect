#!/usr/bin/env python3
"""
Backtest Crash Detection System
Tests the trading alert system against 25 years of historical data
to see how many crashes were detected and potential returns
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from trading_alert_system import TradingAlertSystem


class CrashBacktester:
    """Backtest crash detection over historical data"""

    def __init__(self, config_file='config.json'):
        """Initialize backtester"""
        self.system = TradingAlertSystem(config_file)
        self.signals = []

    def fetch_historical_data(self, years=25):
        """Fetch historical data for backtesting"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365 + 180)

        print(f"Fetching {years} years of historical data...")
        print(f"From {start_date.date()} to {end_date.date()}")

        # Fetch S&P 500 data
        index_data = yf.download(
            '^GSPC',
            start=start_date,
            end=end_date,
            progress=False
        )

        # Fetch VIX data
        vix_data = yf.download(
            '^VIX',
            start=start_date,
            end=end_date,
            progress=False
        )

        if len(index_data) < 100:
            raise ValueError(f"Insufficient data: {len(index_data)} days")

        # Combine data
        data = pd.DataFrame(index=index_data.index)
        data['close'] = index_data['Close'].values
        data['vix'] = vix_data['Close'].values
        data['returns'] = data['close'].pct_change()
        data['put_call_ratio'] = self.system.calculate_put_call_proxy(data)

        print(f"✓ Fetched {len(data)} days of data\n")
        return data.dropna()

    def run_backtest(self, data, lookback_window=90):
        """
        Run backtest on historical data

        For each day with sufficient history, check if signal triggers
        """
        print("Running backtest...")
        print("="*70)

        signals = []
        min_data_points = self.system.config['data']['min_data_points']

        # Start from first date with enough history
        start_idx = lookback_window

        for i in range(start_idx, len(data)):
            # Get data window for this date
            current_date = data.index[i]
            window_start = i - lookback_window
            window_data = data.iloc[window_start:i+1].copy()

            if len(window_data) < min_data_points:
                continue

            # Calculate indicators for this date
            try:
                state = self.system.calculate_current_state(window_data)
                signal_type, conditions = self.system.check_signal(state)

                if signal_type:
                    # Signal triggered!
                    signal_info = {
                        'date': current_date,
                        'type': signal_type,
                        'price': state['price'],
                        'fractal': state['fractal_dimension'],
                        'vix': state['vix'],
                        'put_call': state['put_call_ratio'],
                        'markov': state['markov_state']
                    }

                    # Find subsequent low (look forward 60 days)
                    future_window = min(60, len(data) - i - 1)
                    if future_window > 0:
                        future_prices = data['close'].iloc[i:i+future_window+1]
                        low_idx = future_prices.idxmin()
                        low_price = future_prices.min()

                        signal_info['low_date'] = low_idx
                        signal_info['low_price'] = low_price
                        signal_info['drop_pct'] = (
                            (low_price - state['price']) /
                            state['price'] * 100
                        )
                        signal_info['days_to_low'] = (
                            (low_idx - current_date).days
                        )

                    signals.append(signal_info)

                    # Print signal as it's found
                    drop = signal_info.get('drop_pct', 0)
                    days = signal_info.get('days_to_low', 0)
                    print(
                        f"Signal #{len(signals)}: "
                        f"{current_date.date()} | "
                        f"{signal_type} | "
                        f"Price: ${state['price']:.2f} | "
                        f"Drop: {drop:.2f}% in {days} days"
                    )

            except Exception as e:
                # Skip dates with calculation errors
                continue

        self.signals = signals
        return signals

    def analyze_results(self, signals):
        """Analyze backtest results"""
        print("\n" + "="*70)
        print("BACKTEST RESULTS")
        print("="*70)

        if not signals:
            print("\n❌ NO SIGNALS DETECTED in the last 25 years")
            print("\nPossible reasons:")
            print("  - Thresholds too strict for current configuration")
            print("  - No crashes severe enough to trigger all 4 indicators")
            print(
                f"  - Current config: Fractal < "
                f"{self.system.config['trading']['thresholds']['fractal_max']}, "
                f"VIX > "
                f"{self.system.config['trading']['thresholds']['vix_min']}, "
                f"P/C > "
                f"{self.system.config['trading']['thresholds']['put_call_min']}"
            )
            return

        print(f"\n✓ Detected {len(signals)} signals\n")

        # Detailed signal information
        for i, sig in enumerate(signals, 1):
            print(f"\nSignal #{i}: {sig['type']}")
            print(f"  Date: {sig['date'].date()}")
            print(f"  Entry Price: ${sig['price']:.2f}")

            if 'low_price' in sig:
                print(f"  Subsequent Low: ${sig['low_price']:.2f}")
                print(
                    f"  Drop: {sig['drop_pct']:.2f}% "
                    f"({sig['days_to_low']} days)"
                )
            else:
                print("  No subsequent low found (near end of data)")

            print(f"\n  Indicators:")
            fractal = sig['fractal']
            print(f"    Fractal: {fractal:.3f}" if fractal else "    Fractal: N/A")
            print(f"    VIX: {sig['vix']:.2f}")
            print(f"    Put/Call: {sig['put_call']:.2f}")
            print(f"    Markov: {sig['markov']}")

        # Summary statistics
        print("\n" + "="*70)
        print("SUMMARY STATISTICS")
        print("="*70)

        drops = [s['drop_pct'] for s in signals if 'drop_pct' in s]

        if drops:
            print(f"\nTotal signals: {len(signals)}")
            print(f"Signals with data: {len(drops)}")
            print(f"\nAverage drop: {np.mean(drops):.2f}%")
            print(f"Median drop: {np.median(drops):.2f}%")
            print(f"Max drop: {np.min(drops):.2f}%")
            print(f"Min drop: {np.max(drops):.2f}%")

            avg_days = np.mean(
                [s['days_to_low'] for s in signals if 'days_to_low' in s]
            )
            print(f"\nAverage days to low: {avg_days:.1f}")

            # Calculate returns if trading 3x inverse
            # For SPXS (3x inverse): if SPY drops 10%, SPXS gains ~30%
            inverse_returns = [-d * 3 for d in drops]
            print(f"\n3x INVERSE ETF RETURNS (if held to low):")
            print(f"  Average return: {np.mean(inverse_returns):.2f}%")
            print(f"  Best trade: {np.max(inverse_returns):.2f}%")
            print(f"  Worst trade: {np.min(inverse_returns):.2f}%")

            # With stop loss
            stopped_returns = []
            for d in drops:
                if d > -1.5:  # Hit stop loss
                    stopped_returns.append(-1.5 * 3)  # 3x leverage
                else:
                    stopped_returns.append(-d * 3)

            print(f"\n3x INVERSE ETF WITH 1.5% STOP LOSS:")
            print(f"  Average return: {np.mean(stopped_returns):.2f}%")
            print(f"  Win rate: {sum(1 for r in stopped_returns if r > 0) / len(stopped_returns) * 100:.1f}%")

        print("\n" + "="*70)


def main():
    """Main entry point"""
    import sys

    # Get years from command line argument, default to 5
    years = 25
    if len(sys.argv) > 1:
        try:
            years = int(sys.argv[1])
        except ValueError:
            print("Usage: python backtest_crash_detection.py [years]")
            sys.exit(1)

    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║          CRASH DETECTION BACKTEST - {years} YEAR ANALYSIS{' ' * (26 - len(str(years)))}║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
""")

    # Create backtester
    backtester = CrashBacktester('config.json')

    # Fetch data
    data = backtester.fetch_historical_data(years=years)

    # Run backtest
    signals = backtester.run_backtest(data)

    # Analyze results
    backtester.analyze_results(signals)

    print("\n")


if __name__ == "__main__":
    main()
