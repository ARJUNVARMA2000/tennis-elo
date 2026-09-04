"""Translate accepted-release inspection into stable output findings."""

from __future__ import annotations

from .common import HealthFinding


def lineage_observation(output_root, tours, *, require_accepted: bool) -> tuple[dict, dict[str, list[HealthFinding]]]:
    """Inspect the whole release once and translate issues into blocking typed findings.

    The pre-deploy gate calls this with ``require_accepted=False`` because acceptance is
    written only after that gate succeeds. Authoritative health requires the private
    receipt. Raw parser/IO detail remains private; the public contract carries only a
    stable reason, safe relative artifact path, and state. Global release issues are
    attached to both tours because one shared manifest owns both payloads.
    """
    from ...artifact_lineage import AcceptedRelease, inspect_release

    state = inspect_release(
        output_root,
        require_accepted=require_accepted,
    )
    accepted = state.release if isinstance(state.release, AcceptedRelease) else None
    release = accepted.release if accepted is not None else state.release
    summary = {
        "schema": "artifact-lineage-v1",
        "status": state.state,
        "releaseId": release.release_id if release is not None else None,
        "manifestSha256": release.manifest_sha256 if release is not None else None,
        "tours": list(tours),
    }
    by_tour: dict[str, list[HealthFinding]] = {tour: [] for tour in tours}
    for issue in state.issues:
        affected = (issue.tour,) if issue.tour in tours else tuple(tours)
        for tour in affected:
            reason = issue.reason.value
            path = issue.path
            by_tour[tour].append(HealthFinding(
                code=issue.code,
                severity="error",
                scope="output",
                tour=tour,
                entity=path or "release",
                evidence={"state": state.state, "reason": reason, "path": path},
                message=(
                    f"{tour.upper()} release lineage: "
                    f"{reason.replace('-', ' ')}"
                    + (f" ({path})" if path else "")
                ),
            ))
    return summary, by_tour
