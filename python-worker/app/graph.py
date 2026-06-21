"""LangGraph pipeline definitions for analyze, fix-plan, and apply-fix workflows.

Each ``build*Graph`` function returns a compiled graph consumed by ``app.main``.
Nodes mutate ``AnalyzeState`` or ``FixState`` (see ``app.state``).
"""

from typing import Any
import sys

from langgraph.graph import END,StateGraph

from app.config import settings
from app.state import AnalyzeState,FixState

from app.tools.file_tools import copyWorkspaceForFix,prepareWorkspace
from app.tools.fix_tools import (applyFixStrategy,applyPlannedChanges,generatePatch,runValidationIfNeeded,selectDependencies,snapshotOrignal,writeTestLogs)

from app.tools.maven_tools import dependenciesFromSbom,detectUpgradeCandidates,generateSbom,scanVulnerabilities
from app.tools.rag_tools import (analyzeFailureLogsWithAi,createAiReportFromEvidence,createFixPlanWithAi,createSelfCorrectionPlanWithAi,evaluateResolutionWithAi,retrieveAnalysisContext,retrieveFixContext)
from app.tools.report_tools import buildVulnerabilityDiff
from app.tools.self_correction_tools import runSelfCorrectionTool

def withError(state,message):
    """Append an error string to the state's errors list."""
    return [*state.get("errors",[]),message]

def buildLinearGraph(stateCls,nodes:list[tuple[str,Any]]):
    """Build a sequential LangGraph: node1 -> node2 -> ... -> END."""
    graph=StateGraph(stateCls)
    for name,node in nodes:
        graph.add_node(name,node)
    graph.set_entry_point(nodes[0][0])
    for current,next_node in zip(nodes,nodes[1:]):
        graph.add_edge(current[0],next_node[0])
    graph.add_edge(nodes[-1][0],END)
    return graph.compile()

def buildAnalyzeGraph():
    """Linear graph: prepare project -> collect evidence -> RAG -> generate report."""
    return buildLinearGraph(AnalyzeState,[
        ("prepareProject",prepareProjectNode),
        ("collectEvidence",collectEvidenceNode),
        ("retrieveRagContext",retrieveAnalysisRagNode),
        ("generateReport",generateReportNode)
    ])

def buildFixPlanGraph():
    """Linear graph: select findings -> RAG -> create fix plan -> validate plan."""
    return buildLinearGraph(
        FixState,
        [
            ("selectFindings",selectFixFindingsNode),
            ("retrieveRagContext",retrieveFixRagNode),
            ("createFixPlan",createFixPlanNode),
            ("validatePlan",validateFixPlanNode)
        ]
    )


def buildApplyFixGraph():
    """Branching graph: approval -> apply -> rescan -> evaluate -> self-correct loop -> report."""
    graph=StateGraph(FixState)
    graph.add_node("approvalCheck",approvalCheckNode)
    graph.add_node("applyFix",applyAndValidateNode)
    graph.add_node("rescanProject",rescanProjectNode)
    graph.add_node("analyzeResults",analyzeResultsNode)
    graph.add_node("selfCorrect",selfCorrectNode)
    graph.add_node("finaliseReport",finaliseReportNode)

    graph.set_entry_point("approvalCheck")
    graph.add_conditional_edges("approvalCheck",routeAfterApproval,{"approved":"applyFix","needsApproval":"finaliseReport"})
    graph.add_conditional_edges("applyFix",routeAfterApply,{"continue":"rescanProject","done":"finaliseReport"})
    graph.add_edge("rescanProject","analyzeResults")
    graph.add_conditional_edges("analyzeResults",routeAfterResultAnalysiss,{"retry":"selfCorrect","done":"finaliseReport"})
    graph.add_conditional_edges("selfCorrect",routeAfterSelfCorrection,{"retry":"applyFix","done":"finaliseReport"})
    graph.add_edge("finaliseReport",END)
    return graph.compile()



