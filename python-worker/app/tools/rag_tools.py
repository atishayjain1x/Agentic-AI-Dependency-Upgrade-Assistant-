"""RAG retrieval and LLM enrichment for reports, fix plans, and self-correction."""

from __future__ import annotations
import json

from pathlib import Path
from typing import Any
from app.config import settings
from app.llm_factory import buildEmbeddings, buildLLM
from app.prompts import(
    buildFailureAnalysisPrompt,
    buildCompactReportPrompt,
    buildFixPlanPrompt,
    buildResolutionEvaluationPrompt,
    buildSelfCorrectionPrompt,
    buildReportPrompt,
)

from app.tools.report_tools import buildAnalysisReport
from app.tools.self_correction_tools import tool_descriptions

_retrieverCache=None

def ai_disabled()->bool:
    """Return True when AI enrichment is off or the Google API key is missing."""
    if not settings.enableAiEnrichment:
        return True
    if settings.aiProvider.lower()=="gemini" and not settings.googleApiKey:
        return True
    return False

def invokeLLM(prompt:str)->str:
    """Call Gemini and return the text content of the response."""
    response=buildLLM().invoke(prompt)
    return getattr(response,"content")

def invokeLLMJson(prompt:str):
    """Call the LLM and parse the response as JSON."""
    return parseLooseJson(invokeLLM(prompt))

def createAiReportFromEvidence(jobId:str,projectName:str,workspace:dict[str,Any],
                               dependencies:list[dict[str,Any]],
                               upgradeCandidates:dict[str,Any],
                               vulnerabilityScan:dict[str,Any],
                                errors:list[str],
                                contextDocs:list[dict[str,str]] | None=None,)-> tuple[dict[str,Any],dict[str,Any]]:
    """Build a deterministic report and optionally enrich it via LLM and RAG."""
    fallbackReport=buildAnalysisReport(jobId,projectName,workspace,dependencies,upgradeCandidates
                                       ,vulnerabilityScan,errors)
    
    if not settings.enableAiEnrichment:
        fallbackReport["aiReportGeneration"]={
            "enabled": False,
            "status": "SKIPPED",
            "reason": "ENABLE_AI_ENRICHMENT=false"

        }
        return fallbackReport,fallbackReport["aiReportGeneration"]
    
    if settings.aiProvider.lower()=="gemini" and not settings.googleApiKey:
        fallbackReport["aiReportGeneration"]={
            "enabled": True,
            "status": "SKIPPED",
            "reason": "GOOGLE_API_KEY is not configured"

        }
        return fallbackReport,fallbackReport["aiReportGeneration"]
    

    try:
        if contextDocs is None:
            retriever = buildRetriever()
            contextDocs = retrieveReportContext(
                retriever, dependencies, upgradeCandidates, vulnerabilityScan
            )

        if settings.aiCompactReport:
            prompt = buildCompactReportPrompt(
                jobId,
                projectName,
                dependencies,
                upgradeCandidates,
                vulnerabilityScan,
                errors,
                contextDocs,
            )
            enrichment = invokeLLMJson(prompt)
            report = {
                **fallbackReport,
                "aiSummary": enrichment,
                "recommendedFixOrder": enrichment.get("recommendedFixOrder") or fallbackReport.get("recommendedFixOrder", []),
                "citations": sorted(set((enrichment.get("citations") or []) + [doc["source"] for doc in contextDocs])),
            }
        else:
            prompt = buildReportPrompt(
                jobId,
                projectName,
                workspace,
                dependencies,
                upgradeCandidates,
                vulnerabilityScan,
                errors,
                contextDocs,
            )
            report = parseAiReportJson(invokeLLM(prompt))

        report["aiReportGeneration"] = {
            "enabled": True,
            "status": "COMPLETED",
            "provider": settings.aiProvider,
            "model": settings.ollamaModel if settings.aiProvider.lower()=="ollama" else settings.llmModel,
            "embeddingModel": settings.embeddingModel,
            "citations": sorted({doc["source"] for doc in contextDocs}),
        }
        return report, report["aiReportGeneration"]

    except Exception as exc:
        fallbackReport["aiReportGeneration"]={
            "enabled":True,
            "status": "FAILED",
            "reason": str(exc),
            "fallback": "Returned deterministic tool-built report"
        }

        return fallbackReport,fallbackReport["aiReportGeneration"]
    
