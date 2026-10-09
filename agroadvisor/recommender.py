"""A learned crop recommender: given soil and climate, which crop suits this plot.

The deterministic engine (:mod:`agroadvisor.engine`) answers the question "given
*this* crop, how should I manage it" — irrigation, fertiliser, pest risk. This
module answers the upstream question "*which* crop should I plant here" from seven
agronomic measurements, using a supervised classifier trained on real field data
(:mod:`agroadvisor.real_data`).

The two sit side by side and compose: recommend a crop, then hand it to the
engine for a management plan. The recommender adds a learned capability without
changing a single line of the engine's audited arithmetic.

The estimator is a multinomial logistic regression over standardised features.
That choice is deliberate for a portfolio piece: it is interpretable (one weight
per feature per crop), well-calibrated for probabilities, and — unlike a tree
ensemble that can memorise its training set and report a perfect training score —
it exposes a genuine, readable train/test gap, which is what
:mod:`agroadvisor.real_benchmark` uses to demonstrate that the model generalises.
"""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from .real_data import AgroSample

#: Fixed seed so every training run of the recommender is reproducible.
RANDOM_STATE = 0


def build_model() -> Pipeline:
    """Build the (untrained) recommender estimator.

    Standardisation puts the seven features — which span very different scales,
    from pH near 6 to rainfall near 200 mm — onto a common footing before the
    logistic regression, so no feature dominates by unit alone.
    """
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=2000, C=1.0, random_state=RANDOM_STATE),
    )


@dataclass
class CropRecommender:
    """A trained crop recommender over :class:`~agroadvisor.real_data.AgroSample`."""

    model: Pipeline

    @classmethod
    def train(cls, samples: list[AgroSample]) -> CropRecommender:
        """Fit the estimator on labelled samples and return a ready recommender."""
        model = build_model()
        model.fit([s.features() for s in samples], [s.label for s in samples])
        return cls(model=model)

    @property
    def crops(self) -> list[str]:
        """The crops the recommender can choose between, sorted."""
        return sorted(str(c) for c in self.model.classes_)

    def recommend(self, sample: AgroSample) -> str:
        """The single best-suited crop for one observation."""
        return str(self.model.predict([sample.features()])[0])

    def recommend_many(self, samples: list[AgroSample]) -> list[str]:
        """Best-suited crop for each observation, in order."""
        return [str(label) for label in self.model.predict([s.features() for s in samples])]

    def ranked(self, sample: AgroSample, k: int = 3) -> list[tuple[str, float]]:
        """The top-``k`` crops with their predicted probabilities, most likely first."""
        proba = self.model.predict_proba([sample.features()])[0]
        classes = self.model.classes_
        order = sorted(range(len(classes)), key=lambda i: proba[i], reverse=True)
        return [(str(classes[i]), float(proba[i])) for i in order[:k]]
