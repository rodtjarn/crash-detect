#!/usr/bin/env python3
"""
Portfolio Backtest with Exit Rules
$100,000 starting capital, 3% positions, 20% gain target, 5% stop loss
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from trading_alert_system import TradingAlertSystem


class PortfolioBacktester:
    """Backtest with portfolio tracking and exit rules"""

    def __init__(self, config_file='config.json'):
        """Initialize backtester"""
        self.system = TradingAlertSystem(config_file)
        self.trades = []
        self.portfolio_history = []

    def fetch_historical_data(self, years=20):
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

        # Fetch 3x inverse ETF (SPXS) data
        spxs_data = yf.download(
            'SPXS',
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

        # Add SPXS data
        if len(spxs_data) > 0:
            spxs_df = pd.DataFrame(index=spxs_data.index)
            spxs_df['spxs_close'] = spxs_data['Close'].values
            data = data.join(spxs_df, how='left')
        else:
            data['spxs_close'] = np.nan

        print(f"✓ Fetched {len(data)} days of data\n")
        return data.dropna(subset=['close', 'vix'])

    def simulate_3x_inverse(self, spy_return):
        """Simulate 3x inverse ETF return"""
        return -3 * spy_return

    def run_backtest(self, data, lookback_window=90):
        """
        Run backtest with exit rules

        Strategy:
        - Entry: Sell 3% of portfolio, buy SPXS
        - Exit: Whichever comes first:
          * 8 days elapsed
          * SPXS gains 20%
          * SPXS loses 5%
        """
        print("Running portfolio backtest with exit rules...")
        print("="*70)

        config = self.system.config['trading']
        initial_capital = config.get('initial_capital', 100000)
        position_pct = config['position_size'] / 100  # 3% = 0.03
        hold_days = config['hold_days']
        gain_target = config.get('gain_target', 20.0) / 100  # 20% = 0.20
        stop_loss = config.get('stop_loss', 5.0) / 100  # 5% = 0.05
        min_data_points = self.system.config['data']['min_data_points']

        print(f"Initial Capital: ${initial_capital:,.2f}")
        print(f"Position Size: {position_pct*100:.1f}%")
        print(f"Gain Target: {gain_target*100:.1f}%")
        print(f"Stop Loss: {stop_loss*100:.1f}%")
        print(f"Max Hold: {hold_days} days\n")

        portfolio_value = initial_capital
        cash = initial_capital
        trades = []
        start_idx = lookback_window
        last_trade_exit = None

        for i in range(start_idx, len(data)):
            current_date = data.index[i]

            # Skip if we're still in a trade
            if last_trade_exit and current_date <= last_trade_exit:
                continue

            # Get data window for this date
            window_start = i - lookback_window
            window_data = data.iloc[window_start:i+1].copy()

            if len(window_data) < min_data_points:
                continue

            # Calculate indicators for this date
            try:
                state = self.system.calculate_current_state(window_data)
                signal_type, conditions = self.system.check_signal(state)

                if signal_type == 'SHORT':
                    # Signal triggered! Execute trade
                    entry_date = current_date
                    entry_idx = i
                    entry_price_spy = state['price']

                    # Calculate position sizes
                    position_value = portfolio_value * position_pct
                    long_value = portfolio_value - position_value

                    # SPXS entry
                    if not pd.isna(data['spxs_close'].iloc[i]):
                        entry_price_spxs = data['spxs_close'].iloc[i]
                        use_real_spxs = True
                    else:
                        entry_price_spxs = 100  # Simulated starting price
                        use_real_spxs = False

                    # Monitor for exit daily
                    exit_date = None
                    exit_idx = None
                    exit_price_spy = None
                    exit_price_spxs = None
                    exit_reason = None
                    days_held = 0

                    for j in range(i + 1, min(i + hold_days + 1, len(data))):
                        check_date = data.index[j]
                        days_held = j - i

                        # Get current prices
                        current_spy = data['close'].iloc[j]

                        if use_real_spxs and not pd.isna(
                            data['spxs_close'].iloc[j]
                        ):
                            current_spxs = data['spxs_close'].iloc[j]
                        else:
                            # Simulate SPXS price
                            spy_return = (
                                (current_spy - entry_price_spy) /
                                entry_price_spy
                            )
                            simulated_return = self.simulate_3x_inverse(
                                spy_return
                            )
                            current_spxs = entry_price_spxs * (
                                1 + simulated_return
                            )

                        # Calculate SPXS return
                        spxs_return = (
                            (current_spxs - entry_price_spxs) /
                            entry_price_spxs
                        )

                        # Check exit conditions
                        if spxs_return >= gain_target:
                            exit_date = check_date
                            exit_idx = j
                            exit_price_spy = current_spy
                            exit_price_spxs = current_spxs
                            exit_reason = f"GAIN TARGET ({spxs_return*100:.1f}%)"
                            break
                        elif spxs_return <= -stop_loss:
                            exit_date = check_date
                            exit_idx = j
                            exit_price_spy = current_spy
                            exit_price_spxs = current_spxs
                            exit_reason = f"STOP LOSS ({spxs_return*100:.1f}%)"
                            break
                        elif days_held >= hold_days:
                            exit_date = check_date
                            exit_idx = j
                            exit_price_spy = current_spy
                            exit_price_spxs = current_spxs
                            exit_reason = f"TIME EXIT ({days_held}d)"
                            break

                    # If no exit found, use last available data
                    if exit_date is None:
                        exit_idx = min(i + hold_days, len(data) - 1)
                        exit_date = data.index[exit_idx]
                        exit_price_spy = data['close'].iloc[exit_idx]
                        days_held = exit_idx - i

                        if use_real_spxs and not pd.isna(
                            data['spxs_close'].iloc[exit_idx]
                        ):
                            exit_price_spxs = data['spxs_close'].iloc[exit_idx]
                        else:
                            spy_return = (
                                (exit_price_spy - entry_price_spy) /
                                entry_price_spy
                            )
                            exit_price_spxs = entry_price_spxs * (
                                1 + self.simulate_3x_inverse(spy_return)
                            )
                        exit_reason = f"END OF DATA ({days_held}d)"

                    # Calculate returns
                    spy_return = (
                        (exit_price_spy - entry_price_spy) / entry_price_spy
                    )
                    spxs_return = (
                        (exit_price_spxs - entry_price_spxs) /
                        entry_price_spxs
                    )

                    # Update portfolio
                    long_portion = long_value * (1 + spy_return)
                    short_portion = position_value * (1 + spxs_return)
                    new_portfolio_value = long_portion + short_portion

                    portfolio_return = (
                        (new_portfolio_value - portfolio_value) /
                        portfolio_value
                    )

                    trade_info = {
                        'entry_date': entry_date,
                        'exit_date': exit_date,
                        'days_held': days_held,
                        'exit_reason': exit_reason,
                        'entry_price_spy': entry_price_spy,
                        'exit_price_spy': exit_price_spy,
                        'entry_price_spxs': entry_price_spxs,
                        'exit_price_spxs': exit_price_spxs,
                        'spy_return': spy_return * 100,
                        'spxs_return': spxs_return * 100,
                        'portfolio_before': portfolio_value,
                        'portfolio_after': new_portfolio_value,
                        'portfolio_return': portfolio_return * 100,
                        'position_value': position_value,
                        'fractal': state['fractal_dimension'],
                        'vix': state['vix'],
                        'put_call': state['put_call_ratio']
                    }

                    trades.append(trade_info)
                    portfolio_value = new_portfolio_value
                    last_trade_exit = exit_date

                    # Print trade
                    print(
                        f"Trade #{len(trades)}: "
                        f"{entry_date.date()} -> {exit_date.date()} "
                        f"({days_held}d) | "
                        f"SPXS: {spxs_return*100:+.1f}% | "
                        f"Portfolio: ${portfolio_value:,.2f} "
                        f"({portfolio_return*100:+.2f}%) | "
                        f"{exit_reason}"
                    )

            except Exception as e:
                continue

        self.trades = trades
        return trades, portfolio_value

    def analyze_results(self, trades, final_portfolio):
        """Analyze backtest results"""
        print("\n" + "="*70)
        print("PORTFOLIO BACKTEST RESULTS")
        print("="*70)

        config = self.system.config['trading']
        initial_capital = config.get('initial_capital', 100000)

        if not trades:
            print("\n❌ NO TRADES EXECUTED")
            return

        print(f"\nInitial Capital: ${initial_capital:,.2f}")
        print(f"Final Portfolio: ${final_portfolio:,.2f}")
        total_return = (final_portfolio - initial_capital) / initial_capital
        print(f"Total Return: {total_return*100:+.2f}%")
        print(f"\nTotal Trades: {len(trades)}")

        # Exit reason breakdown
        print("\nEXIT REASONS:")
        exit_reasons = {}
        for trade in trades:
            reason = trade['exit_reason'].split('(')[0].strip()
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        for reason, count in sorted(
            exit_reasons.items(), key=lambda x: x[1], reverse=True
        ):
            pct = count / len(trades) * 100
            print(f"  {reason}: {count} ({pct:.1f}%)")

        # Trade statistics
        portfolio_returns = [t['portfolio_return'] for t in trades]
        spxs_returns = [t['spxs_return'] for t in trades]

        print(f"\nPORTFOLIO PERFORMANCE:")
        print(f"  Average return per trade: {np.mean(portfolio_returns):.2f}%")
        print(f"  Median return: {np.median(portfolio_returns):.2f}%")
        print(f"  Best trade: {np.max(portfolio_returns):.2f}%")
        print(f"  Worst trade: {np.min(portfolio_returns):.2f}%")
        win_rate = (
            sum(1 for r in portfolio_returns if r > 0) / len(portfolio_returns)
        )
        print(f"  Win rate: {win_rate*100:.1f}%")

        print(f"\nSPXS POSITION PERFORMANCE:")
        print(f"  Average SPXS return: {np.mean(spxs_returns):.2f}%")
        print(f"  Best SPXS trade: {np.max(spxs_returns):.2f}%")
        print(f"  Worst SPXS trade: {np.min(spxs_returns):.2f}%")

        # Annual metrics
        if len(trades) > 0:
            years = (
                (trades[-1]['exit_date'] - trades[0]['entry_date']).days /
                365.25
            )
            if years > 0:
                trades_per_year = len(trades) / years
                annual_return = (
                    (final_portfolio / initial_capital) ** (1/years) - 1
                )
                print(f"\nANNUAL METRICS:")
                print(f"  Trades per year: {trades_per_year:.1f}")
                print(f"  Annualized return: {annual_return*100:.2f}%")

        print("\n" + "="*70)

        return {
            'initial_capital': initial_capital,
            'final_portfolio': final_portfolio,
            'total_return': total_return * 100,
            'trades': len(trades),
            'win_rate': win_rate * 100,
            'avg_return': np.mean(portfolio_returns),
            'best_trade': np.max(portfolio_returns),
            'worst_trade': np.min(portfolio_returns)
        }


def main():
    """Main entry point"""
    import sys

    years = 20
    if len(sys.argv) > 1:
        try:
            years = int(sys.argv[1])
        except ValueError:
            print("Usage: python backtest_portfolio.py [years]")
            sys.exit(1)

    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║          PORTFOLIO BACKTEST - {years} YEARS{' ' * (32 - len(str(years)))}║
║                                                                   ║
║  Starting Capital: $100,000                                       ║
║  Position Size: 3%                                                ║
║  Gain Target: 20% | Stop Loss: 5% | Max Hold: 8 days             ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
""")

    # Create backtester
    backtester = PortfolioBacktester('config.json')

    # Fetch data
    data = backtester.fetch_historical_data(years=years)

    # Run backtest
    trades, final_portfolio = backtester.run_backtest(data)

    # Analyze results
    summary = backtester.analyze_results(trades, final_portfolio)

    # Save detailed results to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f'backtest_results_{timestamp}.txt'

    with open(log_file, 'w') as f:
        f.write("="*70 + "\n")
        f.write(f"PORTFOLIO BACKTEST RESULTS - {years} YEARS\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*70 + "\n\n")

        f.write("CONFIGURATION:\n")
        f.write(f"  Initial Capital: ${summary['initial_capital']:,.2f}\n")
        f.write("  Position Size: 3%\n")
        f.write("  Gain Target: 20%\n")
        f.write("  Stop Loss: 5%\n")
        f.write("  Max Hold: 8 days\n\n")

        f.write("SUMMARY:\n")
        f.write(f"  Final Portfolio: ${summary['final_portfolio']:,.2f}\n")
        f.write(f"  Total Return: {summary['total_return']:+.2f}%\n")
        f.write(f"  Total Trades: {summary['trades']}\n")
        f.write(f"  Win Rate: {summary['win_rate']:.1f}%\n")
        f.write(
            f"  Average Return per Trade: {summary['avg_return']:.2f}%\n"
        )
        f.write(f"  Best Trade: {summary['best_trade']:.2f}%\n")
        f.write(f"  Worst Trade: {summary['worst_trade']:.2f}%\n\n")

        f.write("="*70 + "\n")
        f.write("DETAILED TRADE LOG\n")
        f.write("="*70 + "\n\n")

        for i, trade in enumerate(trades, 1):
            f.write(f"Trade #{i}:\n")
            f.write(f"  Entry Date: {trade['entry_date'].date()}\n")
            f.write(f"  Exit Date: {trade['exit_date'].date()}\n")
            f.write(f"  Days Held: {trade['days_held']}\n")
            f.write(f"  Exit Reason: {trade['exit_reason']}\n")
            f.write(
                f"  SPY: ${trade['entry_price_spy']:.2f} -> "
                f"${trade['exit_price_spy']:.2f} "
                f"({trade['spy_return']:+.2f}%)\n"
            )
            f.write(
                f"  SPXS: ${trade['entry_price_spxs']:.2f} -> "
                f"${trade['exit_price_spxs']:.2f} "
                f"({trade['spxs_return']:+.2f}%)\n"
            )
            f.write(
                f"  Portfolio: ${trade['portfolio_before']:,.2f} -> "
                f"${trade['portfolio_after']:,.2f} "
                f"({trade['portfolio_return']:+.2f}%)\n"
            )
            f.write(
                f"  Indicators: Fractal={trade['fractal']:.3f}, "
                f"VIX={trade['vix']:.1f}, P/C={trade['put_call']:.2f}\n"
            )
            f.write("\n")

    print(f"\n✓ Detailed results saved to: {log_file}")
    print("\n")


if __name__ == "__main__":
    main()