def prepareProjectNode(state:AnalyzeState):
    """Extract the ZIP into an isolated workspace and detect the Maven reactor root."""
    try:
        workspace=prepareWorkspace(state["jobId"],state["zipPath"])
        sys.stderr.write(f"DEBUG prepareProjectNode: workspace={workspace.get('projectRoot')}\n")
        sys.stderr.flush()
        return {**state,"workspace":workspace,"errors":state.get("errors",[])}
    except Exception as e:
        sys.stderr.write(f"DEBUG prepareProjectNode: error={str(e)}\n")
        sys.stderr.flush()
        return {**state,"workspace":{},"errors":withError(state,str(e))}

def collectEvidenceNode(state:AnalyzeState):
    """Generate SBOM, parse dependencies, detect upgrades, and scan vulnerabilities."""
    workspace=state.get("workspace") or {}
    errors=state.get("errors",[])
    if not workspace.get("projectRoot"):
        sys.stderr.write(f"DEBUG collectEvidenceNode: no projectRoot\n")
        sys.stderr.flush()
        return {
            **state,
            "sbom":{},
            "dependencies":[],
            "upgradeCandidates":{"dependencyUpdates":[],"commands":{}},
            "vulnerabilities":{"success":False,"vulnerabilities":[]},
            "errors":errors
        }
    sbom_result=generateSbom(workspace["projectRoot"])
    sys.stderr.write(f"DEBUG collectEvidenceNode: sbom_result={sbom_result.get('success')}\n")
    sys.stderr.flush()
    if not sbom_result.get("success"):
        errors=[*errors,sbom_result.get("error","SBOM generation failed")]
    
    dependencies=dependenciesFromSbom(sbom_result.get("bom",{}))
    sys.stderr.write(f"DEBUG collectEvidenceNode: dependencies count={len(dependencies)}\n")
    sys.stderr.flush()
    upgradeCandidates=detectUpgradeCandidates(workspace["projectRoot"],dependencies)
    vulnerabilities=scanVulnerabilities(workspace["projectRoot"],sbom_result.get("path"))
    return {
        **state,
        "sbom":sbom_result,
        "dependencies":dependencies,
        "upgradeCandidates":upgradeCandidates,
        "vulnerabilities":vulnerabilities,
        "errors":errors
    }

def retrieveAnalysisRagNode(state:AnalyzeState):
    """Retrieve migration docs from Qdrant based on vulnerabilities and upgrade candidates."""
    try:
        contextDocs=retrieveAnalysisContext(dependencies=state.get("dependencies",[]),
                                            
                                            upgradeCandidates=state.get("upgradeCandidates",{}),
                                            vulnerabilityScan=state.get("vulnerabilities",{})
                                            )
        return {**state,"ragContext":contextDocs}
    except Exception as ex:
        return {**state,"ragContext":[],"errors":withError(state,f"Rag Retrieval failed:{ex}")}

def generateReportNode(state:AnalyzeState):
    """Build an AI-enriched dependency report and attach agent trace metadata."""
    report,metadata=createAiReportFromEvidence(state["jobId"],state["projectName"],state.get("workspace"),
                                               state.get("dependencies"),state.get("upgradeCandidates"),
                                               state.get("vulnerabilities"),state.get("errors"),state.get("ragContext"))
    
    report["agentTrace"]={
        "ragSources":sorted({doc["source"]for doc in state.get("ragContext",[])}),
        "toolEvidence":{
            "dependencyCount":len(state.get("dependencies",[])),
            "upgradeCandidateCount":len(state.get("upgradeCandidates",{}).get("dependencyUpdates",[])),
            "vulnerabilityCount":len(state.get("vulnerabilities",{}).get("vulnerabilities",[]))
        }
    }
    return {**state,"report":report,"aiEnrichment":metadata}

def selectFixFindingsNode(state:FixState) -> FixState:
    """Filter vulnerable report dependencies by ids, category, or all."""
    selected=selectDependencies(report=state.get("report",{}),fixBy=state.get("fixBy",""),value=state.get("value",""),
                                dependencyIds=state.get("dependencyIds",[]))
    errors=state.get("errors",[])
    if not selected:
        errors=withError(state,"No dependencies selected for fixing")
    return {**state,"selectedDependencies":selected,"errors":errors}    

