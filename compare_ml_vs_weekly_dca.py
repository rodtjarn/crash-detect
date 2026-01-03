#!/usr/bin/env python3
"""
Comprehensive Backtest: ML Strategy vs Weekly DCA
==================================================
Compares ML-driven buy-and-hold against weekly dollar cost averaging
with detailed period-by-period performance reporting.

Tests multiple historical periods to validate strategy consistency.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ml_crash_detector import MLCrashDetector
import warnings
warnings.filterwarnings('ignore')


def calculate_investment_amount(probability, drawdown, available_cash,
                                 min_investment=5000, max_pct=0.20):
    """Calculate optimal investment amount for ML strategy"""
    if probability < 0.5:
        return 0

    prob_factor = (probability - 0.5) * 2
    base_pct = 0.05 + (prob_factor * 0.15)

    drawdown_magnitude = abs(drawdown)
    drawdown_multiplier = 1 + (drawdown_magnitude - 0.05) / 0.10
    drawdown_multiplier = np.clip(drawdown_multiplier, 1.0, 3.0)

    investment_pct = min(base_pct * drawdown_multiplier, max_pct)
    investment = available_cash * investment_pct

    if investment < min_investment and available_cash >= min_investment:
        investment = min_investment

    if available_cash < min_investment:
        investment = 0

    return investment


def run_ml_strategy(data, detector, initial_capital, cooldown_days=5):
    """Run ML buy-and-hold strategy"""

    # Calculate features
    data_with_features = detector.calculate_technical_indicators(data.copy())
    data_with_features = data_with_features.dropna(subset=detector.feature_names)

    cash = initial_capital
    shares = 0
    purchases = []
    last_purchase_date = None

    for i in range(len(data_with_features)):
        current_date = data_with_features.index[i]
        current_price = data_with_features['close'].iloc[i]

        # Check cooldown
        if last_purchase_date is not None:
            days_since = (current_date - last_purchase_date).days
            if days_since < cooldown_days:
                continue

        # Get ML prediction
        features = data_with_features.iloc[i][detector.feature_names].values.reshape(1, -1)
        probability = detector.model.predict_proba(features)[0, 1]

        # Buy signal
        if probability >= 0.5 and cash >= 5000:
            drawdown = data_with_features.iloc[i]['drawdown']
            investment = calculate_investment_amount(probability, drawdown, cash)

            if investment > 0:
                shares_bought = investment / current_price
                shares += shares_bought
                cash -= investment

                purchases.append({
                    'date': current_date,
                    'price': current_price,
                    'investment': investment,
                    'shares': shares_bought,
                    'probability': probability
                })

                last_purchase_date = current_date

    final_price = data['close'].iloc[-1]
    final_value = cash + (shares * final_price)

    return {
        'final_value': final_value,
        'cash': cash,
        'shares': shares,
        'total_invested': initial_capital - cash,
        'purchases': purchases
    }


def run_weekly_dca(data, initial_capital):
    """Run weekly dollar cost averaging"""

    # Calculate weeks in period
    days = (data.index[-1] - data.index[0]).days
    weeks = days / 7

    if weeks < 1:
        weeks = 1

    weekly_investment = initial_capital / weeks

    shares = 0
    total_invested = 0
    purchases = []

    # Invest every Monday (or closest trading day)
    current_date = data.index[0]
    end_date = data.index[-1]

    while current_date <= end_date:
        # Find closest trading day
        closest_idx = data.index.get_indexer([current_date], method='nearest')[0]

        if closest_idx < len(data) and total_invested < initial_capital:
            trade_date = data.index[closest_idx]
            price = float(data['close'].iloc[closest_idx])

            # Don't buy on same day twice
            if not purchases or trade_date != purchases[-1]['date']:
                shares_bought = weekly_investment / price
                shares += shares_bought
                total_invested += weekly_investment

                purchases.append({
                    'date': trade_date,
                    'price': price,
                    'investment': weekly_investment,
                    'shares': shares_bought
                })

        # Move to next week
        current_date += timedelta(days=7)

    final_price = data['close'].iloc[-1]
    final_value = shares * final_price

    return {
        'final_value': final_value,
        'shares': shares,
        'total_invested': total_invested,
        'purchases': purchases
    }


def backtest_period(start_date, end_date, initial_capital=250000):
    """Backtest both strategies on a specific period"""

    # Load model
    detector = MLCrashDetector()
    detector.load_model('ml_crash_model.pkl')

    # Fetch data
    qqq_data = yf.download('QQQ', start=start_date, end=end_date, progress=False)

    data = pd.DataFrame()
    data['close'] = qqq_data['Close']
    data['high'] = qqq_data['High']
    data['low'] = qqq_data['Low']
    data['volume'] = qqq_data['Volume']

    # Fetch VIX
    vix_data = yf.download('^VIX', start=start_date, end=end_date, progress=False)
    data['vix'] = vix_data['Close']
    data = data.dropna()

    if len(data) < 200:
        return None

    # Run both strategies
    ml_result = run_ml_strategy(data, detector, initial_capital)
    dca_result = run_weekly_dca(data, initial_capital)

    # Calculate returns
    ml_return = (ml_result['final_value'] - initial_capital) / initial_capital
    dca_return = (dca_result['final_value'] - initial_capital) / initial_capital

    # Lump sum comparison
    lump_sum_shares = initial_capital / float(data['close'].iloc[0])
    lump_sum_value = lump_sum_shares * float(data['close'].iloc[-1])
    lump_sum_return = (lump_sum_value - initial_capital) / initial_capital

    return {
        'start_date': data.index[0],
        'end_date': data.index[-1],
        'start_price': float(data['close'].iloc[0]),
        'end_price': float(data['close'].iloc[-1]),
        'ml_result': ml_result,
        'dca_result': dca_result,
        'ml_return': ml_return,
        'dca_return': dca_return,
        'lump_sum_return': lump_sum_return,
        'lump_sum_value': lump_sum_value,
        'outperformance_vs_dca': ml_return - dca_return,
        'outperformance_vs_lump': ml_return - lump_sum_return
    }


def main():
    """Run comprehensive backtest across multiple periods"""

    print("="*100)
    print("COMPREHENSIVE BACKTEST: ML STRATEGY vs WEEKLY DOLLAR COST AVERAGING")
    print("="*100)
    print(f"\nStarting Capital: $250,000")
    print(f"Investment Vehicle: QQQ")
    print(f"ML Strategy: Buy dips detected by Random Forest, hold forever")
    print(f"DCA Strategy: Invest equal amounts weekly, hold forever")
    print(f"\n{'='*100}\n")

    # Define test periods
    periods = [
        # Full historical periods
        ("2005-01-01", "2015-01-01", "2005-2015: Financial Crisis Era"),
        ("2010-01-01", "2020-01-01", "2010-2020: Bull Market + COVID Start"),
        ("2015-01-01", "2025-01-01", "2015-2025: COVID + Recovery"),

        # Specific crisis periods
        ("2007-01-01", "2010-01-01", "2007-2010: Financial Crisis"),
        ("2019-01-01", "2021-01-01", "2019-2021: COVID Crash"),

        # Recent periods
        ("2020-01-01", "2024-01-01", "2020-2024: COVID Recovery"),
        ("2018-01-01", "2023-01-01", "2018-2023: Recent 5 Years"),

        # Bull markets
        ("2009-01-01", "2014-01-01", "2009-2014: Post-Crisis Bull"),
        ("2012-01-01", "2017-01-01", "2012-2017: Steady Bull"),
        ("2021-01-01", "2026-01-01", "2021-2026: Recent Bull"),
    ]

    results = []

    for start, end, description in periods:
        print(f"\nBacktesting: {description}")
        print(f"  Period: {start} to {end}")

        result = backtest_period(start, end)

        if result is None:
            print(f"  ⚠️  Insufficient data, skipping...")
            continue

        results.append({**result, 'description': description})

        # Display results
        print(f"  ✓ Completed")
        print(f"\n  QQQ Performance:")
        print(f"    Start Price: ${result['start_price']:.2f}")
        print(f"    End Price:   ${result['end_price']:.2f}")
        print(f"    Price Change: {((result['end_price']/result['start_price'])-1)*100:+.2f}%")

        print(f"\n  ML Strategy:")
        print(f"    Final Value:  ${result['ml_result']['final_value']:,.0f}")
        print(f"    Total Return: {result['ml_return']*100:+.2f}%")
        print(f"    Purchases:    {len(result['ml_result']['purchases'])}")
        print(f"    Invested:     ${result['ml_result']['total_invested']:,.0f}")
        print(f"    Cash Left:    ${result['ml_result']['cash']:,.0f}")

        print(f"\n  Weekly DCA:")
        print(f"    Final Value:  ${result['dca_result']['final_value']:,.0f}")
        print(f"    Total Return: {result['dca_return']*100:+.2f}%")
        print(f"    Purchases:    {len(result['dca_result']['purchases'])}")

        print(f"\n  Lump Sum (Buy & Hold):")
        print(f"    Final Value:  ${result['lump_sum_value']:,.0f}")
        print(f"    Total Return: {result['lump_sum_return']*100:+.2f}%")

        print(f"\n  Outperformance:")
        print(f"    vs Weekly DCA:  {result['outperformance_vs_dca']*100:+.2f}%")
        print(f"    vs Lump Sum:    {result['outperformance_vs_lump']*100:+.2f}%")

        winner = "ML" if result['outperformance_vs_dca'] > 0 else "DCA"
        print(f"\n  🏆 Winner vs DCA: {winner}")

        print(f"\n{'-'*100}\n")

    # Summary statistics
    if len(results) == 0:
        print("No valid results")
        return

    print(f"\n{'='*100}")
    print("SUMMARY STATISTICS ACROSS ALL PERIODS")
    print(f"{'='*100}\n")

    ml_returns = [r['ml_return'] for r in results]
    dca_returns = [r['dca_return'] for r in results]
    lump_returns = [r['lump_sum_return'] for r in results]

    print(f"ML Strategy:")
    print(f"  Average Return:  {np.mean(ml_returns)*100:+.2f}%")
    print(f"  Median Return:   {np.median(ml_returns)*100:+.2f}%")
    print(f"  Min Return:      {np.min(ml_returns)*100:+.2f}%")
    print(f"  Max Return:      {np.max(ml_returns)*100:+.2f}%")
    print(f"  Std Dev:         {np.std(ml_returns)*100:.2f}%")

    print(f"\nWeekly DCA:")
    print(f"  Average Return:  {np.mean(dca_returns)*100:+.2f}%")
    print(f"  Median Return:   {np.median(dca_returns)*100:+.2f}%")
    print(f"  Min Return:      {np.min(dca_returns)*100:+.2f}%")
    print(f"  Max Return:      {np.max(dca_returns)*100:+.2f}%")

    print(f"\nLump Sum:")
    print(f"  Average Return:  {np.mean(lump_returns)*100:+.2f}%")
    print(f"  Median Return:   {np.median(lump_returns)*100:+.2f}%")

    print(f"\nOutperformance:")
    outperf_dca = [(ml - dca) * 100 for ml, dca in zip(ml_returns, dca_returns)]
    outperf_lump = [(ml - lump) * 100 for ml, lump in zip(ml_returns, lump_returns)]

    print(f"  vs Weekly DCA:")
    print(f"    Average:  {np.mean(outperf_dca):+.2f}%")
    print(f"    Median:   {np.median(outperf_dca):+.2f}%")
    print(f"    Min:      {np.min(outperf_dca):+.2f}%")
    print(f"    Max:      {np.max(outperf_dca):+.2f}%")

    print(f"  vs Lump Sum:")
    print(f"    Average:  {np.mean(outperf_lump):+.2f}%")
    print(f"    Median:   {np.median(outperf_lump):+.2f}%")

    wins_vs_dca = sum(1 for o in outperf_dca if o > 0)
    wins_vs_lump = sum(1 for o in outperf_lump if o > 0)

    print(f"\nWin Rate:")
    print(f"  vs Weekly DCA:  {wins_vs_dca}/{len(results)} ({wins_vs_dca/len(results)*100:.1f}%)")
    print(f"  vs Lump Sum:    {wins_vs_lump}/{len(results)} ({wins_vs_lump/len(results)*100:.1f}%)")

    # Period-by-period comparison table
    print(f"\n{'='*100}")
    print("PERIOD-BY-PERIOD COMPARISON TABLE")
    print(f"{'='*100}\n")

    print(f"{'Period':<35} {'ML Return':<12} {'DCA Return':<12} {'Lump Sum':<12} {'vs DCA':<12} {'Winner'}")
    print(f"{'-'*100}")

    for r in results:
        winner = "ML" if r['outperformance_vs_dca'] > 0 else "DCA"
        print(f"{r['description']:<35} {r['ml_return']*100:>10.2f}% {r['dca_return']*100:>11.2f}% "
              f"{r['lump_sum_return']*100:>11.2f}% {r['outperformance_vs_dca']*100:>10.2f}% {winner:>6}")

    # Best and worst periods
    print(f"\n{'='*100}")
    print("BEST AND WORST PERFORMING PERIODS")
    print(f"{'='*100}\n")

    best_ml = max(results, key=lambda x: x['ml_return'])
    worst_ml = min(results, key=lambda x: x['ml_return'])
    best_outperf = max(results, key=lambda x: x['outperformance_vs_dca'])
    worst_outperf = min(results, key=lambda x: x['outperformance_vs_dca'])

    print(f"Best ML Performance:")
    print(f"  Period: {best_ml['description']}")
    print(f"  ML Return: {best_ml['ml_return']*100:+.2f}%")
    print(f"  DCA Return: {best_ml['dca_return']*100:+.2f}%")
    print(f"  Outperformance: {best_ml['outperformance_vs_dca']*100:+.2f}%")

    print(f"\nWorst ML Performance:")
    print(f"  Period: {worst_ml['description']}")
    print(f"  ML Return: {worst_ml['ml_return']*100:+.2f}%")
    print(f"  DCA Return: {worst_ml['dca_return']*100:+.2f}%")
    print(f"  Outperformance: {worst_ml['outperformance_vs_dca']*100:+.2f}%")

    print(f"\nBest Outperformance vs DCA:")
    print(f"  Period: {best_outperf['description']}")
    print(f"  ML Return: {best_outperf['ml_return']*100:+.2f}%")
    print(f"  DCA Return: {best_outperf['dca_return']*100:+.2f}%")
    print(f"  Outperformance: {best_outperf['outperformance_vs_dca']*100:+.2f}%")

    print(f"\nWorst Outperformance vs DCA:")
    print(f"  Period: {worst_outperf['description']}")
    print(f"  ML Return: {worst_outperf['ml_return']*100:+.2f}%")
    print(f"  DCA Return: {worst_outperf['dca_return']*100:+.2f}%")
    print(f"  Outperformance: {worst_outperf['outperformance_vs_dca']*100:+.2f}%")

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'ml_vs_dca_comparison_{timestamp}.txt'

    with open(filename, 'w') as f:
        f.write("ML STRATEGY vs WEEKLY DCA - COMPREHENSIVE BACKTEST\n")
        f.write("="*100 + "\n\n")

        f.write(f"ML Strategy Average Return: {np.mean(ml_returns)*100:+.2f}%\n")
        f.write(f"Weekly DCA Average Return:  {np.mean(dca_returns)*100:+.2f}%\n")
        f.write(f"Average Outperformance:     {np.mean(outperf_dca):+.2f}%\n")
        f.write(f"Win Rate vs DCA:            {wins_vs_dca}/{len(results)} ({wins_vs_dca/len(results)*100:.1f}%)\n\n")

        f.write("PERIOD-BY-PERIOD RESULTS:\n")
        f.write("="*100 + "\n\n")

        for r in results:
            f.write(f"{r['description']}\n")
            f.write(f"  ML Return:     {r['ml_return']*100:+.2f}%\n")
            f.write(f"  DCA Return:    {r['dca_return']*100:+.2f}%\n")
            f.write(f"  Lump Sum:      {r['lump_sum_return']*100:+.2f}%\n")
            f.write(f"  Outperformance: {r['outperformance_vs_dca']*100:+.2f}%\n")
            f.write(f"  ML Purchases:  {len(r['ml_result']['purchases'])}\n")
            f.write(f"  DCA Purchases: {len(r['dca_result']['purchases'])}\n\n")

    print(f"\n✓ Results saved to {filename}\n")


if __name__ == '__main__':
    main()
