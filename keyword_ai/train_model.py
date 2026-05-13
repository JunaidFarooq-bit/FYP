"""
Run this script once to train and save the relevance scorer model.
Usage: python keyword_ai/train_model.py
"""

import os
import csv
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from keyword_ai.services.embeddings import get_embeddings

DATASET_PATH = os.path.join(os.path.dirname(__file__), "dataset", "keyword_dataset.csv")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "relevance_scorer.pkl")


def load_dataset(path: str):
    keywords, labels = [], []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            keywords.append(row["keyword"].strip())
            labels.append(int(row["label"].strip()))
    return keywords, labels


def train():
    print("Loading dataset...")
    keywords, labels = load_dataset(DATASET_PATH)
    print(f"  {len(keywords)} samples loaded.")

    print("Generating embeddings (this may take ~30s on first run)...")
    X = get_embeddings(keywords)
    y = np.array(labels)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("Training Logistic Regression...")
    clf = LogisticRegression(max_iter=500, C=1.0, random_state=42)
    clf.fit(X_train, y_train)

    print("\nEvaluation on test set:")
    y_pred = clf.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=["Not relevant", "Relevant"]))

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    print(f"\nModel saved to: {MODEL_PATH}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    train()