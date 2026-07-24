"""Optional: train a small classifier on the rule-based risk_score.py output.

The composite-score-plus-thresholds approach in risk_score.py works fine for a
handful of tickers, but the thresholds are arbitrary. Once you're loading enough
stocks that eyeballing thresholds stops being reliable, this trains a classifier
using the rule-based levels as weak labels and lets you swap `classify_risk_level`
for `predict_level` in risk_score.py.
"""
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score

from src.ingest.clean_returns import RETURNS_MATRIX_PATH
from src.risk.risk_score import build_features_table, classify_risk_level, compute_composite_score

MODEL_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "risk_model.joblib"
FEATURE_COLUMNS = ["volatility", "beta", "max_drawdown", "sharpe"]


def build_training_set(features: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    scores = compute_composite_score(features)
    labels = scores.apply(classify_risk_level)
    return features[FEATURE_COLUMNS], labels


def train(features: pd.DataFrame, labels: pd.Series) -> RandomForestClassifier:
    model = RandomForestClassifier(n_estimators=200, max_depth=4, random_state=0)
    model.fit(features, labels)
    return model


def predict_level(model: RandomForestClassifier, features_row: pd.Series) -> str:
    return model.predict(features_row[FEATURE_COLUMNS].to_frame().T)[0]


def main() -> None:
    returns = pd.read_parquet(RETURNS_MATRIX_PATH)
    features = build_features_table(returns)

    X, y = build_training_set(features)
    if len(X) < 10:
        print(
            f"Only {len(X)} tickers loaded — too few for a meaningful train/test split. "
            "Load more tickers before training, or keep using the rule-based score."
        )
        return

    model = train(X, y)
    scores = cross_val_score(model, X, y, cv=min(5, len(X)))
    print(f"Cross-val accuracy vs rule-based labels: {scores.mean():.2f} (+/- {scores.std():.2f})")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"Saved model -> {MODEL_PATH}")


if __name__ == "__main__":
    main()
