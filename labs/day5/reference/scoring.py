"""
The machine learning step of the capstone pipeline.

This is the point where the week joins up. The features are not read from a CSV
that someone prepared by hand: they are read from `analytics_marts.ml_request_features`,
a table dbt built on Day 4 from the raw extract landed on Day 1, using the
feature ideas worked out on Day 2, to train the kind of model built on Day 3.

The predictions are written back into the warehouse, so the output of the model
is queryable alongside everything else rather than trapped in a notebook.

The estimator is a scikit-learn Pipeline, exactly as on Day 3. In a pipeline the
scaler is fitted inside each cross-validation fold, so the validation fold has no
influence on the scaling. That is the same idea as idempotency in the pipeline
around it: the unit does its own work and does not depend on hidden state.
"""
from __future__ import annotations

import logging

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text
from sqlalchemy.engine import Engine

LOG = logging.getLogger("scoring")

FEATURE_TABLE = "analytics_marts.ml_request_features"
PREDICTION_TABLE = "sla_predictions"
PREDICTION_SCHEMA = "analytics_ml"

# resolution_hours is excluded deliberately. It is only known once the request
# has been resolved, so using it to predict whether the request met its target
# would be leakage. This is the same drop made on Day 3.
LEAKY_COLUMNS = ["resolution_hours", "satisfaction_score"]

RANDOM_STATE = 42


def load_features(engine: Engine) -> pd.DataFrame:
    """
    Read the model-ready feature mart that dbt builds.

    The rows are then sorted into a canonical order. This matters more than it
    looks. A table has no inherent row order, and dbt rebuilds this one from
    scratch on every run, so Postgres is free to hand the rows back differently
    each time. train_test_split divides the frame by position, so an unordered
    read produces a different split, and therefore different accuracy, from an
    identical pipeline on identical data.

    Sorting here is what makes the run reproducible. It is the same idea as
    idempotency one level down: given the same inputs, produce the same output.
    """
    df = pd.read_sql(text(f"select * from {FEATURE_TABLE}"), engine)
    df = df.sort_values(by=list(df.columns), kind="mergesort").reset_index(drop=True)
    LOG.info("load_features: %s rows, %s columns", len(df), df.shape[1])
    return df


def build_pipeline() -> Pipeline:
    """
    Assemble the estimator.

    Imputer first, then scaler, then the forest. Writing it as a Pipeline means
    the whole thing is one object that can be fitted, scored and later saved,
    rather than four steps that must be repeated in the right order by hand.
    """
    return Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=200,
                    min_samples_leaf=5,
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def train_and_score(engine: Engine) -> dict:
    """
    Train on the labelled rows, then predict for every row including the
    unlabelled ones, and write the predictions back to the warehouse.

    The unlabelled rows are the requests that are still open. Those are exactly
    the rows a service manager cares about, because they are the ones where a
    prediction can still change the outcome.
    """
    df = load_features(engine)

    features = [c for c in df.columns if c not in LEAKY_COLUMNS + ["sla_met"]]
    labelled = df[df["sla_met"].notna()].copy()
    unlabelled = df[df["sla_met"].isna()].copy()

    LOG.info(
        "train_and_score: %s labelled, %s unlabelled, %s features",
        len(labelled),
        len(unlabelled),
        len(features),
    )

    X = labelled[features]
    y = labelled["sla_met"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=RANDOM_STATE, stratify=y
    )

    pipe = build_pipeline()
    pipe.fit(X_train, y_train)

    predicted = pipe.predict(X_test)
    probability = pipe.predict_proba(X_test)[:, 1]

    metrics = {
        "rows_total": int(len(df)),
        "rows_labelled": int(len(labelled)),
        "rows_unlabelled": int(len(unlabelled)),
        "n_features": len(features),
        "accuracy": round(float(accuracy_score(y_test, predicted)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, probability)), 4),
    }
    LOG.info("train_and_score: %s", metrics)
    LOG.info("\n%s", classification_report(y_test, predicted, digits=3))

    # Score every row, so open requests get a prediction too.
    scored = df[features].copy()
    out = pd.DataFrame(
        {
            "predicted_sla_met": pipe.predict(scored).astype(int),
            "predicted_probability": pipe.predict_proba(scored)[:, 1].round(4),
            "actual_sla_met": df["sla_met"],
            "is_open": df["sla_met"].isna().astype(int),
        }
    )

    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {PREDICTION_SCHEMA}"))
    out.to_sql(
        PREDICTION_TABLE,
        engine,
        schema=PREDICTION_SCHEMA,
        if_exists="replace",
        index=False,
    )
    LOG.info(
        "train_and_score: wrote %s rows to %s.%s",
        len(out),
        PREDICTION_SCHEMA,
        PREDICTION_TABLE,
    )

    return metrics
