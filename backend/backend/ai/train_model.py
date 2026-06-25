from pathlib import Path

import joblib
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

from backend.ai.anomaly_detection import train_isolation_forest
from backend.ai.feature_engineering import (
    build_feature_matrix,
    prepare_training_dataset,
)


MODEL_DIR = Path(__file__).resolve().parent / "models"

FAULT_MODEL_PATH = MODEL_DIR / "fault_prediction_xgboost.joblib"
ANOMALY_MODEL_PATH = MODEL_DIR / "anomaly_isolation_forest.joblib"
LABEL_ENCODER_PATH = MODEL_DIR / "label_encoder.joblib"


def train_fault_prediction_model(x_values, y_values):
    label_encoder = LabelEncoder()
    encoded_labels = label_encoder.fit_transform(y_values)

    if len(set(encoded_labels)) < 2:
        raise ValueError("Need at least two classes to train fault prediction model.")

    x_train, x_test, y_train, y_test = train_test_split(
        x_values,
        encoded_labels,
        test_size=0.2,
        random_state=42,
        stratify=encoded_labels,
    )

    model = XGBClassifier(
        n_estimators=120,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="multi:softprob",
        eval_metric="mlogloss",
        random_state=42,
    )

    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    accuracy = accuracy_score(y_test, predictions)

    print(f"Fault prediction accuracy: {accuracy:.4f}")
    print(classification_report(y_test, predictions, target_names=label_encoder.classes_))

    return model, label_encoder


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print("Preparing V.E.N.U.S training dataset...")
    training_dataframe = prepare_training_dataset(limit=5000)

    print("Training labels:")
    print(training_dataframe["label"].value_counts())

    x_values, y_values = build_feature_matrix(training_dataframe)

    print("Training Isolation Forest anomaly detection model...")
    anomaly_model = train_isolation_forest(x_values)

    print("Training XGBoost fault prediction model...")
    fault_model, label_encoder = train_fault_prediction_model(x_values, y_values)

    joblib.dump(anomaly_model, ANOMALY_MODEL_PATH)
    joblib.dump(fault_model, FAULT_MODEL_PATH)
    joblib.dump(label_encoder, LABEL_ENCODER_PATH)

    print("Models saved successfully:")
    print(f"- {ANOMALY_MODEL_PATH}")
    print(f"- {FAULT_MODEL_PATH}")
    print(f"- {LABEL_ENCODER_PATH}")


if __name__ == "__main__":
    main()