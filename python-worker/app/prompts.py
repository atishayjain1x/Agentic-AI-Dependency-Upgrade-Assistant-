"""
LLM prompt builders for the Maven dependency upgrade agent.

Each function returns a single user prompt string. The model response is parsed as
strict JSON by ``app.tools.rag_tools`` (``invokeLLMJson`` / ``parseLooseJson``)
and consumed by LangGraph nodes in ``app.graph`` and helpers in
``app.tools.report_tools``, ``app.tools.fix_tools``, and
``app.tools.self_correction_tools``.

Field names in the OUTPUT JSON SCHEMA sections intentionally mirror downstream
code. Do not rename response fields without updating those consumers.
"""

from __future__ import annotations

import json
from typing import Any

# Internal strategy names used by report enrichment and apply/self-correction.
FIX_STRATEGIES: tuple[str, ...] = (
    "VERSION_BUMP",
    "PARENT_UPGRADE",
    "BOM_UPGRADE",
    "DEPENDENCY_MANAGEMENT_OVERRIDE",
    "TRANSITIVE_OVERRIDE",
    "PLUGIN_UPGRADE",
    "MANUAL_REVIEW_REQUIRED",
    "NO_ACTION_REQUIRED",
    "OPENREWRITE_MIGRATION",
)

# Valid self-correction tool keys from app.tools.self_correction_tools.SELF_CORRECTION_TOOLS
SELF_CORRECTION_TOOL_NAMES: tuple[str, ...] = (
    "suggestVersionBumpRetry",
    "suggestManualReviewForTransitive",
    "suggestManualReviewForBuildFailure",
    "suggestOpenRewriteMigration",
)

# plannedChanges.changeType values consumed by app.graph.buildPlannedChange
PLANNED_CHANGE_TYPES: tuple[str, ...] = (
    "DEPENDENCY_VERSION_UPDATE",
    "PARENT_VERSION_UPDATE",
    "BOM_VERSION_UPDATE",
    "MANUAL_CHANGE",
)

# Report category values produced by app.tools.report_tools.enrichDependency
REPORT_CATEGORIES: tuple[str, ...] = (
    "CRITICAL_SECURITY",
    "HIGH_SECURITY",
    "MEDIUM_SECURITY",
    "LOW_SECURITY",
    "SAFE_PATCH_UPGRADE",
    "SAFE_MINOR_UPGRADE",
    "MAJOR_BREAKING_UPGRADE",
)


def _json(value: Any) -> str:
    """Serialize prompt evidence as indented JSON safe for embedding in f-strings."""
    return json.dumps(value, separators=(",", ":"), default=str)


def _clip(value: Any, limit: int = 500) -> Any:
    """Keep prompt evidence compact without changing its shape."""
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + "...[truncated]"
    if isinstance(value, list):
        return [_clip(item, limit) for item in value]
    if isinstance(value, dict):
        return {key: _clip(item, limit) for key, item in value.items()}
    return value


