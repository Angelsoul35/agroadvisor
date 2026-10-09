"""Real-data benchmark of the learned crop recommender.

These tests are functional: they load the vendored real dataset, train and
evaluate the recommender, and assert properties that only hold if the pipeline
genuinely works — the loader returns all 2200 real rows across 22 crops, the
recommender beats chance by a wide margin and generalises (its cross-validation
and held-out numbers agree with a small train/test gap), and a shuffled-label
control collapses to chance. The fetch path is exercised with a monkeypatched
``urlopen`` that drives the retry and pagination logic without a network call.
"""

from __future__ import annotations

import io
import json
import urllib.error
from urllib.parse import parse_qs, urlparse

import pytest

from agroadvisor import real_data
from agroadvisor.engine import SoilTest
from agroadvisor.real_benchmark import (
    OVERFIT_GAP,
    HoldoutScores,
    classify_fit,
    evaluate,
    format_report,
)
from agroadvisor.real_data import (
    EXPECTED_CROPS,
    EXPECTED_ROWS,
    FEATURE_NAMES,
    AgroSample,
    fetch_rows,
    load_samples,
    write_jsonl,
)
from agroadvisor.recommender import CropRecommender


@pytest.fixture(scope="module")
def samples() -> list[AgroSample]:
    return load_samples()


@pytest.fixture(scope="module")
def report(samples):
    # The expensive step (CV + held-out + shuffled control) runs once per module.
    return evaluate(samples)


# --------------------------------------------------------------------------- #
# Loader: the vendored file really is the full dataset.
# --------------------------------------------------------------------------- #


def test_loader_returns_the_full_real_dataset(samples):
    assert EXPECTED_ROWS == 2200
    assert EXPECTED_CROPS == 22
    assert len(samples) == EXPECTED_ROWS
    labels = {s.label for s in samples}
    assert len(labels) == EXPECTED_CROPS
    assert {"rice", "maize", "coffee", "muskmelon"} <= labels


def test_each_sample_reuses_soiltest_and_exposes_seven_features(samples):
    sample = samples[0]
    assert isinstance(sample.soil, SoilTest)
    feats = sample.features()
    assert len(feats) == len(FEATURE_NAMES) == 7
    # features() order must match FEATURE_NAMES and the underlying SoilTest.
    assert feats[0] == sample.soil.n_kg_ha
    assert feats[1] == sample.soil.p_kg_ha
    assert feats[2] == sample.soil.k_kg_ha
    assert feats[3] == sample.temperature_c
    assert feats[5] == sample.ph


def test_dataset_values_are_in_plausible_agronomic_ranges(samples):
    # Bounds true of this real dataset (humidity tops out a hair above 100 — the
    # mild measurement noise of genuine field data) yet tight enough to catch a
    # corrupted or mis-parsed vendoring.
    for sample in samples:
        assert sample.soil.n_kg_ha >= 0
        assert sample.soil.p_kg_ha >= 0
        assert sample.soil.k_kg_ha >= 0
        assert 0 < sample.humidity_pct < 110
        assert 0 < sample.ph < 14
        assert sample.rainfall_mm >= 0
        assert -10 < sample.temperature_c < 60
        assert sample.label
    # The dataset is perfectly balanced: 100 rows for each of the 22 crops.
    counts: dict[str, int] = {}
    for sample in samples:
        counts[sample.label] = counts.get(sample.label, 0) + 1
    assert set(counts.values()) == {100}


# --------------------------------------------------------------------------- #
# The recommender beats chance and generalises.
# --------------------------------------------------------------------------- #


def test_chance_level_is_one_over_the_number_of_crops(report):
    assert report.chance == pytest.approx(1 / 22, abs=1e-6)


def test_recommender_beats_chance_on_cross_validation(report):
    # Real CV accuracy is ~0.93; 0.80 is a safe, still-meaningful floor and far
    # above the 1/22 chance baseline.
    assert report.cross_val.accuracy_mean > 0.80
    assert report.cross_val.macro_f1_mean > 0.80
    assert report.cross_val.accuracy_mean > 10 * report.chance