def retrieveFixRagNode(state:FixState) -> FixState:
    """Retrieve RAG context for the selected dependencies."""
    try:
        contextDocs=retrieveFixContext(dependencies=state.get("selectedDependencies",[]))
        return {**state,"ragContext":contextDocs}
    except Exception as ex:
        return {**state,"ragContext":[],"errors":withError(state,f"Rag Retrieval failed:{ex}")}
    
def createFixPlanNode(state:FixState) -> FixState:
    """Ask the LLM for a fix plan and normalize it into a consistent shape."""
    plan=createFixPlanWithAi(report=state.get("report",{}),selectedDependencies=state.get("selectedDependencies",[]),
                             fixBy=state.get("fixBy",""),value=state.get("value",""),
                             contextDocs=state.get("ragContext",[]))
    plan=normalizeFixPlan(state,plan)
    return {**state,"fixPlan":plan,"selectedDependencies":plan.get("dependencies",[])}

def validateFixPlanNode(state:FixState) -> FixState:
    """Attach approval metadata indicating human review is required by default."""
    plan=state.get("fixPlan",{})
    approval=buildApproval(approved=False,fixPlan=plan)
    return {**state,"approval":approval,"fixPlan":{**plan,"approval":approval}}

def normalizeFixPlan(state:FixState,plan:dict) -> dict:
    """Fill missing fix-plan fields: IDs, strategy, plannedChanges, risk, citations, etc."""
    selected=normalizePlanDependencies(plan.get("dependencies"), state.get("selectedDependencies",[]))
    effectiveStrategy=inferFixStrategy(selected)
    plannedChanges=normalizePlannedChanges(
        plan.get("plannedChanges"),
        selected,
        effectiveStrategy,
    )
    citations=normalizeCitations(plan.get("citations"), state.get("ragContext",[]))
    return{
        "fixPlanId":state["jobId"],
        "analysisJobId":state["analysisJobId"],
        "fixBy":state["fixBy"],
        "value":state["value"],
        "status": "PLANNED" if plan.get("status") in {None,"FALLBACK"} else plan.get("status"),
        "dependencies":selected,
        "dependencyIds":[dependency.get("dependencyId") for dependency in selected if dependency.get("dependencyId")],
        "plannedChanges":plannedChanges,
        "commandsToRun":plan.get("commandsToRun") or ["mvn test"],
        "riskLevel":plan.get("riskLevel") or inferPlanRisk(selected),
        "instructions":plan.get("instructions") or "Review and approve the planned dependency changes.",
        "manualRisks":plan.get("manualRisks") or [],
        "requiresApproval":True,
        "citations":citations,
    }

def inferFixStrategy(dependencies:list[dict]) -> str:
    """Infer whether selected vulnerable dependencies can be version-bumped."""
    if dependencies and all(targetVersionForDependency(dependency) for dependency in dependencies):
        return "VERSION_BUMP"
    return "MANUAL_REVIEW_REQUIRED"

def normalizePlanDependencies(planDependencies:list[dict] | None, selectedDependencies:list[dict]) -> list[dict]:
    """Keep model-selected dependencies aligned to the original selected full objects."""
    selectedById={dependency.get("dependencyId"): dependency for dependency in selectedDependencies}
    if not planDependencies:
        return selectedDependencies
    normalized=[]
    for dependency in planDependencies:
        dependencyId=dependency.get("dependencyId")
        if dependencyId in selectedById:
            normalized.append(selectedById[dependencyId])
    return normalized or selectedDependencies