def buildReportPrompt(
    jobId: str,
    projectName: str,
    workspace: dict[str, Any],
    dependencies: list[dict[str, Any]],
    upgradeCandidates: dict[str, Any],
    vulnerabilityScan: dict[str, Any],
    errors: list[str],
    contextDocs: list[dict[str, str]],
) -> str:
    """
    Build the analysis-report enrichment prompt.

    Called by ``createAiReportFromEvidence`` in ``app.tools.rag_tools`` from the
    ``generateReport`` LangGraph node. The parsed JSON becomes ``state["report"]``
    and must match the shape built by ``buildAnalysisReport`` in
    ``app.tools.report_tools`` so ``selectDependencies`` and fix planning work.

    Args:
        jobId: Analysis job identifier echoed in the report.
        projectName: Maven project display name.
        workspace: Extracted workspace metadata (projectRoot, rootPomPath, pomMetadata).
        dependencies: CycloneDX SBOM dependency list from ``dependenciesFromSbom``.
        upgradeCandidates: Maven Versions plugin output (dependency/plugin/property updates).
        vulnerabilityScan: OSV scanner result dict with a ``vulnerabilities`` list.
        errors: Non-fatal tool warnings collected during evidence gathering.
        contextDocs: RAG migration documents with ``source`` and ``content`` keys.

    Returns:
        Prompt string instructing the model to return JSON only. Expected top-level
        keys: jobId, projectName, status, workspace, summary, recommendedFixOrder,
        dependencies, toolStatus, warnings, citations.

        Each ``dependencies[]`` entry must include at minimum: dependencyId, groupId,
        artifactId, currentVersion, latestVersion, recommendedVersion, upgradeType,
        priority, category, fixStrategy, reason, vulnerabilityIds.
    """
    evidence = {
        "jobId": jobId,
        "projectName": projectName,
        "workspace": {
            "projectRoot": workspace.get("projectRoot"),
            "rootPomPath": workspace.get("rootPomPath"),
            "pomMetadata": workspace.get("pomMetadata"),
        },
        "dependenciesFromSbom": _clip(dependencies, 240),
        "dependencyUpdates": _clip(upgradeCandidates.get("dependencyUpdates", []), 240),
        "pluginUpdates": _clip(upgradeCandidates.get("pluginUpdates", []), 160),
        "propertyUpdates": _clip(upgradeCandidates.get("propertyUpdates", []), 160),
        "vulnerabilities": _clip(vulnerabilityScan.get("vulnerabilities", []), 320),
        "vulnerabilityScanSuccess": vulnerabilityScan.get("success", False),
        "upgradeCommands": upgradeCandidates.get("commands", {}),
        "toolWarnings": errors,
    }

    context = [
        {"source": doc["source"], "content": _clip(doc["content"], 900)}
        for doc in contextDocs
    ]

    categories = ", ".join(REPORT_CATEGORIES)
    strategies = ", ".join(FIX_STRATEGIES)

    return f"""You are a senior Maven dependency-analysis agent. Produce a dependency upgrade report using ONLY the factual evidence below.

EVIDENCE SOURCES (authoritative; do not override):
- CycloneDX SBOM dependencies (dependenciesFromSbom)
- Maven Versions plugin output (dependencyUpdates, pluginUpdates, propertyUpdates)
- OSV vulnerability scan results (vulnerabilities)
- Tool warnings (toolWarnings)
- Retrieved migration RAG documents (supporting context only)

TOOL EVIDENCE:
{_json(evidence)}

RAG CONTEXT (cite sources in citations; do not invent CVEs, versions, or severities):
{_json(context)}

RULES:
1. Return strict JSON only. No markdown, prose, or code fences.
2. Include ONLY dependencies present in dependenciesFromSbom. Do not add or rename coordinates.
3. Echo workspace exactly from evidence.workspace (projectRoot, rootPomPath, pomMetadata).
4. Versions must come from SBOM, dependencyUpdates, OSV fixedVersions, or explicit SBOM fields only.
5. vulnerabilityIds, priority, and category must come from OSV/tool evidence only.
6. fixStrategy must be one of: {strategies}.
7. category must be one of: {categories}, or LOW when no finding applies.
8. priority must be CRITICAL, HIGH, MEDIUM, or LOW (from OSV severity or upgrade risk).
9. upgradeType must be PATCH, MINOR, MAJOR, or UNKNOWN when present.
10. warnings must equal toolWarnings unless you add a brief note tied to missing evidence.
11. toolStatus.sbomGenerated, toolStatus.vulnerabilityScanSuccess, and toolStatus.upgradeDetectionSuccess must reflect evidence booleans.

OUTPUT JSON SCHEMA (field names must match exactly):
{{
  "jobId": string,
  "projectName": string,
  "status": "COMPLETED" | "COMPLETED_WITH_ERRORS",
  "workspace": {{
    "projectRoot": string | null,
    "rootPomPath": string | null,
    "pomMetadata": object | null
  }},
  "summary": {{
    "totalDependencies": number,
    "critical": number,
    "high": number,
    "medium": number,
    "low": number,
    "categories": object
  }},
  "recommendedFixOrder": string[],
  "dependencies": [{{
    "dependencyId": string,
    "groupId": string,
    "artifactId": string,
    "currentVersion": string | null,
    "latestVersion": string | null,
    "recommendedVersion": string | null,
    "upgradeType": "PATCH" | "MINOR" | "MAJOR" | "UNKNOWN" | null,
    "priority": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
    "category": string,
    "fixStrategy": string,
    "reason": string,
    "vulnerabilityIds": string[]
  }}],
  "toolStatus": {{
    "sbomGenerated": boolean,
    "vulnerabilityScanSuccess": boolean,
    "upgradeDetectionSuccess": boolean
  }},
  "warnings": string[],
  "citations": string[]
}}"""


