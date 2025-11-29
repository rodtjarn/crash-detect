# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an automated trading alert system that monitors stock market conditions and sends email/SMS notifications when specific technical indicators align for high-probability trade setups. The system implements a four-indicator strategy combining fractal dimension analysis, put/call ratios, VIX levels, and Hidden Markov Model regime detection.

**Core Strategy**: Fractal < 0.7 + Put/Call > 1.2 + Markov=Volatile + VIX > 25
**Expected Performance**: 90%+ win rate, 4%+ average return per trade
**Signal Frequency**: ~10-15 signals per year

## System Architecture

### Main Components

**trading_alert_system.py** (667 lines)
- `TradingAlertSystem` class: Main orchestrator for the entire system
- Market data fetching via yfinance API
- Four technical indicator calculations:
  - Fractal dimension using Hurst exponent (R/S analysis)
  - Put/Call ratio proxy calculation
  - VIX (volatility index) monitoring
  - Hidden Markov Model for regime detection (4-state: Normal, Volatile, Crisis, Bull)
- Signal generation logic for both LONG and SHORT setups
- Email alerts via SMTP (supports Gmail, Outlook, Yahoo)
- SMS alerts via Twilio API (optional)
- Trade recommendation engine with entry/exit/stop-loss calculations

**config.json**
- JSON configuration for email/SMS credentials
- Trading parameters (symbols, position sizing, thresholds)
- Data fetching parameters (lookback days, minimum data points)
- Threshold customization for different risk profiles

**test_setup.py**
- Dependency validation (checks all required Python packages)
- Configuration validation
- SMTP connectivity testing
- Market data fetch verification

## Key Technical Details

### Indicator Calculations

**Fractal Dimension** (lines 139-203 in trading_alert_system.py)
- Uses Hurst exponent via rescaled range (R/S) analysis
- Lower values (<0.7) indicate volatility compression ("calm before the storm")
- Computed on 60-day rolling window of closing prices
- Max lag of 20 days for R/S calculation

**Hidden Markov Model** (lines 205-261)
- 4-state Gaussian HMM with full covariance
- Features: returns, 5-day volatility, 20-day volatility
- State classification based on mean returns and volatility:
  - Crisis: negative returns, high volatility (std > 0.015)
  - Volatile: high volatility (std > 0.012)
  - Bull: positive returns, lower volatility
  - Normal: low volatility baseline
- Trained on 90 days of historical data

**Put/Call Ratio Proxy** (lines 124-137)
- Real P/C data requires CBOE subscription
- Current implementation uses VIX-normalized proxy with 5-day price momentum
- Formula: 0.8 + (VIX/20 - 1) * 0.3 + (-returns_5d_avg * 10)
- Clipped to realistic range [0.3, 2.5]

### Signal Logic

**SHORT Signal** (lines 305-312):
- Fractal dimension < 0.7 (volatility compressed)
- Put/Call ratio > 1.2 (bearish sentiment)
- VIX > 25 (elevated fear)
- Markov state = "Volatile" (unstable regime)
- All 4 conditions must be met simultaneously

**LONG Signal** (lines 314-321):
- Fractal dimension < 0.8
- Put/Call ratio < 0.5
- VIX < 20
- Markov state = "Bull"
- All 4 conditions must be met simultaneously

## Common Development Tasks

### Running the System

**Manual check** (for testing):
```bash
python trading_alert_system.py
```

**Test setup** (verify dependencies and config):
```bash
python test_setup.py
```

**Install dependencies**:
```bash
pip install yfinance pandas numpy hmmlearn scikit-learn
pip install twilio  # Optional, for SMS alerts
```

### Scheduled Execution

**Linux/Mac (cron)**:
```bash
# Run daily at 4:30 PM ET (market close)
30 16 * * 1-5 cd /home/per/work && python trading_alert_system.py >> logs.txt 2>&1
```

**Windows (Task Scheduler)**:
- Trigger: Daily at 4:30 PM, Monday-Friday
- Action: `python C:\path\to\trading_alert_system.py`

### Configuration

**Email setup** (config.json):
- For Gmail: Use app-specific password (not regular password)
- Generate at: https://myaccount.google.com/apppasswords
- Requires 2FA enabled on Gmail account

**Threshold tuning**:
- More conservative (fewer signals): Lower fractal_max (0.6), raise put_call_min (1.3), raise vix_min (30)
- More aggressive (more signals): Raise fractal_max (0.8), lower put_call_min (1.1), lower vix_min (20)

## Important Implementation Notes

### Data Fetching
- Uses yfinance library for market data (Yahoo Finance API)
- Default lookback: 90 days of historical data
- Minimum 60 data points required for indicator calculations
- VIX symbol: ^VIX
- S&P 500 index: ^GSPC

### Put/Call Ratio Limitation
- Current implementation uses a proxy calculation (lines 124-137)
- For production use, replace with real CBOE Put/Call ratio data
- Real data requires subscription to CBOE data feed
- Modify `calculate_put_call_proxy()` method to integrate real data source

### HMM Training
- Model trained on each run (not persisted)
- Training uses 90 days of return and volatility features
- State labels determined dynamically based on statistical characteristics
- Model convergence: 100 iterations, random_state=42 for reproducibility

### Position Sizing & Risk
- Default: 2% of portfolio per trade
- Stop loss: Entry ± 1.5%
- Target: Entry ± 4%
- Risk/Reward ratio: 2.7:1

## File Dependencies

```
trading_alert_system.py
├── yfinance (market data)
├── pandas (data manipulation)
├── numpy (numerical calculations)
├── hmmlearn (Hidden Markov Model)
├── scikit-learn (HMM dependency)
├── smtplib (email alerts)
└── twilio (optional SMS alerts)

config.json (required for configuration)
test_setup.py (standalone diagnostic script)
```

## Testing & Validation

**Dependency check**:
```bash
python test_setup.py
```
Validates: package imports, config.json format, SMTP connectivity, data fetch capability

**Manual trigger test**:
```bash
python trading_alert_system.py
```
Shows current indicator values and whether signals triggered

**Check logs** (if scheduled via cron):
```bash
tail -f logs.txt
```

## Alert Format

**Email alerts** include:
- Trade direction (LONG/SHORT) and symbol
- Position size recommendation
- Entry price, stop loss, target price
- Win probability and expected return
- Current values of all 4 indicators
- Detailed rationale explaining the setup

**SMS alerts** (optional) include:
- Condensed trade information
- Entry/stop/target prices
- Win probability

## Risk Management Defaults

- Position size: 2% of portfolio (configurable in config.json)
- Stop loss: Always 1.5% from entry
- Target profit: 4% from entry
- Maximum recommended position: 3% of portfolio
- Signal frequency: Approximately 1-2 per month

## Known Limitations

1. **Put/Call Ratio**: Uses proxy calculation instead of real CBOE data
2. **Market hours**: No pre-market or after-hours data handling
3. **Single market focus**: Optimized for S&P 500 only
4. **No backtesting mode**: System runs live checks only (backtesting analysis in separate .txt files)
5. **Email rate limiting**: No duplicate alert prevention (sends on every run if conditions met)
6. **Data dependencies**: Relies on Yahoo Finance API availability