def normalizePlannedChanges(plannedChanges:list[dict] | None, dependencies:list[dict], fixStrategy:str) -> list[dict]:
    """Use AI changes only when complete; otherwise rebuild from dependency versions."""
    expectedByDependency={
        dependency.get("dependencyId"): buildPlannedChange(dependency, fixStrategy)
        for dependency in dependencies
    }
    expectedByDependency={key:value for key,value in expectedByDependency.items() if key and value}
    if not plannedChanges:
        return list(expectedByDependency.values())

    normalized=[]
    for change in plannedChanges:
        dependencyId=change.get("dependency")
        expected=expectedByDependency.get(dependencyId)
        if not expected:
            continue
        if not change.get("toVersion"):
            normalized.append(expected)
            continue
        normalized.append({
            **expected,
            **change,
            "changeType": expected["changeType"],
            "toVersion": expected["toVersion"],
        })
    return normalized or list(expectedByDependency.values())

def normalizeCitations(planCitations:list[str] | None, contextDocs:list[dict]) -> list[str]:
    """Prevent invented citations while preserving retrieved source references."""
    contextSources=sorted({doc["source"] for doc in contextDocs})
    if not planCitations:
        return contextSources
    allowed=set(contextSources)
    citations=[citation for citation in planCitations if citation in allowed]
    return citations or contextSources

def buildPlannedChange(dependency:dict,fixStrategy:str) -> dict:
    """Build one pom.xml version-change entry from a dependency and fix strategy."""
    targetVersion=targetVersionForDependency(dependency)
    if not targetVersion:
        return None
    changeType={
        "VERSION_BUMP":"DEPENDENCY_VERSION_UPDATE",
        "PARENT_UPGRADE":"PARENT_VERSION_UPDATE",
        "BOM_UPGRADE":"BOM_VERSION_UPDATE",
    }.get(fixStrategy,"MANUAL_CHANGE")

    return{
        "file":"pom.xml",
        "dependency":dependency.get("dependencyId")  ,
        "fromVersion":dependency.get("currentVersion"),
        "toVersion":targetVersion,
        "changeType":changeType}

def targetVersionForDependency(dependency:dict) -> str | None:
    """Return the best known target version for a vulnerable dependency."""
    candidates=dependency.get("fixedVersionCandidates") or []
    return dependency.get("recommendedVersion") or dependency.get("latestVersion") or (candidates[-1] if candidates else None)
    

def inferPlanRisk(dependencies:list[dict]) -> str:
    """Derive LOW, MEDIUM, or HIGH risk from dependency priority levels."""
    priorities={d.get("priority") for d in dependencies}
    if priorities & {"CRITICAL","HIGH"}:
        return "HIGH"
    if "MEDIUM" in priorities:
        return "MEDIUM"
    return "LOW"


def buildApproval(approved:bool,fixPlan:dict) -> dict:
    """Build approval metadata; human gate unless already approved."""
    requiresApproval= not approved

    return {
        "approved":approved,
        "requiresApproval":requiresApproval,
        "fixPlanId":fixPlan.get("fixPlanId"),
        "status":"APPROVAL_REQUIRED" if requiresApproval else "APPROVED_OR_NOT_REQUIRED",
        "message":(
            "Human Approval Required: Please review the planned dependency changes and approve or reject them."
            if requiresApproval 
            else "No human approval required. The fix plan can proceed automatically."
        )
    }

def approvalCheckNode(state:FixState) -> FixState:
    """Reconcile approval state from the fix plan and the approved flag."""
    plan=state.get("fixPlan",{})
    approval=buildApproval(approved=state.get("approved",False),fixPlan=plan)
    return {**state,"approval":approval,"selectedDependencies":plan.get("dependencies",[]),
            "fixStrategy":inferFixStrategy(plan.get("dependencies",[]))}


def routeAfterApproval(state:FixState) -> str:
    """Route to applyFix if approved, otherwise finaliseReport."""
    approval=state.get("approval",{})
    if approval.get("requiresApproval"):
        return "needsApproval"
    else:
        return "approved"
    

