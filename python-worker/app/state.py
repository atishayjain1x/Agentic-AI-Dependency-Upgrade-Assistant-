"""TypedDict state schemas for LangGraph analyze and fix pipelines."""

from typing import Any,TypedDict

class AnalyzeState(TypedDict, total=False):
    """State carried through the dependency analysis graph."""

    jobId:str
    projectName:str
    zipPath:str

    workspace: dict[str,Any]
    sbom: dict[str,Any]

    dependencies:list[dict[str,Any]]

    upgradeCandidates:dict[str,Any]

    vulnerabilities:list[dict[str,Any]]
    
    report: dict[str,Any]

    aiEnrichments:dict[str,Any]

    ragContext:list[dict[str,Any]]

    errors:list[str]

class FixState(TypedDict, total=False):
    """State carried through the fix-plan and apply-fix graphs."""

    jobId:str
    analysisJobId:str
    zipPath:str
    report: dict[str,Any]
    fixBy:str
    value:str
    dependencyIds:list[str]
    approved:bool
    workspace: dict[str,Any]

    selectedDependencies:list[dict[str,Any]]
    fixPlan:dict[str,Any]
    ragContext:list[dict[str,Any]]



    approval: dict[str,Any]
    guardrails:dict[str,Any]
    fixIteration:int
    fixResult:dict[str,Any]
    testResult:dict[str,Any]
    rescanReport:dict[str,Any]
    resolution:dict[str,Any]
    vulnerabilityDiff:dict[str,Any]
    outcomeAnalysis: dict[str,Any]
    failureAnalysis:dict[str,Any]
    selfCorrection:dict[str,Any]
    patchPath:str
    fixReport:dict[str,Any]

    errors:list[str]
