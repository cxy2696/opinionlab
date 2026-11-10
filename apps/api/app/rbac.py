"""PRD 9.1 permission matrix: 6 roles x features x data scope."""

from __future__ import annotations

from enum import StrEnum


class Scope(StrEnum):
    ORG = "org"
    OWN = "own"
    SHARED = "shared"
    SUMMARY = "summary"
    DENIED = "denied"


FEATURES = (
    "view_runs",
    "upload_dataset",
    "manage_scenario",
    "submit_run",
    "cancel_run",
    "export_parquet",
    "export_html",
    "delete_assets",
    "org_admin",
    "use_case_review",
)

MATRIX: dict[str, dict[str, Scope]] = {
    "analyst": {
        "view_runs": Scope.ORG,
        "upload_dataset": Scope.ORG,
        "manage_scenario": Scope.DENIED,
        "submit_run": Scope.DENIED,
        "cancel_run": Scope.DENIED,
        "export_parquet": Scope.DENIED,
        "export_html": Scope.ORG,
        "delete_assets": Scope.DENIED,
        "org_admin": Scope.DENIED,
        "use_case_review": Scope.DENIED,
    },
    "researcher": {
        "view_runs": Scope.ORG,
        "upload_dataset": Scope.ORG,
        "manage_scenario": Scope.OWN,
        "submit_run": Scope.ORG,
        "cancel_run": Scope.OWN,
        "export_parquet": Scope.ORG,
        "export_html": Scope.ORG,
        "delete_assets": Scope.OWN,
        "org_admin": Scope.DENIED,
        "use_case_review": Scope.DENIED,
    },
    "scenario_owner": {
        "view_runs": Scope.ORG,
        "upload_dataset": Scope.ORG,
        "manage_scenario": Scope.ORG,
        "submit_run": Scope.ORG,
        "cancel_run": Scope.ORG,
        "export_parquet": Scope.ORG,
        "export_html": Scope.ORG,
        "delete_assets": Scope.ORG,
        "org_admin": Scope.DENIED,
        "use_case_review": Scope.DENIED,
    },
    "org_admin": {
        "view_runs": Scope.ORG,
        "upload_dataset": Scope.ORG,
        "manage_scenario": Scope.ORG,
        "submit_run": Scope.ORG,
        "cancel_run": Scope.ORG,
        "export_parquet": Scope.ORG,
        "export_html": Scope.ORG,
        "delete_assets": Scope.ORG,
        "org_admin": Scope.ORG,
        "use_case_review": Scope.ORG,
    },
    "reviewer": {
        "view_runs": Scope.SHARED,
        "upload_dataset": Scope.DENIED,
        "manage_scenario": Scope.DENIED,
        "submit_run": Scope.DENIED,
        "cancel_run": Scope.DENIED,
        "export_parquet": Scope.DENIED,
        "export_html": Scope.SUMMARY,
        "delete_assets": Scope.DENIED,
        "org_admin": Scope.DENIED,
        "use_case_review": Scope.DENIED,
    },
    "platform_admin": {
        "view_runs": Scope.DENIED,
        "upload_dataset": Scope.DENIED,
        "manage_scenario": Scope.DENIED,
        "submit_run": Scope.DENIED,
        "cancel_run": Scope.DENIED,
        "export_parquet": Scope.DENIED,
        "export_html": Scope.DENIED,
        "delete_assets": Scope.DENIED,
        "org_admin": Scope.ORG,
        "use_case_review": Scope.ORG,
    },
}


def is_allowed(role: str, feature: str) -> bool:
    return MATRIX.get(role, {}).get(feature, Scope.DENIED) is not Scope.DENIED
