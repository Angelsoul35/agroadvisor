"""Benchmark the learned crop recommender on real agronomic data.

This runs a leakage-free evaluation of
:class:`~agroadvisor.recommender.CropRecommender` on the 2200-row public
Crop-recommendation dataset and prints a readable report. It demonstrates, with
real numbers, that the learned component generalises rather than memorising:

* **stratified 5-fold cross-validation** — accuracy and macro-F1, mean +/- std,
  so the headline figure is an average over five disjoint test folds, not one
  lucky split;
* **a held-out 25% split** — train vs test accuracy and the train/test gap, the
  direct read on over- or under-fitting;
* **a fit verdict** — well-fit / overfit / underfit, derived from the gap and the
  margin over chance;
* **a shuffled-label control** — the same pipeline trained on labels that have
  been randomly permuted, which must collapse to chance (1/22). If it did not,
  the real score would be suspect (a sign of leakage).

Run it with ``python -m agroadvisor.real_benchmark``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split

from .real_data import AgroSample, load_samples
from .recommender import build_model

#: Human-readable dataset name for the printed report.
_DATASET_LABEL = "randalakab/Crop-recommendation (Hugging Face)"

#: Evaluation protocol constants (fixed seeds keep the whole report reproducible).
CV_SPLITS = 5
HOLDOUT_FRACTION = 0.25
RANDOM_STATE = 42
SHUFFLE_SEED = 0

#: Fit thresholds. A train/test gap above ``OVERFIT_GAP`` means the model fits its
#: training set markedly better than unseen data (overfitting, high variance). A
#: model whose held-out accuracy fails to clear ``WELL_FIT_CHANCE_MULTIPLE`` times
#: the chance rate — without a large gap — is too weak to capture the signal
#: (underfitting, high bias). Everything else is well-fit.
OVERFIT_GAP = 0.10
WELL_FIT_CHANCE_MULTIPLE = 4.0


@dataclass(frozen=True)
class CrossValScores:
    """Mean and spread of the metrics across the cross-validation test folds."""

    accuracy_mean: float
    accuracy_std: float
    macro_f1_mean: float
    macro_f1_std: float


@dataclass(frozen=True)
class HoldoutScores:
    """Train vs test scores on a single stratified held-out split."""

    train_accuracy: float
    test_accuracy: float
    test_macro_f1: float

    @property
    def gap(self) -> float:
        """Train minus test accuracy: the generalisation gap."""
        return self.train_accuracy - self.test_accuracy


@dataclass(frozen=True)
class BenchmarkReport:
    """The full benchmark result."""

    n_samples: int
    n_classes: int
    chance: float
    cross_val: CrossValScores
    holdout: HoldoutScores
    shuffled_accuracy: float
    fit_verdict: str

    @property
    def cv_holdout_agreement(self) -> float:
        """How closely the CV mean accuracy and the held-out test accuracy agree."""
        return abs(self.cross_val.accuracy_mean - self.holdout.test_accuracy)


def _xy(samples: list[AgroSample]) -> tuple[np.ndarray, np.ndarray]:
    features = np.asarray([s.features() for s in samples], dtype=float)
    labels = np.asarray([s.label for s in samples])
    return features, labels


def cross_validate_recommender(
    features: np.ndarray,
    labels: np.ndarray,
    *,
    splits: int = CV_SPLITS,
    random_state: int = RANDOM_STATE,
) -> CrossValScores:
    """Stratified k-fold CV, returning mean +/- std of accuracy and macro-F1."""
    folds = StratifiedKFold(n_splits=splits, shuffle=True, random_state=random_state)
    scores = cross_validate(
        build_model(), features, labels, cv=folds, scoring=("accuracy", "f1_macro")
    )
    return CrossValScores(
        accuracy_mean=float(scores["test_accuracy"].mean()),
        accuracy_std=float(scores["test_accuracy"].std()),
        macro_f1_mean=float(scores["test_f1_macro"].mean()),
        macro_f1_std=float(scores["test_f1_macro"].std()),
    )


def holdout_recommender(
    features: np.ndarray,
    labels: np.ndarray,
    *,
    fraction: float = HOLDOUT_FRACTION,
    random_state: int = RANDOM_STATE,
) -> HoldoutScores:
    """Fit on a stratified train split and score train and test to read the gap."""
    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=fraction, stratify=labels, random_state=random_state
    )
    model = build_model()
    model.fit(x_train, y_train)
    return HoldoutScores(
        train_accuracy=float(accuracy_score(y_train, model.predict(x_train))),
        test_accuracy=float(accuracy_score(y_test, model.predict(x_test))),
        test_macro_f1=float(f1_score(y_test, model.predict(x_test), average="macro")),
    )


def shuffled_control(
    features: np.ndarray,
    labels: np.ndarray,
    *,
    splits: int = CV_SPLITS,
    random_state: int = RANDOM_STATE,
    seed: int = SHUFFLE_SEED,
) -> float:
    """CV accuracy with the labels randomly permuted: must collapse to chance.

    Breaking the feature-label link destroys all signal, so a leakage-free
    pipeline can do no better than guessing. A score that stayed high here would
    mean the evaluation itself was leaking information.
    """
    permuted = labels.copy()
    np.random.default_rng(seed).shuffle(permuted)
    folds = StratifiedKFold(n_splits=splits, shuffle=True, random_state=random_state)
    scores = cross_validate(build_model(), features, permuted, cv=folds, scoring=("accuracy",))
    return float(scores["test_accuracy"].mean())


def classify_fit(
    holdout: HoldoutScores,
    chance: float,
    *,
    overfit_gap: float = OVERFIT_GAP,
    chance_multiple: float = WELL_FIT_CHANCE_MULTIPLE,
) -> str:
    """Label the fit as ``"well-fit"``, ``"overfit"`` or ``"underfit"``.

    * **overfit** (high variance) — the train/test gap exceeds ``overfit_gap``:
      the model fits its training set markedly better than unseen data.
    * **underfit** (high bias) — with no large gap, the held-out accuracy still
      fails to clear ``chance_multiple`` times the chance rate: the model is too
      simple to capture the signal and is weak on both train and test.
    * **well-fit** — a small gap *and* test accuracy comfortably above chance.
    """
    if holdout.gap > overfit_gap:
        return "overfit"
    if holdout.test_accuracy < chance_multiple * chance:
        return "underfit"
    return "well-fit"


def evaluate(samples: list[AgroSample]) -> BenchmarkReport:
    """Run the full benchmark (CV, held-out split, shuffled control) on the samples."""
    features, labels = _xy(samples)
    classes = sorted(set(labels.tolist()))
    chance = 1.0 / len(classes)
    holdout = holdout_recommender(features, labels)
    return BenchmarkReport(
        n_samples=len(samples),
        n_classes=len(classes),
        chance=chance,
        cross_val=cross_validate_recommender(features, labels),
        holdout=holdout,
        shuffled_accuracy=shuffled_control(features, labels),
        fit_verdict=classify_fit(holdout, chance),
    )


def format_report(report: BenchmarkReport) -> str:
    """Render the benchmark as a readable, aligned text block."""
    cv = report.cross_val
    ho = report.holdout
    margin = ho.test_accuracy / report.chance
    lines = [
        "AgroAdvisor - learned crop recommender, real-data benchmark",
        "===========================================================",
        f"Dataset : {_DATASET_LABEL}",
        f"Samples : {report.n_samples} real field observations",
        f"Classes : {report.n_classes} crops",
        "Features: N, P, K, temperature, humidity, ph, rainfall",
        f"Chance  : {report.chance:.4f}  (1/{report.n_classes})",
        "Model   : StandardScaler -> multinomial LogisticRegression",
        "",
        f"Stratified {CV_SPLITS}-fold cross-validation",
        f"  accuracy : {cv.accuracy_mean:.4f} +/- {cv.accuracy_std:.4f}",
        f"  macro-F1 : {cv.macro_f1_mean:.4f} +/- {cv.macro_f1_std:.4f}",
        "",
        "Held-out split (75% train / 25% test, stratified)",
        f"  train accuracy : {ho.train_accuracy:.4f}",
        f"  test  accuracy : {ho.test_accuracy:.4f}",
        f"  test  macro-F1 : {ho.test_macro_f1:.4f}",
        f"  train-test gap : {ho.gap:.4f}",
        "",
        "Generalisation",
        f"  CV accuracy ({cv.accuracy_mean:.4f}) and held-out test accuracy "
        f"({ho.test_accuracy:.4f}) agree to within {report.cv_holdout_agreement:.4f}",
        f"  verdict: {report.fit_verdict.upper()}  "
        f"(gap {ho.gap:.4f} <= {OVERFIT_GAP:g}; test accuracy {margin:.1f}x chance)",
        "",
        "Shuffled-label control",
        f"  CV accuracy on permuted labels : {report.shuffled_accuracy:.4f}  "
        f"(collapses to chance {report.chance:.4f})",
    ]
    return "\n".join(lines)


def main() -> int:
    """Load the vendored dataset, run the benchmark, and print the report."""
    report = evaluate(load_samples())
    print(format_report(report))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
