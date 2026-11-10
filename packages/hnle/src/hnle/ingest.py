"""CSV ingest, hashtag cleaning and pseudonymisation.

The engine never sees raw user identifiers: IDs are HMAC-SHA256 hashed with an
org-specific salt before any grouping happens, and columns that look like raw
PII (phone, national id, email, nickname) are rejected outright.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd
import yaml  # type: ignore[import-untyped]

from hnle.graph import Hypergraph, canonical_node_order, normalize_weights

TAG_RE = re.compile(r"#([\w\u4e00-\u9fff]+)")
TAG_VALID_RE = re.compile(r"[0-9a-z_\u4e00-\u9fff]+")
PII_COLUMN_PATTERNS = (
    r"(phone|mobile|手机号|手机|telephone|\btel\b)",
    r"(id_?card|national_?id|身份证|ssn)",
    r"(e?mail|邮箱|邮件)",
    r"(nickname|昵称|real_?name|真实姓名|display_name)",
)
CONTENT_COLUMN_PATTERNS = (r"(content|正文|body|message|text)",)
DEFAULT_STOPWORDS = frozenset({"nan", "none", "null", "user", "via", "rt", "hashtag"})
UNMAPPED_POLICIES = frozenset({"drop", "to_negative", "to_positive", "exclude_user"})


class IngestError(ValueError):
    """Structured ingest failure with a stable machine-readable code."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


@dataclass(frozen=True)
class IngestConfig:
    user_column: str = "user"
    hashtags_column: str = "hashtags"
    sentiment_column: str | None = "sentiment"
    engagement_column: str | None = "engagement"
    min_size: int = 2
    max_size: int = 200
    allow_content: bool = False
    stopwords: frozenset[str] = DEFAULT_STOPWORDS
    mapping_path: Path | None = None
    unmapped_policy: str = "drop"


@dataclass
class IngestResult:
    graph: Hypergraph
    weights: npt.NDArray[np.float64]
    stats: dict[str, Any]
    warnings: list[str] = field(default_factory=list)


def derive_org_salt(root_key: bytes, org_id: str) -> bytes:
    """Derive a per-org salt so hashes cannot be correlated across tenants."""
    return hmac.new(root_key, org_id.encode("utf-8"), hashlib.sha256).digest()


def pseudonymize(raw_id: str, salt: bytes) -> str:
    """HMAC-SHA256 of a raw id; the raw value is never stored."""
    return hmac.new(salt, raw_id.encode("utf-8"), hashlib.sha256).hexdigest()


def load_sentiment_mapping(path: str | Path) -> dict[str, int]:
    """Load and lower-case the sentiment -> opinion mapping YAML."""
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    labels = payload.get("labels", {})
    if not isinstance(labels, dict):
        raise IngestError("MAPPING_INVALID", "sentiment mapping must contain a labels mapping")
    return {str(key).strip().lower(): int(value) for key, value in labels.items()}


def parse_hashtags(value: str, stopwords: frozenset[str] = DEFAULT_STOPWORDS) -> list[str]:
    """Normalise a hashtag cell: extract, lower-case, de-duplicate, filter noise."""
    text = str(value).strip().lower()
    if not text or text in stopwords:
        return []
    tags = TAG_RE.findall(text)
    if not tags:
        parts = [part.lstrip("#") for part in re.split(r"[,\s]+", text) if part]
        tags = parts
    seen: list[str] = []
    for tag in tags:
        candidate = tag.strip().lower()
        if not candidate or candidate in stopwords or candidate.isdigit():
            continue
        if not TAG_VALID_RE.fullmatch(candidate):
            continue
        if candidate not in seen:
            seen.append(candidate)
    return seen


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IngestError(
            "ENCODING_ERROR", "input must be valid UTF-8", {"reason": str(exc)}
        ) from exc


def _check_columns(df: pd.DataFrame, config: IngestConfig) -> None:
    required = {config.user_column, config.hashtags_column}
    missing = sorted(required - set(df.columns))
    if missing:
        raise IngestError(
            "MISSING_COLUMN",
            f"missing required columns: {missing}",
            {"missing": missing},
        )
    for column in df.columns:
        lowered = str(column).lower()
        if column == config.user_column:
            continue  # the id column itself is pseudonymised, not persisted
        if any(re.search(pattern, lowered) for pattern in PII_COLUMN_PATTERNS):
            raise IngestError(
                "PII_COLUMN_REJECTED",
                f"column {column!r} looks like raw personal data",
                {"column": column},
            )
        if not config.allow_content and any(
            re.search(pattern, lowered) for pattern in CONTENT_COLUMN_PATTERNS
        ):
            raise IngestError(
                "CONTENT_COLUMN_REJECTED",
                f"column {column!r} looks like post content",
                {"column": column},
            )


def _mapping_for(config: IngestConfig) -> dict[str, int]:
    if config.mapping_path is None:
        return {}
    return load_sentiment_mapping(config.mapping_path)