def buildCompactReportPrompt(
    jobId: str,
    projectName: str,
    dependencies: list[dict[str, Any]],
    upgradeCandidates: dict[str, Any],
    vulnerabilityScan: dict[str, Any],
    errors: list[str],
    contextDocs: list[dict[str, str]],
) -> str:
    """Build a small enrichment prompt suitable for local LLMs."""
    vulnerabilities = vulnerabilityScan.get("vulnerabilities", [])
    evidence = {
        "jobId": jobId,
        "projectName": projectName,
        "dependencyCount": len(dependencies),
        "upgradeCandidateCount": len(upgradeCandidates.get("dependencyUpdates", [])),
        "vulnerabilityCount": len(vulnerabilities),
        "topVulnerabilities": _clip(vulnerabilities[:3], 120),
        "topDependencies": _clip(dependencies[:3], 100),
        "toolWarnings": errors[:2],
        "ragSources": [doc.get("source") for doc in contextDocs[:1]],
        "ragContext": [
            {"source": doc["source"], "content": _clip(doc["content"], 180)}
            for doc in contextDocs[:1]
        ],
    }
    return f"""Return strict JSON only. Create a very short AI note for a Maven dependency analysis report.

EVIDENCE:
{_json(evidence)}

RULES:
1. Do not invent CVEs, versions, dependencies, or severities.
2. Maximum 20 words per string.
3. recommendedFixOrder contains at most 3 IDs from evidence only.

OUTPUT JSON SCHEMA:
{{
  "summaryText": string,
  "recommendedFixOrder": string[],
  "citations": string[]
}}"""


def buildFixPlanPrompt(
    fixBy: str,
    value: str,
    selectedDependencies: list[dict[str, Any]],
    contextDocs: list[dict[str, str]],
) -> str:
    """
    Build the fix-planning prompt for selected report findings.

    Called by ``createFixPlanWithAi`` in ``app.tools.rag_tools`` from the
    ``createFixPlan`` LangGraph node. Output is normalized by ``normalizeFixPlan``
    in ``app.graph`` and must expose keys read there: status, fixStrategy,
    dependencies, plannedChanges, commandsToRun, riskLevel, instructions,
    manualRisks, requiresApproval, citations.

    Args:
        fixBy: IDS, CATEGORY, or ALL (from FixPlanRequest).
        value: Filter value matching fixBy semantics.
        selectedDependencies: Dependencies chosen by ``selectDependencies``.
        contextDocs: RAG docs with source/content for migration guidance.

    Returns:
        Prompt requiring JSON with fix plan fields. ``status`` must be PLANNED for
        a successful plan (see ``app.main.fixPlan`` success check).
        ``plannedChanges[]`` entries use changeType values from PLANNED_CHANGE_TYPES.
    """
    fix_request = {
        "fixBy": fixBy,
        "value": value,
    }
    context = [
        {"source": doc["source"], "content": _clip(doc["content"], 900)}
        for doc in contextDocs
    ]
    change_types = ", ".join(PLANNED_CHANGE_TYPES)

    return f"""You are a senior Maven remediation planner. Create an executable fix plan from selected findings and evidence.

FIX REQUEST:
{_json(fix_request)}

SELECTED DEPENDENCIES (only these may be changed):
{_json(selectedDependencies)}

RAG CONTEXT:
{_json(context)}

RULES:
1. Return strict JSON only. No markdown, prose, or code fences.
2. Plan ONLY for dependencies in SELECTED DEPENDENCIES.
3. fixBy and value must echo the FIX REQUEST exactly.
4. fromVersion/toVersion in plannedChanges must come from currentVersion, latestVersion, recommendedVersion, or OSV fixedVersions on each dependency.
5. dependencyIds must contain the dependencyId of each planned dependency.
6. changeType must be one of: {change_types}.
7. requiresApproval must be true (human approval gate in app.graph.approvalCheckNode).
8. status must be PLANNED when the plan is actionable.
9. commandsToRun defaults to ["mvn test"] unless evidence requires another Maven command.
10. riskLevel must be LOW, MEDIUM, or HIGH (used by normalizeFixPlan / inferPlanRisk).
11. dependencies array must contain full dependency objects from SELECTED DEPENDENCIES (possibly filtered).

OUTPUT JSON SCHEMA (field names must match exactly):
{{
  "status": "PLANNED",
  "fixBy": string,
  "value": string,
  "dependencies": object[],
  "dependencyIds": string[],
  "plannedChanges": [{{
    "file": "pom.xml",
    "dependency": string,
    "fromVersion": string | null,
    "toVersion": string | null,
    "changeType": string
  }}],
  "commandsToRun": string[],
  "riskLevel": "LOW" | "MEDIUM" | "HIGH",
  "instructions": string,
  "manualRisks": string[],
  "requiresApproval": true,
  "citations": string[]
}}"""