def prepareFixWorkspace(state:FixState) -> FixState:
    """Re-extract the analysis ZIP, snapshot the original, and copy a fix workspace."""
    try:
        sys.stderr.write(f"INFO applyFix: preparing workspace for jobId={state.get('jobId')} analysisJobId={state.get('analysisJobId')}\n")
        sys.stderr.flush()
        analysedWorkspace=prepareWorkspace(state["analysisJobId"],state["zipPath"])
        orignalSnapshot=snapshotOrignal(analysedWorkspace["projectRoot"],state["jobId"])
        fixWorkspace=copyWorkspaceForFix(analysedWorkspace["projectRoot"],state["jobId"])
        sys.stderr.write(f"INFO applyFix: workspace ready projectRoot={fixWorkspace.get('projectRoot')}\n")
        sys.stderr.flush()
        return {
            **state,
            "workspace":{**fixWorkspace,"orignalProjectRoot":orignalSnapshot},
            "errors":state.get("errors",[])
        }
    except Exception as e:
        sys.stderr.write(f"ERROR applyFix: workspace preparation failed: {e}\n")
        sys.stderr.flush()
        return {**state,"workspace":{},"errors":withError(state,str(e))}


def runApplyChecks(state:FixState) -> FixState:
    """Run safety checks for applying planned changes."""
    violations=[]
    plannedChanges=(state.get("fixPlan") or {}).get("plannedChanges",[])
    if not state.get("approved",False):
        violations.append("Fix plan not approved for execution.")
    if state.get("fixIteration",0) >= settings.maxFixIterations:
        violations.append(f"Maximum fix iterations ({settings.maxFixIterations}) reached.")
    if not plannedChanges:
        violations.append("No planned changes found in fix plan.")
    unsupported=[change for change in plannedChanges if change.get("changeType")!="DEPENDENCY_VERSION_UPDATE"]
    if unsupported:
        violations.append("Only DEPENDENCY_VERSION_UPDATE planned changes can be applied automatically.")
    return {"passed":not violations,"violations":violations}


def applyAndValidateNode(state:FixState):
    """Prepare workspace and apply fixPlan.plannedChanges without invoking AI."""
    sys.stderr.write(f"INFO applyFix: started jobId={state.get('jobId')}\n")
    sys.stderr.flush()
    prepared=prepareFixWorkspace(state)
    if not prepared.get("workspace",{}).get("projectRoot"):
        sys.stderr.write("INFO applyFix: workspace preparation failed\n")
        sys.stderr.flush()
        return {**prepared,
                "fixResult":failedFixResult(prepared,"Fix workspace preparation failed. Cannot apply fix plan."),
                "testResult":{"success":False,"skipped":True}}

    checks=runApplyChecks(prepared)
    sys.stderr.write(f"INFO applyFix: guardrails passed={checks['passed']} violations={checks['violations']}\n")
    sys.stderr.flush()
    if not checks["passed"]:
        return {
            **prepared,
            "fixResult": failedFixResult(prepared,"Fix Blocked By Safety Checks"),
            "testResult":{"success":False,"skipped":True}
        }
    
    workspace=prepared["workspace"]
    plannedChanges=(prepared.get("fixPlan") or {}).get("plannedChanges",[])
    sys.stderr.write(f"INFO applyFix: applying plannedChanges count={len(plannedChanges)}\n")
    sys.stderr.flush()
    fixResult=applyPlannedChanges(workspace["projectRoot"],plannedChanges)
    sys.stderr.write(f"INFO applyFix: apply result success={fixResult.get('success')} message={fixResult.get('message')}\n")
    sys.stderr.flush()
    validated={
        **prepared,
        "guardrails":checks,
        "fixResult":fixResult,
        "fixIteration":prepared.get("fixIteration",0)+1,
        "testResult":{"success":True,"skipped":True,"exitCode":0,"stdout":"","stderr":""}
    }
    return {**validated,"failureAnalysis":{"status":"SKIPPED","reason":"Fast apply uses plannedChanges without validation or AI analysis"}}

def failedFixResult(state:FixState,message:str) -> dict:
    """Return a standard failure payload when a fix cannot proceed."""
    return{
        "success":False,
        "fixedDependencies":[],
        "failedDependencies":state.get("selectedDependencies",[]),
        "message":message
    }

