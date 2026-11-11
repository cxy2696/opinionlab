# Sample data: Kaggle social-media sentiment posts

`kaggle_sentiment.csv` is the 732-row *Social Media Sentiments Analysis
Dataset* published by Kashish Parmar on Kaggle under **CC0: Public Domain**
(<https://www.kaggle.com/datasets/kashishparmar02/social-media-sentiments-analysis-dataset>).

The repository copy keeps the original columns and adds one derived column,
`engagement = Retweets + Likes`. Nothing else was changed. SHA-256:

```
f08b6589e75eb0cb3828dde35edf969ccb5b16bc6e98b901e296207ee76a2783
```

The file is included because the worked case in
[`docs/CASE_STUDY.md`](../docs/CASE_STUDY.md) should be runnable without a
download. It is a convenience sample, not a representative social-media
corpus: the user identifiers are pseudonymous handles, 617 of 670 users appear
once, and the sentiment column contains 191 emotion labels rather than a stance
scale. Those limits are why the case is framed as a structural scenario, not as
a prediction about a real population.

The valence mapping in
[`scenarios/mappings/kaggle_valence.yaml`](../scenarios/mappings/kaggle_valence.yaml)
is derived from the documented lexicon in the HNL research repository. It maps
169 labels to positive or negative and leaves 22 ambiguous labels unmapped;
rows with unmapped labels are dropped by the ingest policy.