def buildSelfCorrectionPrompt(
    fixPlan: dict[str, Any],
    resolution: dict[str, Any],
    failureAnalysis: dict[str, Any],
    selectedDependencies: list[dict[str, Any]],
    availableTools: list[dict[str, str]],
    iteration: int,
) -> str:
    """
    Build the self-correction prompt after a failed or partial fix iteration.

    Called by ``createSelfCorrectionPlanWithAi`` from the ``selfCorrect`` LangGraph
    node. Parsed JSON is merged into ``state["fixPlan"]`` via
    ``correction["updatedFixPlan"]`` and drives ``runSelfCorrectionTool`` using
    ``correction["selectedTool"]``.

    Args:
        fixPlan: Current fix plan from state (includes fixStrategy, dependencies).
        resolution: Output of ``evaluateResolutionWithAi`` (resolved, status,
            remainingVulnerabilities, reason, nextAction).
        failureAnalysis: Output of ``analyzeFailureLogsWithAi`` (failureType,
            summary, suggestedNextActions, recommendedFixStrategy).
        selectedDependencies: Dependencies still targeted for retry.
        availableTools: Tool catalog from ``tool_descriptions()`` (name, description).
        iteration: Current fixIteration from state (guardrailed by maxFixIterations).

    Returns:
        Prompt requiring JSON with: status, selectedTool, updatedFixPlan, reason,
        stopRetry. ``selectedTool`` must be a key from SELF_CORRECTION_TOOL_NAMES.
    """
    tool_names = ", ".join(SELF_CORRECTION_TOOL_NAMES)
    strategies = ", ".join(FIX_STRATEGIES)

    return f"""You are a senior Maven self-correction agent. Adjust the fix plan after a failed or partial remediation iteration.

ITERATION: {iteration}

CURRENT FIX PLAN:
{_json(fixPlan)}

RESOLUTION STATE (from evaluateResolutionWithAi; includes remainingVulnerabilities):
{_json(resolution)}

FAILURE ANALYSIS (from analyzeFailureLogsWithAi / Maven logs):
{_json(failureAnalysis)}

SELECTED DEPENDENCIES:
{_json(selectedDependencies)}

AVAILABLE SELF-CORRECTION TOOLS (selectedTool must be one of these name values exactly):
{_json(availableTools)}

VALID selectedTool VALUES: {tool_names}

RULES:
1. Return strict JSON only. No markdown, prose, or code fences.
2. Do not invent dependencies, versions, CVE IDs, or severities.
3. updatedFixPlan.fixStrategy must be one of: {strategies}.
4. selectedTool must exactly match one VALID selectedTool VALUE (camelCase).
5. Retry VERSION_BUMP only when recommendedVersion or latestVersion exists on a dependency.
6. Set stopRetry true when strategy is MANUAL_REVIEW_REQUIRED, NO_ACTION_REQUIRED, or OPENREWRITE_MIGRATION, or when iteration is exhausted.
7. Human approval is required before the next mutation; do not assume approval.
8. Use resolution.remainingVulnerabilities to avoid re-targeting resolved items.

OUTPUT JSON SCHEMA (field names must match exactly):
{{
  "status": "PLANNED" | "FALLBACK",
  "selectedTool": string,
  "updatedFixPlan": {{
    "fixStrategy": string,
    "dependencies": object[],
    "instructions": string,
    "plannedChanges": object[]
  }},
  "reason": string,
  "stopRetry": boolean
}}"""


