#!/usr/bin/env python3
"""
Backtest ML Crash Detection Strategy
Simulates buying SPY when model predicts opportunity, holding until profit target or time limit
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ml_crash_detector import MLCrashDetector
import warnings
warnings.filterwarnings('ignore')


def backtest_ml_strategy(
    initial_capital=100000,
    position_size_pct=0.10,  # 10% of portfolio per trade
    profit_target=0.15,       # 15% profit target
    stop_loss=0.05,           # 5% stop loss
    max_hold_days=252,        # Max 1 year hold
    probability_threshold=0.5 # Min probability to trigger buy
):
    """
    Backtest the ML strategy with realistic trading rules
    """

    print(f"{'='*80}")
    print("ML CRASH DETECTION STRATEGY BACKTEST")
    print(f"{'='*80}")

    print(f"\nStrategy Parameters:")
    print(f"  Initial Capital: ${initial_capital:,}")
    print(f"  Position Size: {position_size_pct*100:.0f}% per trade")
    print(f"  Profit Target: {profit_target*100:.0f}%")
    print(f"  Stop Loss: {stop_loss*100:.0f}%")
    print(f"  Max Hold: {max_hold_days} days")
    print(f"  Probability Threshold: {probability_threshold*100:.0f}%")

    # Load trained model
    detector = MLCrashDetector()
    detector.load_model('ml_crash_model.pkl')

    # Fetch historical data
    print(f"\nFetching historical data for backtest...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=25 * 365)

    data = yf.download('SPY', start=start_date, end=end_date, progress=False)

    spy_data = pd.DataFrame()
    spy_data['close'] = data['Close']
    spy_data['high'] = data['High']
    spy_data['low'] = data['Low']
    spy_data['volume'] = data['Volume']

    # Fetch VIX
    vix_data = yf.download('^VIX', start=start_date, end=end_date, progress=False)
    spy_data['vix'] = vix_data['Close']

    spy_data = spy_data.dropna()

    print(f"✓ Loaded {len(spy_data)} days")
    print(f"  Period: {spy_data.index[0].date()} to {spy_data.index[-1].date()}")

    # Calculate features
    print(f"\nCalculating features for backtest...")
    spy_data = detector.calculate_technical_indicators(spy_data)
    spy_data = spy_data.dropna(subset=detector.feature_names)

    # Run backtest
    print(f"\nRunning backtest...")
    print(f"{'='*80}\n")

    cash = initial_capital
    portfolio_value = initial_capital
    shares_held = 0
    position_entry_price = 0
    position_entry_date = None
    trades = []

    in_position = False

    for i in range(len(spy_data)):
        current_date = spy_data.index[i]
        current_price = spy_data['close'].iloc[i]

        # Update portfolio value
        if in_position:
            portfolio_value = cash + (shares_held * current_price)

            # Check exit conditions
            days_held = (current_date - position_entry_date).days
            position_return = (current_price - position_entry_price) / position_entry_price

            # Exit on profit target
            if position_return >= profit_target:
                # Sell
                cash += shares_held * current_price
                portfolio_value = cash

                trades.append({
                    'entry_date': position_entry_date,
                    'exit_date': current_date,
                    'entry_price': position_entry_price,
                    'exit_price': current_price,
                    'return': position_return,
                    'days_held': days_held,
                    'exit_reason': 'Profit Target'
                })

                shares_held = 0
                in_position = False

            # Exit on stop loss
            elif position_return <= -stop_loss:
                # Sell
                cash += shares_held * current_price
                portfolio_value = cash

                trades.append({
                    'entry_date': position_entry_date,
                    'exit_date': current_date,
                    'entry_price': position_entry_price,
                    'exit_price': current_price,
                    'return': position_return,
                    'days_held': days_held,
                    'exit_reason': 'Stop Loss'
                })

                shares_held = 0
                in_position = False

            # Exit on max hold
            elif days_held >= max_hold_days:
                # Sell
                cash += shares_held * current_price
                portfolio_value = cash

                trades.append({
                    'entry_date': position_entry_date,
                    'exit_date': current_date,
                    'entry_price': position_entry_price,
                    'exit_price': current_price,
                    'return': position_return,
                    'days_held': days_held,
                    'exit_reason': 'Max Hold'
                })

                shares_held = 0
                in_position = False

        # Check for buy signal (only if not in position)
        if not in_position and i >= 200:  # Need historical data for features
            # Get features for current date
            features = spy_data.iloc[i][detector.feature_names].values.reshape(1, -1)

            # Predict
            probability = detector.model.predict_proba(features)[0, 1]

            # Buy if probability exceeds threshold
            if probability >= probability_threshold:
                # Calculate position size
                position_value = portfolio_value * position_size_pct
                shares_to_buy = position_value / current_price

                # Execute buy
                shares_held = shares_to_buy
                cash -= shares_to_buy * current_price
                position_entry_price = current_price
                position_entry_date = current_date
                in_position = True

    # Close any remaining position at end
    if in_position:
        final_price = spy_data['close'].iloc[-1]
        cash += shares_held * final_price
        portfolio_value = cash

        position_return = (final_price - position_entry_price) / position_entry_price
        days_held = (spy_data.index[-1] - position_entry_date).days

        trades.append({
            'entry_date': position_entry_date,
            'exit_date': spy_data.index[-1],
            'entry_price': position_entry_price,
            'exit_price': final_price,
            'return': position_return,
            'days_held': days_held,
            'exit_reason': 'End of Backtest'
        })

    # Calculate metrics
    print(f"{'='*80}")
    print("BACKTEST RESULTS")
    print(f"{'='*80}\n")

    total_return = (portfolio_value - initial_capital) / initial_capital
    years = (spy_data.index[-1] - spy_data.index[0]).days / 365.25
    annualized_return = (pow(portfolio_value / initial_capital, 1/years) - 1)

    # Buy and hold comparison
    initial_spy_price = spy_data['close'].iloc[200]  # Start when backtest starts
    final_spy_price = spy_data['close'].iloc[-1]
    buy_hold_return = (final_spy_price - initial_spy_price) / initial_spy_price
    buy_hold_annualized = (pow(1 + buy_hold_return, 1/years) - 1)

    print(f"Portfolio Performance:")
    print(f"  Initial Capital:     ${initial_capital:,.2f}")
    print(f"  Final Value:         ${portfolio_value:,.2f}")
    print(f"  Total Return:        {total_return*100:+.2f}%")
    print(f"  Annualized Return:   {annualized_return*100:+.2f}%")
    print(f"  Backtest Period:     {years:.1f} years")

    print(f"\nBuy & Hold SPY:")
    print(f"  Total Return:        {buy_hold_return*100:+.2f}%")
    print(f"  Annualized Return:   {buy_hold_annualized*100:+.2f}%")

    print(f"\nOutperformance:")
    print(f"  vs Buy & Hold:       {(total_return - buy_hold_return)*100:+.2f}%")
    print(f"  Annualized:          {(annualized_return - buy_hold_annualized)*100:+.2f}%")

    # Trade statistics
    print(f"\n{'='*80}")
    print("TRADE STATISTICS")
    print(f"{'='*80}\n")

    if len(trades) > 0:
        winning_trades = [t for t in trades if t['return'] > 0]
        losing_trades = [t for t in trades if t['return'] <= 0]

        print(f"Total Trades:        {len(trades)}")
        print(f"Winning Trades:      {len(winning_trades)} ({len(winning_trades)/len(trades)*100:.1f}%)")
        print(f"Losing Trades:       {len(losing_trades)} ({len(losing_trades)/len(trades)*100:.1f}%)")

        avg_return = np.mean([t['return'] for t in trades])
        avg_win = np.mean([t['return'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['return'] for t in losing_trades]) if losing_trades else 0

        print(f"\nAverage Returns:")
        print(f"  All Trades:        {avg_return*100:+.2f}%")
        print(f"  Winning Trades:    {avg_win*100:+.2f}%")
        print(f"  Losing Trades:     {avg_loss*100:+.2f}%")

        best_trade = max(trades, key=lambda x: x['return'])
        worst_trade = min(trades, key=lambda x: x['return'])

        print(f"\nBest Trade:          {best_trade['return']*100:+.2f}% ({best_trade['entry_date'].date()})")
        print(f"Worst Trade:         {worst_trade['return']*100:+.2f}% ({worst_trade['entry_date'].date()})")

        avg_hold = np.mean([t['days_held'] for t in trades])
        print(f"\nAverage Hold Time:   {avg_hold:.0f} days")

        # Exit reasons
        exit_reasons = {}
        for trade in trades:
            reason = trade['exit_reason']
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        print(f"\nExit Reasons:")
        for reason, count in exit_reasons.items():
            print(f"  {reason:<20} {count:3d} ({count/len(trades)*100:.1f}%)")

        # Detailed trades
        print(f"\n{'='*80}")
        print("DETAILED TRADE LOG")
        print(f"{'='*80}\n")

        for i, trade in enumerate(trades, 1):
            print(f"Trade #{i}: {trade['entry_date'].date()} → {trade['exit_date'].date()}")
            print(f"  Entry: ${trade['entry_price']:.2f}, Exit: ${trade['exit_price']:.2f}")
            print(f"  Return: {trade['return']*100:+.2f}%, Hold: {trade['days_held']} days")
            print(f"  Exit: {trade['exit_reason']}")
            print()

    else:
        print("No trades executed during backtest period")

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'ml_backtest_{timestamp}.txt'

    with open(filename, 'w') as f:
        f.write("ML CRASH DETECTION BACKTEST RESULTS\n")
        f.write("="*80 + "\n\n")
        f.write(f"Final Portfolio Value: ${portfolio_value:,.2f}\n")
        f.write(f"Total Return: {total_return*100:+.2f}%\n")
        f.write(f"Annualized Return: {annualized_return*100:+.2f}%\n")
        f.write(f"Buy & Hold Return: {buy_hold_return*100:+.2f}%\n")
        f.write(f"Outperformance: {(total_return - buy_hold_return)*100:+.2f}%\n\n")

        if trades:
            f.write(f"Total Trades: {len(trades)}\n")
            f.write(f"Win Rate: {len(winning_trades)/len(trades)*100:.1f}%\n")
            f.write(f"Average Return: {avg_return*100:+.2f}%\n\n")

            f.write("TRADE DETAILS:\n")
            f.write("="*80 + "\n")
            for trade in trades:
                f.write(f"\n{trade['entry_date'].date()} → {trade['exit_date'].date()}\n")
                f.write(f"  Return: {trade['return']*100:+.2f}%, Days: {trade['days_held']}\n")
                f.write(f"  Exit: {trade['exit_reason']}\n")

    print(f"\n✓ Results saved to {filename}\n")


if __name__ == '__main__':
    backtest_ml_strategy()