def routeAfterApply(state:FixState) -> str:
    """Finalize immediately after fast planned-change apply."""
    return "done"

def rescanProjectNode(state:FixState) -> FixState:
    """Re-run SBOM, upgrades, vulnerability scan, and AI report on the fixed workspace."""
    workspace=state.get("workspace",{})
    if not workspace.get("projectRoot"):
        return {**state,"rescanReport":state.get("report",{})}
    report, _metadata=scanProjectToReport(
        state["jobId"],
        f"fix-{state["jobId"]}",
        workspace,
        state.get("errors")
    )

    return {**state,"rescanReport":report}


def analyzeResultsNode(state:FixState)->FixState:
    """Diff vulnerabilities, evaluate resolution with AI, and set outcome for retry logic."""
    diff=buildVulnerabilityDiff(state.get("report",{}),state.get("rescanReport",{}))
    resolution=evaluateResolutionWithAi(fixBy=state["fixBy"],
                                        value=state["value"],
                                        fixStrategy="",
                                        selectedDependencies=state.get("selectedDependencies",[]),
                                        rescanReport=state.get("rescanReport",{}),
                                        testResult=state.get("testResult",{}),
                                        iteration=state.get("fixIteration",0))
    remaining=resolution.get("remainingVulnerabilities",[])
    outcome={
        "status":"RESOLVED" if resolution.get("resolved") else "UNRESOLVED",
        "resolved":bool(resolution.get("resolved")),
        "reason":resolution.get("reason",""),
        "nextAction":resolution.get("nextAction",""),
        "testStatus":{
            "success":state.get("testResult",{}).get("success",False),
            "skipped":state.get("testResult",{}).get("skipped",False),
            "exitCode":state.get("testResult",{}).get("exitCode",-1)
        },
        "failureAnalysis":state.get("failureAnalysis",{}),
        "vulnerabilityDiff":diff,
        "remainingVulnerabilities":remaining
    }
    updatedState={**state,"vulnerabilityDiff":diff,"resolution":resolution,"outcomeAnalysis":outcome}
    if remaining:
        updatedState["selectedDependencies"]=remaining
    return updatedState


def routeAfterResultAnalysiss(state:FixState)->str:
    """Retry self-correction if unresolved and under the max iteration limit."""
    canRetry= not state.get("resolution",{}).get("resolved") and state.get("fixIteration",0) < settings.maxFixIterations and state.get("selectedDependencies",[])
    return "retry" if canRetry else "done"   

def selfCorrectNode(state:FixState)->FixState:
    """Run AI self-correction and a deterministic tool; merge an updated fix plan for retry."""
    correction=createSelfCorrectionPlanWithAi(
        fixPlan=state.get("fixPlan",{}),
        resolution=state.get("resolution",{}),
        failureAnalysis=state.get("failureAnalysis",{}),
        selectedDependencies=state.get("selectedDependencies",[]),
        iteration=state.get("fixIteration",0))
        
    toolResult=runSelfCorrectionTool(
        correction.get("selectedTool","suggestVersionBumpRetry"),
        {
            "fixPlan":state.get("fixPlan",{}),
            "resolution":state.get("resolution",{}),
            "failureAnalysis":state.get("failureAnalysis",{}),
            "selectedDependencies":state.get("selectedDependencies",[]),
            "iteration":state.get("fixIteration",0)
        }
    )
    toolPlan={
        "dependencies":toolResult.get("dependencies",[]),
        "instructions":toolResult.get("instructions",""),
    }
    updatedPlan={
        **state.get("fixPlan",{}),
        **correction.get("updatedFixPlan",{}),
        **{key:value for key,value in toolPlan.items() if value},
        "selfCorrection":correction,
        "selfCorrectionToolResult":toolResult
    }

    return {
        **state,
        "selfCorrection":{**correction, "toolResult":toolResult},
        "fixPlan":updatedPlan,
        "selectedDependencies":updatedPlan.get("dependencies") or state.get("selectedDependencies",[])
    }

    
