"""Deterministic self-correction tools invoked after a failed fix iteration.

Each tool returns a recommended fix strategy and whether to stop retrying.
The LLM selects a tool name; ``runSelfCorrectionTool`` dispatches it.
"""

from __future__ import annotations

from typing import Any


def suggestVersionBumpRetry(context: dict[str, Any]) -> dict[str, Any]:
    """Retry a direct VERSION_BUMP when target versions are still available."""
    return {
        "tool": "suggestVersionBumpRetry",
        "recommendedFixStrategy": "VERSION_BUMP",
        "stopRetry": False,
        "instructions": "Retry version bump only for unresolved dependencies with concrete recommendedVersion or latestVersion.",
        "dependencies": dependenciesWithTargetVersions(context.get("selectedDependencies", [])),
    }


def suggestManualReviewForTransitive(context: dict[str, Any]) -> dict[str, Any]:
    """Escalate transitive dependency conflicts to manual review."""
    return {
        "tool": "suggestManualReviewForTransitive",
        "recommendedFixStrategy": "MANUAL_REVIEW_REQUIRED",
        "stopRetry": True,
        "instructions": "Manual review required for transitive dependencies.",
        "dependencies": context.get("selectedDependencies", []),
    }


def suggestManualReviewForBuildFailure(context: dict[str, Any]) -> dict[str, Any]:
    """Escalate Maven build/test failures to manual review."""
    return {
        "tool": "suggestManualReviewForBuildFailure",
        "recommendedFixStrategy": "MANUAL_REVIEW_REQUIRED",
        "stopRetry": True,
        "instructions": "Manual review required for build failures.",
        "dependencies": context.get("selectedDependencies", []),
    }


def suggestOpenRewriteMigration(context: dict[str, Any]) -> dict[str, Any]:
    """Recommend an OpenRewrite migration when automated bumps are insufficient."""
    return {
        "tool": "suggestOpenRewriteMigration",
        "recommendedFixStrategy": "OPENREWRITE_MIGRATION",
        "stopRetry": True,
        "instructions": "Apply an OpenRewrite recipe or manual migration before retrying.",
        "dependencies": context.get("selectedDependencies", []),
    }


SELF_CORRECTION_TOOLS = {
    "suggestVersionBumpRetry": suggestVersionBumpRetry,
    "suggestManualReviewForTransitive": suggestManualReviewForTransitive,
    "suggestManualReviewForBuildFailure": suggestManualReviewForBuildFailure,
    "suggestOpenRewriteMigration": suggestOpenRewriteMigration,
}


def tool_descriptions() -> list[dict[str, str]]:
    """Return the self-correction tool catalog for LLM prompt construction."""
    return [
        {
            "name": name,
            "description": (func.__doc__ or "").strip(),
        }
        for name, func in SELF_CORRECTION_TOOLS.items()
    ]


def runSelfCorrectionTool(toolName: str, context: dict[str, Any]) -> dict[str, Any]:
    """Dispatch a named self-correction tool; fallback to manual review if unknown."""
    tool = SELF_CORRECTION_TOOLS.get(toolName)
    if not tool:
        return {
            "tool": toolName,
            "recommendedFixStrategy": "MANUAL_REVIEW_REQUIRED",
            "stopRetry": True,
            "instructions": "Unknown self-correction tool. Manual review required.",
            "dependencies": context.get("selectedDependencies", []),
        }
    return tool(context)


def dependenciesWithTargetVersions(dependencies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter dependencies that have a recommendedVersion or latestVersion."""
    return [dep for dep in dependencies if dep.get("recommendedVersion") or dep.get("latestVersion")]