def ingest_dataframe(
    df: pd.DataFrame,
    *,
    salt: bytes,
    config: IngestConfig | None = None,
) -> IngestResult:
    """Build a deterministic hypergraph from an in-memory dataframe."""
    cfg = config or IngestConfig()
    if cfg.unmapped_policy not in UNMAPPED_POLICIES:
        raise IngestError("UNMAPPED_POLICY", f"unknown unmapped policy {cfg.unmapped_policy!r}")
    _check_columns(df, cfg)
    if df.empty:
        raise IngestError("EMPTY_DATASET", "no rows to ingest")

    working = df.copy()
    raw_users = working[cfg.user_column].astype(str)
    working["_pseudonym"] = [pseudonymize(value, salt) for value in raw_users]
    warnings: list[str] = []
    stats: dict[str, Any] = {"row_count": int(len(working))}

    mapping = _mapping_for(cfg)
    if cfg.sentiment_column and cfg.sentiment_column in working.columns and mapping:
        labels = working[cfg.sentiment_column].astype(str).str.strip().str.lower()
        opinions = labels.map(mapping)
        mapped_ratio = float(opinions.notna().mean())
        stats["sentiment_mapped_ratio"] = mapped_ratio
        if mapped_ratio == 0.0:
            warnings.append("sentiment_unmapped_all")
        unmapped = opinions.isna()
        if cfg.unmapped_policy == "drop":
            working = working.loc[~unmapped].copy()
            opinions = opinions.loc[~unmapped]
        elif cfg.unmapped_policy == "to_negative":
            opinions = opinions.fillna(0)
        elif cfg.unmapped_policy == "to_positive":
            opinions = opinions.fillna(1)
        else:  # exclude_user: drop every row of a user with any unmapped label
            bad_users = set(working.loc[unmapped, "_pseudonym"])
            keep = ~working["_pseudonym"].isin(bad_users)
            working = working.loc[keep].copy()
            opinions = opinions.loc[keep]
        working["_opinion"] = opinions.astype("int64")
        if working.empty:
            raise IngestError("EMPTY_DATASET", "no rows left after sentiment mapping")
    else:
        stats["sentiment_mapped_ratio"] = None

    tag_members: dict[str, set[str]] = {}
    for pseudonym, raw_tags in zip(
        working["_pseudonym"], working[cfg.hashtags_column], strict=False
    ):
        for tag in parse_hashtags(raw_tags, cfg.stopwords):
            tag_members.setdefault(tag, set()).add(pseudonym)

    oversized = 0
    edges: list[tuple[str, ...]] = []
    for tag in sorted(tag_members):
        members = sorted(tag_members[tag])
        if len(members) > cfg.max_size:
            oversized += 1
            continue
        if len(members) < cfg.min_size:
            continue
        edges.append(tuple(members))

    nodes = canonical_node_order(working["_pseudonym"].astype(str).tolist())
    index = {node: position for position, node in enumerate(nodes)}
    numeric_edges = tuple(tuple(index[member] for member in edge) for edge in edges)

    opinions_array: list[int] = []
    if "_opinion" in working.columns:
        node_opinions: dict[str, int] = {}
        for pseudonym, opinion in zip(working["_pseudonym"], working["_opinion"], strict=False):
            node_opinions.setdefault(str(pseudonym), int(opinion))
        opinions_array = [node_opinions.get(node, 0) for node in nodes]

    if cfg.engagement_column and cfg.engagement_column in working.columns:
        engagement = pd.to_numeric(working[cfg.engagement_column], errors="coerce").fillna(0.0)
        per_node = (
            pd.DataFrame({"node": working["_pseudonym"].astype(str), "engagement": engagement})
            .groupby("node", sort=True)["engagement"]
            .max()
        )
        raw_weights = np.asarray(
            [float(per_node.get(node, 0.0)) for node in nodes], dtype=np.float64
        )
    else:
        raw_weights = np.ones(len(nodes), dtype=np.float64)

    weights, weight_warnings = normalize_weights(raw_weights)
    warnings.extend(weight_warnings.keys())
    stats.update(
        {
            "node_count": len(nodes),
            "edge_count": len(numeric_edges),
            "oversized_edges_dropped": oversized,
            "sentiment_label_count": len(mapping),
        }
    )

    graph = Hypergraph(
        n_nodes=len(nodes),
        hyperedges=numeric_edges,
        initial_opinions=tuple(opinions_array) if opinions_array else None,
    )
    return IngestResult(graph=graph, weights=weights, stats=stats, warnings=warnings)


def ingest_csv(
    path: str | Path, *, salt: bytes, config: IngestConfig | None = None
) -> IngestResult:
    """Read a UTF-8 CSV file and ingest it deterministically."""
    raw = Path(path).read_bytes()
    text = _decode(raw)
    frame = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    return ingest_dataframe(frame, salt=salt, config=config)
