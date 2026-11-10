"""US-011: deterministic ingest, hashtag cleaning, sentiment mapping and PII."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hnle.core.sparse import run_sparse
from hnle.ingest import (
    IngestConfig,
    IngestError,
    IngestResult,
    derive_org_salt,
    ingest_csv,
    ingest_dataframe,
    parse_hashtags,
    pseudonymize,
)
from hnle.spec import ModelSpec

SALT = b"test-salt"
MAPPING = Path(__file__).parents[1] / "scenarios" / "mappings" / "sentiment_multi.yaml"


def _csv(tmp_path: Path, rows: list[dict[str, str]], name: str = "data.csv") -> Path:
    frame = pd.DataFrame(rows)
    path = tmp_path / name
    frame.to_csv(path, index=False)
    return path


def _rows(count: int, label: str = "joy") -> list[dict[str, str]]:
    return [
        {"user": f"user{i}", "hashtags": f"#tag{i % 5}", "sentiment": label, "engagement": "1"}
        for i in range(count)
    ]


def test_repeated_parsing_is_bitwise_deterministic(tmp_path: Path) -> None:
    path = _csv(tmp_path, _rows(50))
    first = ingest_csv(path, salt=SALT, config=IngestConfig(mapping_path=MAPPING))
    for _ in range(19):
        again = ingest_csv(path, salt=SALT, config=IngestConfig(mapping_path=MAPPING))
        assert again.graph.hyperedges == first.graph.hyperedges
        assert again.graph.initial_opinions == first.graph.initial_opinions
        np.testing.assert_array_equal(again.weights, first.weights)


def test_data_driven_initial_share_matches_positive_ratio(tmp_path: Path) -> None:
    rows = [
        {"user": f"u{i}", "hashtags": f"#t{i % 3}", "sentiment": "joy" if i < 6 else "anger"}
        for i in range(10)
    ]
    result = ingest_csv(_csv(tmp_path, rows), salt=SALT, config=IngestConfig(mapping_path=MAPPING))
    assert result.graph.initial_opinions is not None
    share_one = np.mean(result.graph.initial_opinions)
    np.testing.assert_allclose(share_one, 0.6, atol=1e-9)

    spec = ModelSpec(n_steps=1, init_mode="data_driven", latency={"dist": "const", "mu": 100})
    run = run_sparse(spec, result.graph, seed=3)
    np.testing.assert_allclose(np.mean(run.opinions), 0.6, atol=1e-9)


@pytest.mark.parametrize(
    "column", ["email", "phone", "mobile", "id_card", "nickname", "身份证", "邮箱"]
)
def test_pii_columns_are_rejected(column: str, tmp_path: Path) -> None:
    path = _csv(
        tmp_path,
        [{"user": "u1", "hashtags": "#a", "sentiment": "joy", column: "secret"}],
    )
    with pytest.raises(IngestError) as exc:
        ingest_csv(path, salt=SALT, config=IngestConfig(mapping_path=MAPPING))
    assert exc.value.code == "PII_COLUMN_REJECTED"


def test_content_column_rejected_by_default(tmp_path: Path) -> None:
    path = _csv(tmp_path, [{"user": "u1", "hashtags": "#a", "content": "hello"}])
    with pytest.raises(IngestError) as exc:
        ingest_csv(path, salt=SALT)
    assert exc.value.code == "CONTENT_COLUMN_REJECTED"


def test_missing_column_reports_names(tmp_path: Path) -> None:
    path = _csv(tmp_path, [{"user": "u1"}])
    with pytest.raises(IngestError) as exc:
        ingest_csv(path, salt=SALT)
    assert exc.value.code == "MISSING_COLUMN"
    assert "hashtags" in exc.value.details["missing"]


def test_non_utf8_file_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_bytes(b"user,hashtags,sentiment\n\xff\xfe,#a,joy\n")
    with pytest.raises(IngestError) as exc:
        ingest_csv(path, salt=SALT, config=IngestConfig(mapping_path=MAPPING))
    assert exc.value.code == "ENCODING_ERROR"


def test_hashtag_cleaning_filters_noise_and_dedupes() -> None:
    tags = parse_hashtags("#Policy #policy #政策 @user nan 123 #A#B", frozenset({"nan"}))
    assert tags == ["policy", "政策", "a", "b"]


def test_oversized_edges_are_dropped_and_counted(tmp_path: Path) -> None:
    rows = [
        {"user": f"u{i}", "hashtags": "#huge", "sentiment": "joy"} for i in range(5000)
    ]
    result = ingest_csv(
        _csv(tmp_path, rows, "huge.csv"),
        salt=SALT,
        config=IngestConfig(mapping_path=MAPPING, max_size=200),
    )
    assert result.stats["oversized_edges_dropped"] == 1
    assert result.stats["edge_count"] == 0
    assert result.graph.hyperedges == ()


def test_all_zero_engagement_falls_back_to_uniform(tmp_path: Path) -> None:
    rows = _rows(6)
    for row in rows:
        row["engagement"] = "0"
    result = ingest_csv(_csv(tmp_path, rows), salt=SALT, config=IngestConfig(mapping_path=MAPPING))
    assert "engagement_all_zero" in result.warnings
    np.testing.assert_array_equal(result.weights, np.ones(6))
    assert result.weights.max() == 1.0


def test_unmapped_policies(tmp_path: Path) -> None:
    mapping = tmp_path / "mapping.yaml"
    mapping.write_text("labels:\n  joy: 1\n", encoding="utf-8")
    rows = [
        {"user": "u1", "hashtags": "#a", "sentiment": "joy"},
        {"user": "u2", "hashtags": "#a", "sentiment": "mystery"},
    ]

    drop = ingest_csv(
        _csv(tmp_path, rows), salt=SALT,
        config=IngestConfig(mapping_path=mapping, unmapped_policy="drop"),
    )
    assert drop.graph.n_nodes == 1

    to_negative = ingest_csv(
        _csv(tmp_path, rows), salt=SALT,
        config=IngestConfig(mapping_path=mapping, unmapped_policy="to_negative"),
    )
    assert set(to_negative.graph.initial_opinions or ()) == {0, 1}

    excluded = ingest_csv(
        _csv(tmp_path, rows), salt=SALT,
        config=IngestConfig(mapping_path=mapping, unmapped_policy="exclude_user"),
    )
    assert excluded.graph.n_nodes == 1


def test_pseudonymisation_is_stable_and_salt_scoped() -> None:
    salt_a, salt_b = derive_org_salt(b"root", "org-a"), derive_org_salt(b"root", "org-b")
    hashed = pseudonymize("alice", salt_a)
    assert hashed == pseudonymize("alice", salt_a)
    assert hashed != pseudonymize("alice", salt_b)
    assert "alice" not in hashed
    assert len(hashed) == 64


def test_dataframe_api_and_empty_input(tmp_path: Path) -> None:
    frame = pd.DataFrame(_rows(5))
    result: IngestResult = ingest_dataframe(
        frame, salt=SALT, config=IngestConfig(mapping_path=MAPPING)
    )
    assert result.graph.n_nodes == 5
    with pytest.raises(IngestError) as exc:
        ingest_dataframe(frame.iloc[0:0], salt=SALT, config=IngestConfig(mapping_path=MAPPING))
    assert exc.value.code == "EMPTY_DATASET"
