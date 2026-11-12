# Sample data: Kaggle social-media sentiment posts

**Applies to:** OpinionLab v1.4.0 · [Docs index](../docs/README.md) ·
[Case study](../docs/CASE_STUDY.md) · [Changelog](../CHANGELOG.md)

`kaggle_sentiment.csv` is the 732-row *Social Media Sentiments Analysis
Dataset* published by Kashish Parmar on Kaggle under **CC0: Public Domain**
(<https://www.kaggle.com/datasets/kashishparmar02/social-media-sentiments-analysis-dataset>).

The repository copy keeps the original columns and adds one derived column,
`engagement = Retweets + Likes`. Nothing else was changed. SHA-256:

```text
f08b6589e75eb0cb3828dde35edf969ccb5b16bc6e98b901e296207ee76a2783
```

Verify the copy:

```bash
shasum -a 256 data/kaggle_sentiment.csv
```

## What the sample contains

| Item | Value |
|---|---:|
| posts | 732 |
| raw user handles | 670 |
| handles appearing once | 617 |
| emotion labels | 191 |
| platforms | Instagram, Twitter, Facebook |

The file is included because the worked case in
[`docs/CASE_STUDY.md`](../docs/CASE_STUDY.md) should be runnable without a
download. It is a convenience sample, not a representative social-media corpus:
the user identifiers are pseudonymous handles, 617 of 670 raw users appear once,
and the sentiment column contains emotion labels rather than a stance scale.
Those limits are why the case is framed as a structural scenario, not as a
prediction about a real population.

After ingest and valence filtering, the model graph has 586 user nodes and 149
hashtag hyperedges. The reduction from 670 to 586 is explained by the
`unmapped_policy=drop` setting: posts with a sentiment label outside the
mapping are excluded before the hypergraph is built.

## Valence mapping

The mapping in
[`scenarios/mappings/kaggle_valence.yaml`](../scenarios/mappings/kaggle_valence.yaml)
is derived from the documented lexicon in the HNL research repository. It maps
169 labels to positive or negative and leaves 22 labels unmapped; rows with
unmapped labels are dropped by the ingest policy.

The mapping is a modelling choice, not a ground truth. The case study documents
the resulting component structure and the limits of the conclusion.

## Reproduce the model graph

```bash
uv run hnle ingest \
  --csv data/kaggle_sentiment.csv \
  --org-salt opinionlab-public-case-v1 \
  --user-column User --hashtags-column Hashtags \
  --sentiment-column Sentiment --engagement-column engagement \
  --mapping scenarios/mappings/kaggle_valence.yaml \
  --allow-content \
  --out-dir runs/kaggle_case
```

For the full run, use `make case`; see
[`docs/CASE_STUDY.md`](../docs/CASE_STUDY.md) and
[`examples/README.md`](../examples/README.md).

## Licence and provenance

The dataset page is the canonical source and licence record. The repository
copy exists for reproducibility; if you redistribute it, keep the CC0
attribution and the source URL. For the product-level data rules, see
[`docs/COMPLIANCE.md`](../docs/COMPLIANCE.md) and
[`docs/MODEL_CARD.md`](../docs/MODEL_CARD.md).
