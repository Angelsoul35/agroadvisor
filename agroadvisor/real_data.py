"""Real agronomic data: the public Crop-recommendation dataset (2200 rows).

This module fetches and loads a real, public dataset so the learned crop
recommender (:mod:`agroadvisor.recommender`) can be trained and benchmarked on
genuine field measurements rather than synthetic numbers. Each row is one
observation of a plot — its soil macronutrients, climate and acidity — paired
with the crop that is known to suit it.

Source
------
``randalakab/Crop-recommendation`` on the Hugging Face Hub, a mirror of the
classic, widely redistributed Crop Recommendation dataset. Schema (all features
``float64``):

====================  ==========================================================
feature               meaning
====================  ==========================================================
``N`` / ``P`` / ``K`` soil macronutrients (reused as the engine's ``SoilTest``)
``temperature``       air temperature (degrees Celsius)
``humidity``          relative humidity (percent)
``ph``                soil pH
``rainfall``          rainfall (millimetres)
``label``             the recommended crop (one of 22 crops), the target
====================  ==========================================================

The rows are read through the Hugging Face datasets-server rows API, which needs
no authentication. The endpoint rate-limits with HTTP 429, so every request is
retried with exponential backoff. The downloaded rows are vendored under
``datasets/`` (see ``datasets/README.md``); loaders read that local copy.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .engine import SoilTest

#: Hugging Face dataset identifier.
DATASET = "randalakab/Crop-recommendation"

#: datasets-server rows endpoint; ``offset``/``length`` select a page of rows.
ROWS_URL = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=randalakab%2FCrop-recommendation&config=default&split=train"
    "&offset={offset}&length={length}"
)

#: The seven feature columns, in the fixed order the model consumes them.
FEATURE_NAMES: tuple[str, ...] = ("N", "P", "K", "temperature", "humidity", "ph", "rainfall")

#: What a correct vendored copy must contain; asserted by the test suite.
EXPECTED_ROWS = 2200
EXPECTED_CROPS = 22

#: Largest page the datasets-server rows API serves in one request.
MAX_PAGE = 100

_REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = _REPO_ROOT / "datasets"
DEFAULT_PATH = DATA_DIR / "crop_recommendation.jsonl"

_USER_AGENT = "agroadvisor-benchmark/1.0 (+https://github.com/Angelsoul35/agroadvisor)"


@dataclass(frozen=True)
class AgroSample:
    """One real field observation: seven agronomic features and the crop that suits it.

    The three soil macronutrients reuse the engine's :class:`~agroadvisor.engine.SoilTest`
    (kg/ha); ``temperature_c``, ``humidity_pct`` and ``rainfall_mm`` share the names and
    units of the engine's :class:`~agroadvisor.engine.Weather`; ``ph`` is the soil
    acidity. ``label`` is the ground-truth recommended crop for these conditions — the
    target the learned recommender predicts.
    """

    soil: SoilTest
    temperature_c: float
    humidity_pct: float
    ph: float
    rainfall_mm: float
    label: str

    def features(self) -> list[float]:
        """The seven feature values in the fixed order of :data:`FEATURE_NAMES`."""
        return [
            self.soil.n_kg_ha,
            self.soil.p_kg_ha,
            self.soil.k_kg_ha,
            self.temperature_c,
            self.humidity_pct,
            self.ph,
            self.rainfall_mm,
        ]

    @classmethod
    def from_row(cls, row: dict) -> AgroSample:
        """Build a sample from one raw dataset row (the API's / vendored JSON shape)."""
        return cls(
            soil=SoilTest(
                n_kg_ha=float(row["N"]),
                p_kg_ha=float(row["P"]),
                k_kg_ha=float(row["K"]),
            ),
            temperature_c=float(row["temperature"]),
            humidity_pct=float(row["humidity"]),
            ph=float(row["ph"]),
            rainfall_mm=float(row["rainfall"]),
            label=str(row["label"]),
        )

    def to_row(self) -> dict:
        """Serialise back to the raw dataset row shape (for vendoring)."""
        return {
            "N": self.soil.n_kg_ha,
            "P": self.soil.p_kg_ha,
            "K": self.soil.k_kg_ha,
            "temperature": self.temperature_c,
            "humidity": self.humidity_pct,
            "ph": self.ph,
            "rainfall": self.rainfall_mm,
            "label": self.label,
        }


def _open(url: str, *, timeout: float):
    """Open one URL through the standard library with a descriptive User-Agent.

    The scheme is restricted to HTTPS before opening — the exact concern behind
    Bandit's B310 / CWE-22 check (``file:`` or custom schemes are refused) — so the
    targeted suppression on the call below is a reviewed, documented decision.
    """
    if not url.lower().startswith("https://"):
        raise ValueError(f"refusing to open a non-HTTPS URL: {url!r}")
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    return urllib.request.urlopen(request, timeout=timeout)  # nosec B310


def _fetch_page(
    offset: int,
    length: int,
    *,
    retries: int,
    base_delay: float,
    timeout: float,
    sleep: Callable[[float], None],
) -> dict:
    """Fetch one page of rows, retrying transient failures with exponential backoff."""
    url = ROWS_URL.format(offset=offset, length=length)
    delay = base_delay
    last: Exception | None = None
    for _ in range(retries):
        try:
            with _open(url, timeout=timeout) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last = exc
            sleep(delay)
            delay *= 2
    raise RuntimeError(f"failed to fetch rows at offset {offset} after {retries} tries: {last}")


def fetch_rows(
    *,
    page: int = MAX_PAGE,
    retries: int = 6,
    base_delay: float = 2.0,
    timeout: float = 90.0,
    sleep: Callable[[float], None] = time.sleep,
) -> list[dict]:
    """Download every row of the dataset, paging through the rows API.

    Pages of ``page`` rows are requested in turn until the server's reported
    ``num_rows_total`` is reached. Each page is retried up to ``retries`` times
    with exponential backoff starting at ``base_delay`` seconds, because the public
    endpoint rate-limits with HTTP 429. ``sleep`` is injectable so tests drive the
    retry path without waiting. Returns the raw row dicts.
    """
    rows: list[dict] = []
    offset = 0
    total: int | None = None
    while total is None or offset < total:
        payload = _fetch_page(
            offset,
            page,
            retries=retries,
            base_delay=base_delay,
            timeout=timeout,
            sleep=sleep,
        )
        total = int(payload["num_rows_total"])
        rows.extend(item["row"] for item in payload["rows"])
        offset += page
    return rows


def write_jsonl(rows: list[dict], path: Path | str = DEFAULT_PATH) -> Path:
    """Vendor raw rows as one JSON object per line (stable key order for clean diffs)."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return out


def load_samples(path: Path | str = DEFAULT_PATH) -> list[AgroSample]:
    """Load the vendored dataset into :class:`AgroSample` objects.

    Reads the local copy only; it never touches the network. Raises
    :class:`FileNotFoundError` with a hint if the vendored file is missing.
    """
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(
            f"dataset not found at {source}; regenerate it with "
            f"`python -m agroadvisor.real_data`"
        )
    with source.open(encoding="utf-8") as handle:
        return [AgroSample.from_row(json.loads(line)) for line in handle if line.strip()]


def regenerate(path: Path | str = DEFAULT_PATH) -> int:
    """Fetch the dataset from Hugging Face and vendor it locally. Prints a summary."""
    rows = fetch_rows()
    out = write_jsonl(rows, path)
    crops = sorted({str(row["label"]) for row in rows})
    print(f"fetched {len(rows)} rows ({len(crops)} crops) -> {out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(regenerate())