def retrieveReportContext(retriever, dependencies, upgradeCandidates, vulnerabilityScan):
    """Retrieve contextual documents for the report using vector and keyword search."""
    queries = []
    for vulnerability in vulnerabilityScan.get("vulnerabilities", [])[:4]:
        queries.append(
            " ".join(
                [
                    vulnerability.get("vulnerabilityId", ""),
                    vulnerability.get("dependencyId", ""),
                    vulnerability.get("severity", ""),
                    str(vulnerability.get("summary", ""))[:240],
                    "security fix migration"
                    
                ]
            )
        )
    

    for update in upgradeCandidates.get("dependencyUpdates", [])[:4]:
        queries.append(
            " ".join(
                [
                    update.get("dependencyId", ""),
                    update.get("currentVersion", ""),
                    update.get("latestVersion", ""),
                    update.get("updateType", ""),
                    "upgrade breaking changes migration"
                ]
            )
        )

    if not queries and dependencies:
        queries.append("JAVA Maven dependency upgrade vulnerability migration guide")

    docsBySourceAndContent:dict[tuple[str,str], dict[str, str]] = {}
    for query in queries[:settings.aiMaxDependencies]:
        for doc in retriever.invoke(query):
            source=str(doc.metadata.get("source")or doc.metadata.get("filename") or "unknown")
            key=(source,doc.page_content)
            docsBySourceAndContent[key]={
                "source": source,
                "content": doc.page_content,
                "retrieval":"vector"
            }        

        for doc in keywordSearchContext(query):
            key=(doc["source"],doc["content"])
            docsBySourceAndContent[key]=doc
    
    return compactContextDocs(list(docsBySourceAndContent.values())[:settings.ragTopK])


def createFixPlanWithAi(report:dict[str,Any],
                            selectedDependencies:list[dict[str,Any]],
                            fixBy:str,
                            value:str,
                            contextDocs:list[dict[str,str]])-> dict[str,Any]:
    """Ask the LLM for a fix plan from selected dependencies and RAG context."""
    fallback={"status":"FALLBACK",
              "dependencies": selectedDependencies,
              "instructions":"Review and approve the planned dependency changes."}
    if ai_disabled():
        return fallback

    try:
        if contextDocs is None:
            contextDocs = retrieveFixContext(selectedDependencies)

        prompt = buildFixPlanPrompt(
            fixBy,
            value,
            selectedDependencies,
            compactContextDocs(contextDocs[0 : settings.ragTopK]),
        )
        plan = invokeLLMJson(prompt)
        if not plan.get("dependencies"):
            plan["dependencies"] = selectedDependencies
        plan.setdefault("requiresApproval", True)
        return plan
    except Exception:
        return fallback

def retrieveAnalysisContext(
        dependencies:list[dict[str,Any]],
        upgradeCandidates:dict[str,Any],
        vulnerabilityScan:dict[str,Any],
) -> list[dict[str,str]]:
    """Entry point for analyze-graph RAG retrieval."""
    if ai_disabled():
        return []

    retriever=buildRetriever()
    return retrieveReportContext(retriever,dependencies,upgradeCandidates,vulnerabilityScan)

def retrieveFixContext(
        dependencies:list[dict[str,Any]],
) -> list[dict[str,str]]:
    """Retrieve RAG context for each selected dependency during fix planning."""
    if ai_disabled():
        return []

    retriever=buildRetriever()
    contextDocs=[]
    for dep in dependencies[:settings.aiMaxDependencies]:
        contextDocs.extend(retrieveContext(retriever,dep))
    
    return compactContextDocs(dedupeContextDocs(contextDocs)[:settings.ragTopK])


def createSelfCorrectionPlanWithAi(fixPlan:dict[str,Any],
                                   resolution:dict[str,Any],
                                   failureAnalysis:dict[str,Any],
                                   selectedDependencies:list[dict[str,Any]],
                                   iteration:int) -> dict[str,Any]:
    """Ask the LLM for a self-correction plan after a failed fix iteration."""
    fallback = {
        "status": "FALLBACK",
        "selectedTool": "suggestVersionBumpRetry",
        "updatedFixPlan": {
            "instructions": "Retry only if the same dependencies still have a concrete recommendedVersion or latestVersion.",
            "dependencies": selectedDependencies,
            "fixStrategy": fixPlan.get("fixStrategy", "VERSION_BUMP"),
        },
        "reason": "Default self-correction plan",
        "stopRetry": False,
    }
    if ai_disabled():
        return fallback
    
    try:
        prompt=buildSelfCorrectionPrompt(fixPlan,resolution,failureAnalysis,selectedDependencies,tool_descriptions(),iteration)
        correction = invokeLLMJson(prompt)
        updated = correction.setdefault("updatedFixPlan", {})
        if not updated.get("dependencies"):
            updated["dependencies"] = selectedDependencies
        return correction
    except Exception as exc:
        return {**fallback, "reason": f"Self-Correction planner Failed: {exc}"}


