#!/usr/bin/env python3
"""
Machine Learning Crash Detection System
========================================
Uses Random Forest to identify market dips that rebound within 1 year.

Strategy:
- Train on historical market dips (5%+, 10%+, 15%+)
- Label as "good buying opportunity" if market rebounds within 1 year
- Features: Technical indicators, VIX, volume, momentum, volatility
- Model: Random Forest classifier
- Output: Probability of current market being a good buying opportunity
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib
import json
import warnings
warnings.filterwarnings('ignore')


class MLCrashDetector:
    """Machine Learning based crash/dip detection system"""

    def __init__(self, dip_threshold=-0.05, rebound_months=12):
        """
        Initialize ML crash detector

        Args:
            dip_threshold: Minimum drawdown to consider (e.g., -0.05 = -5%)
            rebound_months: Months to wait for rebound (default: 12)
        """
        self.dip_threshold = dip_threshold
        self.rebound_months = rebound_months
        self.model = None
        self.feature_names = None
        self.scaler = None

    def fetch_data(self, years=25):
        """Fetch historical market data"""
        print(f"\nFetching {years} years of market data...")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)

        # Fetch S&P 500 and VIX
        spy_data = yf.download('SPY', start=start_date, end=end_date, progress=False)
        vix_data = yf.download('^VIX', start=start_date, end=end_date, progress=False)

        # Combine data
        data = pd.DataFrame()
        data['close'] = spy_data['Close']
        data['high'] = spy_data['High']
        data['low'] = spy_data['Low']
        data['volume'] = spy_data['Volume']
        data['vix'] = vix_data['Close']

        data = data.dropna()

        print(f"✓ Loaded {len(data)} days of data")
        print(f"  Period: {data.index[0].date()} to {data.index[-1].date()}")

        return data

    def calculate_technical_indicators(self, data):
        """Calculate technical indicators as features"""
        df = data.copy()

        # Returns
        df['returns_1d'] = df['close'].pct_change()
        df['returns_5d'] = df['close'].pct_change(5)
        df['returns_20d'] = df['close'].pct_change(20)
        df['returns_60d'] = df['close'].pct_change(60)

        # Moving averages
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        df['sma_200'] = df['close'].rolling(200).mean()

        # Price relative to moving averages
        df['price_vs_sma20'] = (df['close'] - df['sma_20']) / df['sma_20']
        df['price_vs_sma50'] = (df['close'] - df['sma_50']) / df['sma_50']
        df['price_vs_sma200'] = (df['close'] - df['sma_200']) / df['sma_200']

        # Volatility
        df['volatility_20d'] = df['returns_1d'].rolling(20).std()
        df['volatility_60d'] = df['returns_1d'].rolling(60).std()

        # RSI (Relative Strength Index)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Bollinger Bands
        bb_middle = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        df['bb_upper'] = bb_middle + (bb_std * 2)
        df['bb_lower'] = bb_middle - (bb_std * 2)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_diff'] = df['macd'] - df['macd_signal']

        # Volume indicators
        df['volume_sma_20'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma_20']

        # Drawdown from all-time high
        df['ath'] = df['close'].expanding().max()
        df['drawdown'] = (df['close'] - df['ath']) / df['ath']

        # Drawdown from recent highs
        df['high_20d'] = df['close'].rolling(20).max()
        df['high_60d'] = df['close'].rolling(60).max()
        df['drawdown_20d'] = (df['close'] - df['high_20d']) / df['high_20d']
        df['drawdown_60d'] = (df['close'] - df['high_60d']) / df['high_60d']

        # VIX features
        df['vix_ma_20'] = df['vix'].rolling(20).mean()
        df['vix_ratio'] = df['vix'] / df['vix_ma_20']

        # Momentum
        df['momentum_5d'] = df['close'] - df['close'].shift(5)
        df['momentum_20d'] = df['close'] - df['close'].shift(20)

        return df

    def label_data(self, data):
        """
        Label data points as good buying opportunities (1) or not (0)

        A point is labeled 1 if:
        1. Market has dipped by dip_threshold or more from recent high
        2. Market rebounds to new high within rebound_months
        """
        df = data.copy()
        df['label'] = 0

        rebound_days = self.rebound_months * 21  # Trading days

        labeled_count = 0
        positive_count = 0

        for i in range(len(df) - rebound_days):
            current_price = df['close'].iloc[i]
            recent_high = df['close'].iloc[max(0, i-60):i+1].max()

            # Check if currently in a dip
            drawdown = (current_price - recent_high) / recent_high

            if drawdown <= self.dip_threshold:
                # Check if market rebounds within rebound period
                future_max = df['close'].iloc[i:i+rebound_days].max()

                # Label as 1 if market makes new high or recovers significantly
                if future_max >= recent_high * 0.98:  # Recovers to within 2% of high
                    df['label'].iloc[i] = 1
                    positive_count += 1

                labeled_count += 1

        print(f"\n✓ Labeled {labeled_count} dip events")
        print(f"  Positive labels (good opportunities): {positive_count} ({positive_count/labeled_count*100:.1f}%)")
        print(f"  Negative labels (bad opportunities): {labeled_count - positive_count} ({(labeled_count-positive_count)/labeled_count*100:.1f}%)")

        return df

    def prepare_features(self, data):
        """Prepare feature matrix and labels"""

        # Select feature columns
        feature_cols = [
            # Returns
            'returns_1d', 'returns_5d', 'returns_20d', 'returns_60d',

            # Price vs moving averages
            'price_vs_sma20', 'price_vs_sma50', 'price_vs_sma200',

            # Volatility
            'volatility_20d', 'volatility_60d',

            # Technical indicators
            'rsi', 'bb_position', 'macd_diff',

            # Volume
            'volume_ratio',

            # Drawdowns
            'drawdown', 'drawdown_20d', 'drawdown_60d',

            # VIX
            'vix', 'vix_ratio',

            # Momentum
            'momentum_5d', 'momentum_20d'
        ]

        # Remove rows with NaN
        df = data.dropna(subset=feature_cols + ['label'])

        X = df[feature_cols].values
        y = df['label'].values
        dates = df.index

        self.feature_names = feature_cols

        print(f"\n✓ Prepared features")
        print(f"  Features: {len(feature_cols)}")
        print(f"  Samples: {len(X)}")
        print(f"  Positive samples: {y.sum()} ({y.sum()/len(y)*100:.1f}%)")

        return X, y, dates

    def train_model(self, X, y):
        """Train Random Forest classifier"""
        print(f"\n{'='*70}")
        print("TRAINING RANDOM FOREST MODEL")
        print(f"{'='*70}")

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        print(f"\nTrain set: {len(X_train)} samples")
        print(f"Test set:  {len(X_test)} samples")

        # Train Random Forest
        print(f"\nTraining Random Forest...")
        self.model = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            max_features='sqrt',
            random_state=42,
            n_jobs=-1,
            class_weight='balanced'  # Handle class imbalance
        )

        self.model.fit(X_train, y_train)

        # Evaluate
        print(f"\n{'='*70}")
        print("MODEL EVALUATION")
        print(f"{'='*70}")

        # Training accuracy
        train_score = self.model.score(X_train, y_train)
        print(f"\nTraining accuracy: {train_score:.3f}")

        # Test accuracy
        test_score = self.model.score(X_test, y_test)
        print(f"Test accuracy:     {test_score:.3f}")

        # Cross-validation
        cv_scores = cross_val_score(self.model, X_train, y_train, cv=5)
        print(f"CV accuracy:       {cv_scores.mean():.3f} (+/- {cv_scores.std()*2:.3f})")

        # Predictions
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]

        # Classification report
        print(f"\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=['Not Opportunity', 'Opportunity']))

        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        print(f"\nConfusion Matrix:")
        print(f"                 Predicted Not   Predicted Opp")
        print(f"Actual Not         {cm[0,0]:6d}        {cm[0,1]:6d}")
        print(f"Actual Opp         {cm[1,0]:6d}        {cm[1,1]:6d}")

        # ROC AUC
        roc_auc = roc_auc_score(y_test, y_pred_proba)
        print(f"\nROC AUC Score: {roc_auc:.3f}")

        # Feature importance
        print(f"\n{'='*70}")
        print("TOP 10 MOST IMPORTANT FEATURES")
        print(f"{'='*70}")

        feature_importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

        for idx, row in feature_importance.head(10).iterrows():
            print(f"  {row['feature']:<25} {row['importance']:.4f}")

        return X_test, y_test, y_pred_proba, feature_importance

    def predict_current_market(self, data):
        """Predict if current market is a buying opportunity"""

        if self.model is None:
            raise ValueError("Model not trained. Call train_model() first.")

        # Calculate features for latest data point
        df = self.calculate_technical_indicators(data)

        # Get latest features
        latest = df.iloc[-1]
        X_current = np.array([[latest[col] for col in self.feature_names]])

        # Predict
        prediction = self.model.predict(X_current)[0]
        probability = self.model.predict_proba(X_current)[0, 1]

        return {
            'prediction': 'BUY OPPORTUNITY' if prediction == 1 else 'HOLD',
            'probability': probability,
            'date': df.index[-1],
            'price': latest['close'],
            'drawdown': latest['drawdown'],
            'vix': latest['vix'],
            'rsi': latest['rsi']
        }

    def save_model(self, filename='ml_crash_model.pkl'):
        """Save trained model to disk"""
        if self.model is None:
            raise ValueError("No model to save")

        model_data = {
            'model': self.model,
            'feature_names': self.feature_names,
            'dip_threshold': self.dip_threshold,
            'rebound_months': self.rebound_months
        }

        joblib.dump(model_data, filename)
        print(f"\n✓ Model saved to {filename}")

    def load_model(self, filename='ml_crash_model.pkl'):
        """Load trained model from disk"""
        model_data = joblib.load(filename)

        self.model = model_data['model']
        self.feature_names = model_data['feature_names']
        self.dip_threshold = model_data['dip_threshold']
        self.rebound_months = model_data['rebound_months']

        print(f"\n✓ Model loaded from {filename}")


def main():
    """Main training and evaluation"""

    print(f"{'='*70}")
    print("ML CRASH DETECTION SYSTEM")
    print(f"{'='*70}")

    # Initialize detector
    detector = MLCrashDetector(
        dip_threshold=-0.05,  # 5% dip from recent high
        rebound_months=12      # Rebounds within 1 year
    )

    # Fetch data
    data = detector.fetch_data(years=25)

    # Calculate features
    print(f"\nCalculating technical indicators...")
    data = detector.calculate_technical_indicators(data)

    # Label data
    print(f"\nLabeling buying opportunities...")
    data = detector.label_data(data)

    # Prepare features
    X, y, dates = detector.prepare_features(data)

    # Train model
    X_test, y_test, y_pred_proba, feature_importance = detector.train_model(X, y)

    # Save model
    detector.save_model()

    # Test current market
    print(f"\n{'='*70}")
    print("CURRENT MARKET ANALYSIS")
    print(f"{'='*70}")

    # Fetch recent data
    recent_data = detector.fetch_data(years=2)

    result = detector.predict_current_market(recent_data)

    print(f"\nDate: {result['date'].date()}")
    print(f"Price: ${result['price']:.2f}")
    print(f"Drawdown: {result['drawdown']*100:.2f}%")
    print(f"VIX: {result['vix']:.1f}")
    print(f"RSI: {result['rsi']:.1f}")
    print(f"\nPrediction: {result['prediction']}")
    print(f"Probability: {result['probability']*100:.1f}%")

    if result['probability'] > 0.7:
        print(f"\n🟢 HIGH CONFIDENCE buying opportunity!")
    elif result['probability'] > 0.5:
        print(f"\n🟡 MODERATE buying opportunity")
    else:
        print(f"\n🔴 NOT a buying opportunity")

    print(f"\n{'='*70}")


if __name__ == '__main__':
    main()
