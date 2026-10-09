# Vendored real dataset

This directory holds the real, public dataset that the learned crop recommender
(`agroadvisor/recommender.py`) is trained and benchmarked on. It is vendored so
the benchmark and its tests are reproducible offline and never depend on a live
network call.

## `crop_recommendation.jsonl`

2200 real field observations, one JSON object per line. Each row carries the
seven agronomic features and the ground-truth recommended crop:

| field          | meaning                                  | unit  |
| -------------- | ---------------------------------------- | ----- |
| `N`            | soil nitrogen                            | kg/ha |
| `P`            | soil phosphorus                          | kg/ha |
| `K`            | soil potassium                           | kg/ha |
| `temperature`  | air temperature                          | °C    |
| `humidity`     | relative humidity                        | %     |
| `ph`           | soil pH                                  | —     |
| `rainfall`     | rainfall                                 | mm    |
| `label`        | recommended crop (one of 22, the target) | —     |

The 22 crops are: apple, banana, blackgram, chickpea, coconut, coffee, cotton,
grapes, jute, kidneybeans, lentil, maize, mango, mothbeans, mungbean, muskmelon,
orange, papaya, pigeonpeas, pomegranate, rice, watermelon — 100 rows each.

## Source and provenance

- **Dataset:** [`randalakab/Crop-recommendation`](https://huggingface.co/datasets/randalakab/Crop-recommendation)
  on the Hugging Face Hub.
- **Origin:** a mirror of the classic, widely redistributed Crop Recommendation
  dataset, a standard public benchmark for soil-and-climate crop selection.
- **Access:** fetched through the Hugging Face datasets-server rows API, which
  needs no authentication:
  `https://datasets-server.huggingface.co/rows?dataset=randalakab%2FCrop-recommendation&config=default&split=train&offset=N&length=100`
- **Fetched:** 2026-10-09.

## License note

The dataset is published on the Hugging Face Hub for public, research and
educational use. Consult the dataset card for the authoritative license and
attribution terms before any redistribution beyond this reference project. This
project vendors the data solely to make its benchmark reproducible.

## How to regenerate

From the repository root, with the package installed (`pip install -e ".[dev]"`):

```bash
python -m agroadvisor.real_data
```

This calls `agroadvisor.real_data.fetch_rows` (standard-library `urllib`, with
exponential-backoff retries for the endpoint's HTTP 429 rate limiting), pages
through all 2200 rows, and rewrites `crop_recommendation.jsonl` with stable key
ordering so diffs stay clean.