def evaluateResolutionWithAi(fixBy:str,value:str,fixStrategy:str,
                                selectedDependencies:list[dict[str,Any]],
                                rescanReport:dict[str,Any],
                                testResult:dict[str,Any],
                                iteration:int
                                 )-> dict[str,Any]:
    """Evaluate whether a fix iteration resolved targets; combines deterministic and LLM checks."""
    remaining=remainingMatchingDependencies(rescanReport,fixBy,value,fixStrategy)
    deterministicResolved=not remaining and testResult.get("success",True)

    fallback = {
        "status": "RESOLVED" if deterministicResolved else "UNRESOLVED",
        "resolved": deterministicResolved,
        "remainingVulnerabilities": remaining,
        "iteration": iteration,
        "reason": "Deterministic resolution check based on rescan report and test result",
        "nextAction": "Stop" if deterministicResolved else "Retry or manual review",
    }

    if ai_disabled():
        return fallback

    try:
        prompt=buildResolutionEvaluationPrompt(fixBy,value,fixStrategy,selectedDependencies,remaining,testResult,iteration)
        decision = invokeLLMJson(prompt)
        if remaining or (testResult and testResult.get("success") is False):
            decision["resolved"] = False
            decision["status"] = "UNRESOLVED"
        decision["remainingVulnerabilities"] = remaining
        decision.setdefault("iteration", iteration)
        return decision
    except Exception as exc:
       return {**fallback, "reason": f"Resolution Evaluator Failed {exc}"}

def analyzeFailureLogsWithAi(selectedDependencies:list[dict[str,Any]],
                             testResult:dict[str,Any],
                             fixPlan: dict[str,Any])-> dict[str,Any]:
    """Diagnose Maven test/build failures from stdout/stderr using the LLM."""
    if testResult.get("success",True):
        return {"status":"SKIPPED","reason":"Validation passed or was skipped"}
    
    fallback={
        "status":"FALLBACK",
        "failureType":"UNKNOWN",
        "summary":"Maven validation failed",
        "suggestedNextActions":["Inspect maven test.log and retry with a narrower fix"],

    }
    if ai_disabled():
        return fallback
    
    try:
        stdout=(testResult.get("stdout") or "")[-settings.aiMaxLogChars:]
        stderr=(testResult.get("stderr") or "")[-settings.aiMaxLogChars:]
        prompt=buildFailureAnalysisPrompt(selectedDependencies,fixPlan,stdout,stderr)
        return invokeLLMJson(prompt)
    except Exception as exc:
           return {**fallback, "summary": f"Failure Analysis Failed {exc}"}
    

def remainingMatchingDependencies(report:dict[str,Any],
                                  fixBy:str,value:str,
                                  fixStrategy:str | None=None,)-> list[dict[str,Any]]:
    """Filter the rescan report for dependencies still matching the original fix criteria."""
    remaining=[]
    for dependency in report.get("dependencies",[]):
        if not dependency.get("vulnerabilityIds"):
            continue
        if fixStrategy and dependency.get("fixStrategy") not in {fixStrategy,"MANUAL_REVIEW_REQUIRED"}:
            continue
        if fixBy=="ALL":
            remaining.append(dependency)
        elif fixBy=="CATEGORY" and dependency.get("category")==value:
            remaining.append(dependency)
        elif fixBy == "IDS" and dependency.get("dependencyId") in set(value.split(",")):
            remaining.append(dependency)
    return remaining


def parseAiReportJson(text:str):
    """Parse LLM report JSON, handling optional markdown code fences."""
    return parseLooseJson(text)