def test_recommender_beats_chance_on_holdout(report):
    assert report.holdout.test_accuracy > 0.80
    assert report.holdout.test_macro_f1 > 0.80
    assert report.holdout.test_accuracy > 10 * report.chance


def test_cross_validation_and_holdout_agree(report):
    # Generalisation: the single held-out number is not a lucky split — it tracks
    # the 5-fold cross-validation mean closely.
    assert report.cv_holdout_agreement < 0.05


def test_model_is_well_fit_with_a_small_gap(report):
    assert report.fit_verdict == "well-fit"
    assert report.holdout.gap < OVERFIT_GAP
    assert report.holdout.gap == pytest.approx(
        report.holdout.train_accuracy - report.holdout.test_accuracy
    )


def test_shuffled_label_control_collapses_to_chance(report):
    # With the labels permuted there is no signal left to learn, so the pipeline
    # can do no better than guessing. A high score here would flag leakage.
    assert report.shuffled_accuracy < 3 * report.chance
    assert report.shuffled_accuracy < report.holdout.test_accuracy / 5


# --------------------------------------------------------------------------- #
# The fit classifier: each verdict is reachable and tested directly.
# --------------------------------------------------------------------------- #


def test_classify_fit_flags_overfit():
    chance = 1 / 22
    scores = HoldoutScores(train_accuracy=0.99, test_accuracy=0.60, test_macro_f1=0.60)
    assert scores.gap > OVERFIT_GAP
    assert classify_fit(scores, chance) == "overfit"


def test_classify_fit_flags_underfit():
    chance = 1 / 22
    scores = HoldoutScores(train_accuracy=0.15, test_accuracy=0.12, test_macro_f1=0.10)
    assert scores.gap <= OVERFIT_GAP
    assert classify_fit(scores, chance) == "underfit"


def test_classify_fit_accepts_well_fit():
    chance = 1 / 22
    scores = HoldoutScores(train_accuracy=0.94, test_accuracy=0.93, test_macro_f1=0.93)
    assert classify_fit(scores, chance) == "well-fit"


# --------------------------------------------------------------------------- #
# The recommender's prediction API.
# --------------------------------------------------------------------------- #


def test_recommender_trains_and_predicts_valid_crops(samples):
    recommender = CropRecommender.train(samples)
    assert len(recommender.crops) == 22
    # A rice-like observation: high rainfall, warm, humid, mildly acidic soil.
    probe = AgroSample(
        soil=SoilTest(n_kg_ha=82.0, p_kg_ha=50.0, k_kg_ha=48.0),
        temperature_c=22.0,
        humidity_pct=84.0,
        ph=5.8,
        rainfall_mm=198.0,
        label="?",
    )
    pick = recommender.recommend(probe)
    assert pick in recommender.crops

    ranked = recommender.ranked(probe, k=3)
    assert len(ranked) == 3
    assert ranked[0][0] == pick  # the top-ranked crop is the prediction
    probabilities = [p for _, p in ranked]
    assert probabilities == sorted(probabilities, reverse=True)
    assert all(0.0 <= p <= 1.0 for p in probabilities)


def test_recommend_many_matches_single_recommend(samples):
    recommender = CropRecommender.train(samples)
    subset = samples[:5]
    assert recommender.recommend_many(subset) == [recommender.recommend(s) for s in subset]


# --------------------------------------------------------------------------- #
# Report assembly and the module entry point.
# --------------------------------------------------------------------------- #


def test_report_holds_consistent_numbers(report):
    assert report.n_samples == 2200
    assert report.n_classes == 22


def test_format_report_includes_the_headline_metrics(report):
    text = format_report(report)
    assert "cross-validation" in text
    assert "train-test gap" in text
    assert "Shuffled-label control" in text
    assert f"{report.cross_val.accuracy_mean:.4f}" in text
    assert report.fit_verdict.upper() in text


