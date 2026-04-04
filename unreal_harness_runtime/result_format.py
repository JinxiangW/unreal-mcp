"""Shared result-format helpers for harness tools."""

from __future__ import annotations

from typing import Any, Dict, Optional


def build_query_summary(
    *,
    requested: int,
    returned: int,
    total: int,
    offset: int = 0,
    failed: int = 0,
    verified: Optional[int] = None,
) -> Dict[str, Any]:
    return {
        "requested": requested,
        "returned": returned,
        "total": total,
        "failed": failed,
        "verified": returned if verified is None else verified,
        "offset": offset,
    }


def structured_query_failure(
    *,
    operation_id: str,
    domain: str,
    target: str | None,
    error: str,
    summary: Dict[str, Any],
    filters: Optional[Dict[str, Any]] = None,
    post_state: Optional[Dict[str, Any]] = None,
    result: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "success": False,
        "operation_id": operation_id,
        "domain": domain,
        "targets": [target] if target else [],
        "applied_changes": [],
        "failed_changes": [
            {
                "target": target,
                "field": "query",
                "error": error,
            }
        ],
        "post_state": post_state or {},
        "verification": {"verified": False, "checks": []},
        "summary": summary,
        "items": [],
        "error": error,
    }
    if filters is not None:
        payload["filters"] = filters
    if result is not None:
        payload["result"] = result
    if extra:
        payload.update(extra)
    return payload


def structured_query_success(
    *,
    operation_id: str,
    domain: str,
    targets: list[str],
    post_state: Dict[str, Any],
    summary: Dict[str, Any],
    items: list[Dict[str, Any]],
    filters: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "success": True,
        "operation_id": operation_id,
        "domain": domain,
        "targets": targets,
        "applied_changes": [],
        "failed_changes": [],
        "post_state": post_state,
        "verification": {"verified": True, "checks": []},
        "summary": summary,
        "items": items,
    }
    if filters is not None:
        payload["filters"] = filters
    if extra:
        payload.update(extra)
    return payload