def parseLooseJson(text:str):
    """Strip code fences and parse JSON from LLM output."""
    cleaned=text.strip()
    if cleaned.startswith("```json"):
        cleaned=cleaned.removeprefix("```json").removesuffix("```").strip()
    elif cleaned.startswith("```"):
        cleaned=cleaned.removeprefix("```").removesuffix("```").strip()
    return json.loads(cleaned)

def buildRetriever():
    """Return a cached Qdrant vector retriever (singleton per process)."""
    global _retrieverCache
    if _retrieverCache is not None:
        return _retrieverCache
    
    from langchain_qdrant import QdrantVectorStore

    embeddings = buildEmbeddings()
    vectorStore=QdrantVectorStore.from_existing_collection(
                collection_name=settings.qdrantCollection,
                embedding=embeddings,
                url=settings.qdrantUrl)
    _retrieverCache=vectorStore.as_retriever(search_type="similarity", search_kwargs={"k":settings.ragTopK})
    return _retrieverCache


def retrieveContext(retriever,dependency):
    """Retrieve vector and keyword docs for a single dependency."""
    query=buildRagQuery(dependency)
    docs=[
        {
            "content": doc.page_content,
            "source": str(doc.metadata.get("source") or doc.metadata.get("fileName") or "unknown"),
            "retrieval": "vector"
        }
        for doc in retriever.invoke(query)
    ]
    keywordDocs=filterDependencyKeywordDocs(keywordSearchContext(query), dependency)
    docs.extend(keywordDocs)
    docs=filterDependencyKeywordDocs(dedupeContextDocs(docs), dependency)
    return compactContextDocs(docs[:settings.ragTopK])

def filterDependencyKeywordDocs(docs:list[dict[str,Any]], dependency:dict[str,Any]) -> list[dict[str,Any]]:
    """Prefer local RAG docs that mention the selected dependency coordinates."""
    artifactId=str(dependency.get("artifactId") or "")
    groupId=str(dependency.get("groupId") or "")
    dependencyId=str(dependency.get("dependencyId") or "")
    terms={
        term.lower()
        for term in [
            artifactId,
            artifactId.split("-")[0] if artifactId else "",
            groupId.split(".")[-1] if groupId else "",
            dependencyId,
        ]
        if len(term) >= 4
    }
    if not terms:
        return docs
    return [
        doc for doc in docs
        if any(term in f"{doc.get('source','')} {doc.get('content','')}".lower() for term in terms)
    ]

def buildRagQuery(dependency: dict[str,Any])->str:
    """Build a search query from dependency metadata and vulnerability IDs."""
    return " ".join([
            dependency.get("dependencyId") or "",
            dependency.get("category") or "",
            dependency.get("fixStrategy") or "",
            dependency.get("reason") or "",
            " ".join(str(v) for v in dependency.get('vulnerabilityIds',[]) if v),
            f"from {dependency.get('currentVersion') or ''}",
            f"to {dependency.get('recommendedVersion') or dependency.get('latestVersion') or ''}",
            "migration breaking changes remediation OpenRewrite Maven Java"]
    )

def keywordSearchContext(query):
    """Score local markdown files by term overlap as a keyword-search fallback."""
    terms={term.lower() for term in query.split() if len(term)>=4}
    scored=[]
    for document in loadKeywordRagSources():
        contentLower=document["content"].lower()
        score=sum(1 for term in terms if term in contentLower)
        if score:
            scored.append((score,document))
    scored.sort(key=lambda x: x[0],reverse=True)
    return [
        {**document,"retrieval":"keyword","score":score}
        for score,document in scored[:settings.ragTopK]
    ]

def loadKeywordRagSources():
    """Load all rag-docs/*.md files for keyword fallback search."""
    sources=[]
    for path in sorted(Path(settings.ragDocsDir).glob("*.md")):
        sources.append(
            {
                "source":str(path),
                "sourceType":"migrationDoc",
                "content":path.read_text(encoding="utf-8")
            }
        )
    return sources


def dedupeContextDocs(docs):
    """Deduplicate context documents by (source, content) pairs."""
    seen=set()
    unique=[]
    for d in docs:
        key=(d.get("source"),d.get("content"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(d)
    return unique


def compactContextDocs(docs:list[dict[str,Any]]) -> list[dict[str,Any]]:
    """Trim retrieved documents before embedding them in LLM prompts."""
    compact=[]
    for doc in docs:
        content=str(doc.get("content",""))
        compact.append({
            **doc,
            "content": content[:settings.aiMaxContextChars],
        })
    return compact
    