def test_main_prints_report_and_returns_zero(monkeypatch, samples, report, capsys):
    import agroadvisor.real_benchmark as rb

    monkeypatch.setattr(rb, "load_samples", lambda: samples)
    monkeypatch.setattr(rb, "evaluate", lambda loaded: report)
    assert rb.main() == 0
    out = capsys.readouterr().out
    assert "real-data benchmark" in out
    assert report.fit_verdict.upper() in out


# --------------------------------------------------------------------------- #
# Vendoring: write/load roundtrip and the fetch path (monkeypatched urlopen).
# --------------------------------------------------------------------------- #


def test_write_and_load_roundtrip(tmp_path):
    sample = AgroSample(
        soil=SoilTest(n_kg_ha=10.0, p_kg_ha=20.0, k_kg_ha=30.0),
        temperature_c=21.5,
        humidity_pct=55.0,
        ph=6.2,
        rainfall_mm=120.0,
        label="rice",
    )
    path = tmp_path / "mini.jsonl"
    write_jsonl([sample.to_row()], path)
    loaded = load_samples(path)
    assert loaded == [sample]


def test_load_samples_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="python -m agroadvisor.real_data"):
        load_samples(tmp_path / "does-not-exist.jsonl")


def _row(label: str, value: float) -> dict:
    return {
        "N": value,
        "P": value,
        "K": value,
        "temperature": 20.0,
        "humidity": 60.0,
        "ph": 6.5,
        "rainfall": 100.0,
        "label": label,
    }


class _FakeUrlopen:
    """Stand-in for ``urllib.request.urlopen`` serving canned pages, failing first."""

    def __init__(self, pages: dict[int, dict], fail_first: int = 0) -> None:
        self.pages = pages
        self.fail_first = fail_first
        self.calls = 0

    def __call__(self, request, timeout=None):
        self.calls += 1
        if self.calls <= self.fail_first:
            raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", {}, None)
        offset = int(parse_qs(urlparse(request.full_url).query)["offset"][0])
        return io.BytesIO(json.dumps(self.pages[offset]).encode("utf-8"))


def test_open_refuses_non_https_urls():
    # The HTTPS-only guard is a security control: it must reject other schemes
    # before any network call is attempted.
    for bad in ("http://example.com/x", "file:///etc/passwd", "ftp://host/x"):
        with pytest.raises(ValueError, match="non-HTTPS"):
            real_data._open(bad, timeout=1.0)


def test_fetch_rows_pages_through_and_retries(monkeypatch):
    pages = {
        0: {"num_rows_total": 4, "rows": [{"row": _row("rice", 1)}, {"row": _row("maize", 2)}]},
        2: {"num_rows_total": 4, "rows": [{"row": _row("wheat", 3)}, {"row": _row("coffee", 4)}]},
    }
    fake = _FakeUrlopen(pages, fail_first=1)
    monkeypatch.setattr(real_data.urllib.request, "urlopen", fake)
    slept: list[float] = []

    rows = fetch_rows(page=2, base_delay=1.0, sleep=slept.append)

    assert [r["label"] for r in rows] == ["rice", "maize", "wheat", "coffee"]
    assert fake.calls == 3  # one 429 retry, then two successful pages
    assert slept == [1.0]  # backoff slept exactly once, after the 429


def test_regenerate_fetches_and_vendors(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        real_data, "fetch_rows", lambda: [_row("rice", 1), _row("maize", 2), _row("rice", 3)]
    )
    path = tmp_path / "vendored.jsonl"
    assert real_data.regenerate(path) == 0
    assert path.exists()
    loaded = load_samples(path)
    assert [s.label for s in loaded] == ["rice", "maize", "rice"]
    out = capsys.readouterr().out
    assert "fetched 3 rows (2 crops)" in out


def test_fetch_rows_gives_up_after_exhausting_retries(monkeypatch):
    class _AlwaysFail:
        def __call__(self, request, timeout=None):
            raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(real_data.urllib.request, "urlopen", _AlwaysFail())
    with pytest.raises(RuntimeError, match="failed to fetch rows"):
        fetch_rows(page=2, retries=3, base_delay=0.1, sleep=lambda _delay: None)