def buildResolutionEvaluationPrompt(
    fixBy: str,
    value: str,
    fixStrategy: str,
    selectedDependencies: list[dict[str, Any]],
    remaining: list[dict[str, Any]],
    testResults: dict[str, Any],
    iteration: int,
) -> str:
    """
    Build the post-fix resolution evaluation prompt.

    Called by ``evaluateResolutionWithAi`` from ``analyzeResultsNode``. The graph
    reads ``resolution["resolved"]``, ``resolution["reason"]``,
    ``resolution["nextAction"]``, and critically ``resolution["remainingVulnerabilities"]``
    to populate ``selectedDependencies`` for retry.

    Args:
        fixBy: IDS, CATEGORY, or ALL.
        value: Matching filter value from the fix request.
        fixStrategy: Strategy used during the iteration.
        selectedDependencies: Original targets before rescan.
        remaining: Deterministic remaining matches from ``remainingMatchingDependencies``
            on the rescan report (pre-computed evidence passed into the prompt).
        testResults: Maven test output dict (success, skipped, exitCode, stdout, stderr).
        iteration: Current fixIteration number.

    Returns:
        Prompt requiring JSON with: status, resolved, remainingVulnerabilities,
        iteration, reason, nextAction.
    """
    fix_request = {"fixBy": fixBy, "value": value, "fixStrategy": fixStrategy}
    test_summary = {
        "success": testResults.get("success"),
        "skipped": testResults.get("skipped"),
        "exitCode": testResults.get("exitCode"),
        "stdoutTail": (testResults.get("stdout") or "")[-1200:],
        "stderrTail": (testResults.get("stderr") or "")[-1200:],
    }

    return f"""You are a senior Maven remediation evaluator. Decide whether the fix iteration resolved the targeted findings.

ITERATION: {iteration}

FIX REQUEST:
{_json(fix_request)}

ORIGINAL TARGET DEPENDENCIES:
{_json(selectedDependencies)}

REMAINING MATCHING DEPENDENCIES (deterministic post-rescan evidence; do not add entries):
{_json(remaining)}

MAVEN TEST/BUILD RESULT:
{_json(test_summary)}

RULES:
1. Return strict JSON only. No markdown, prose, or code fences.
2. resolved is true ONLY when remaining is empty AND test_summary.success is true (or skipped with success implied).
3. status is RESOLVED when resolved is true, otherwise UNRESOLVED.
4. remainingVulnerabilities must mirror REMAINING MATCHING DEPENDENCIES exactly (same dependency objects/count).
5. Do not invent vulnerability IDs, versions, or coordinates.
6. If test_summary.success is false, status must be UNRESOLVED even if vulnerabilities decreased.
7. nextAction recommends retry, manual review, or stop (approval still required before retry).
8. iteration must equal {iteration}.

OUTPUT JSON SCHEMA (field names must match exactly):
{{
  "status": "RESOLVED" | "UNRESOLVED",
  "resolved": boolean,
  "remainingVulnerabilities": object[],
  "iteration": number,
  "reason": string,
  "nextAction": string
}}"""


def buildFailureAnalysisPrompt(
    selectedDependencies: list[dict[str, Any]],
    fixPlan: dict[str, Any],
    stdout: str,
    stderr: str,
) -> str:
    """
    Build the Maven failure-log analysis prompt.

    Called by ``analyzeFailureLogsWithAi`` from ``applyAndValidateNode`` when
    ``testResult.success`` is false. Output is stored on ``state["failureAnalysis"]``
    and fed into ``buildSelfCorrectionPrompt``.

    Args:
        selectedDependencies: Dependencies that were part of the approved fix attempt.
        fixPlan: Approved fix plan (fixStrategy, dependencies, plannedChanges).
        stdout: Truncated Maven standard output tail (last 8000 chars).
        stderr: Truncated Maven standard error tail (last 8000 chars).

    Returns:
        Prompt requiring JSON with: status, failureType, summary, rootCause,
        affectedDependencies, suggestedNextActions, recommendedFixStrategy.
        Field names match the fallback dict in ``analyzeFailureLogsWithAi``.
    """
    logs = {
        "stdoutTail": (stdout or "")[-3000:],
        "stderrTail": (stderr or "")[-3000:],
    }
    strategies = ", ".join(FIX_STRATEGIES)

    return f"""You are a senior Maven failure analyst. Diagnose why validation failed after an approved fix attempt.

FIX PLAN (approved scope; do not expand beyond it):
{_json(fixPlan)}

SELECTED DEPENDENCIES:
{_json(selectedDependencies)}

MAVEN LOG EVIDENCE:
{_json(logs)}

RULES:
1. Return strict JSON only. No markdown, prose, or code fences.
2. Infer causes ONLY from stdoutTail/stderrTail plus fixPlan/selectedDependencies context.
3. Do not invent dependencies, versions, CVE IDs, severities, or stack frames absent from logs.
4. recommendedFixStrategy must be one of: {strategies}.
5. failureType must be COMPILATION, TEST, DEPENDENCY, PLUGIN, or UNKNOWN.
6. affectedDependencies lists dependencyId strings only when logs tie failure to them.
7. suggestedNextActions must be short actionable strings for a human-approved retry flow.

OUTPUT JSON SCHEMA (field names must match exactly):
{{
  "status": "COMPLETED" | "FALLBACK",
  "failureType": "COMPILATION" | "TEST" | "DEPENDENCY" | "PLUGIN" | "UNKNOWN",
  "summary": string,
  "rootCause": string,
  "affectedDependencies": string[],
  "suggestedNextActions": string[],
  "recommendedFixStrategy": string
}}"""