def routeAfterSelfCorrection(state:FixState)->str:
    """Stop if manual review or stopRetry; otherwise retry applyFix."""
    correction=state.get("selfCorrection") or {}
    strategy=inferFixStrategy((state.get("fixPlan") or {}).get("dependencies",[]))
    toolResult=correction.get("toolResult") or {}
    if correction.get("stopRetry") or toolResult.get("stopRetry") or strategy in {"MANUAL_REVIEW_REQUIRED","NO_ACTION_REQUIRED"}:
        return  "done"
    return "retry"


def finaliseReportNode(state:FixState) ->FixState:
    """Generate patch and test logs, compute success/status, and build the fixReport."""
    workspace=state.get("workspace") or {}
    patchPath=None
    logsPath=None
    if workspace.get("artifactsPath") and workspace.get("orignalProjectRoot") and workspace.get("projectRoot"):
        patchPath=generatePatch(workspace["orignalProjectRoot"],workspace["projectRoot"],workspace["artifactsPath"])
        logsPath=writeTestLogs(workspace["artifactsPath"],state.get("testResult",{}))

    fixResult=state.get("fixResult",{})
    testResult=state.get("testResult",{})
    approval=state.get("approval",{})
    guardrails=state.get("guardrails",{})
    resolution=state.get("resolution",{})
    errors=state.get("errors",[])

    success=bool(fixResult.get("fixedDependencies")) and not errors
    if approval.get("requiresApproval") or (guardrails and not guardrails.get("passed",True)):
        success=False
    success=success and testResult.get("success",False)
    if resolution:
        success=success and bool(resolution.get("resolved"))
    
    status="COMPLETED" if success else "FAILED"
    if approval.get("requiresApproval"):
        status="APPROVAL_REQUIRED"
    elif guardrails and not guardrails.get("passed",True):
        status="BLOCKED"
    
    report={
        "jobId":state["jobId"],
        "analysisJobId":state["analysisJobId"],
        "status":status,
        "fixBy": state["fixBy"],
        "value":state["value"],
        "dependencyIds":[dependency.get("dependencyId") for dependency in state.get("selectedDependencies",[]) if dependency.get("dependencyId")],
        "iterations":state.get("fixIteration",0),
        "approval":approval,
        "guardrails":guardrails,
        "fixPlan":state.get("fixPlan",{}),
        "fixedDependencies":fixResult.get("fixedDependencies",[]),
        "failedDependencies":fixResult.get("failedDependencies",[]),
        "message":fixResult.get("message"),
        "resolution":resolution,
        "rescanReport":state.get("rescanReport"),
        "vulnerabilityDiff":state.get("vulnerabilityDiff"),
        "outcomeAnalysis":state.get("outcomeAnalysis"),
        "failureAnalysis":state.get("failureAnalysis"),
        "selfCorrection":state.get("selfCorrection"),
        "testStatus":{
            "success":testResult.get("success",False),
            "skipped":testResult.get("skipped",False),
            "exitCode":testResult.get("exitCode")
        },
        "patchPath":patchPath,
        "logsPath":logsPath,
        "errors":errors
    
        }
    
    return {**state,"patchPath":patchPath or "","fixReport":report}



def scanProjectToReport(jobId,projectName,workspace,errors):
    """Re-gather evidence and build an AI report for post-fix rescan."""
    sbomResult=generateSbom(workspace["projectRoot"])
    dependencies=dependenciesFromSbom(sbomResult.get("bom",{}))
    if not sbomResult.get("success"):
        errors=[*errors,sbomResult.get("error","SBOM generation failed during rescan")]
    upgradeCandidates=detectUpgradeCandidates(workspace["projectRoot"])
    vulnerabilities=scanVulnerabilities(workspace["projectRoot"],sbomResult.get("path"))
    return createAiReportFromEvidence(
        jobId,
        projectName,
        workspace,
        dependencies,
        upgradeCandidates,
        vulnerabilities,
        errors
    )
