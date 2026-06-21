"""FastAPI entry point for the dependency analyzer worker.

Exposes health, analyze, fix-plan, and apply-fix endpoints. Each endpoint
delegates to a compiled LangGraph pipeline defined in ``app.graph``.
"""

import logging
import json
from fastapi import FastAPI,File,Form,HTTPException,UploadFile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any


from app.models import (
    AnalyzeRequest,
    ApplyFixRequest,
    FixPlanRequest,
    HealthResponse,
    WorkerResponse
)
from app.config import settings
from app.tools.file_tools import ProjectExtractionError,safeJobPath
from app.rag_indexer import ensureRagIndex,getRagIndexStatus
from app.graph import (
    buildAnalyzeGraph,
    buildFixPlanGraph,
    buildApplyFixGraph,
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan hook: initialize RAG indexing in background."""
    import threading

    loadWorkerStores()
    
    # Start RAG indexing in background thread so app can start immediately
    def index_rag():
        try:
            ensureRagIndex()
        except Exception:
            pass  # Continue serving even if RAG indexing fails
    
    thread = threading.Thread(target=index_rag, daemon=True)
    thread.start()
    yield





app = FastAPI(title="Dependency Analyzer Worker", version="0.1.0",lifespan=lifespan)

analyzeGraph=buildAnalyzeGraph()
fixPlanGraph=buildFixPlanGraph()
applyFixGraph=buildApplyFixGraph()
UPLOAD_CHUNK_SIZE=1024*1024

analysisStore:dict[str,dict[str,Any]]={}
fixPlanStore:dict[str,dict[str,Any]]={}
STATE_DIR=settings.data_dir/"state"
ANALYSIS_STORE_PATH=STATE_DIR/"analysis-store.json"
FIX_PLAN_STORE_PATH=STATE_DIR/"fix-plan-store.json"


def loadJsonStore(path:Path) -> dict[str,dict[str,Any]]:
    """Load a persisted worker store, returning an empty store if absent/corrupt."""
    if not path.exists():
        return {}
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data,dict) else {}
    except Exception:
        logger.exception("Failed to load worker store from %s", path)
        return {}


def saveJsonStore(path:Path,store:dict[str,dict[str,Any]]) -> None:
    """Persist a worker store to disk."""
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(store,ensure_ascii=False,default=str),encoding="utf-8")


def loadWorkerStores() -> None:
    """Restore analysis and fix-plan stores after worker restart."""
    analysisStore.update(loadJsonStore(ANALYSIS_STORE_PATH))
    fixPlanStore.update(loadJsonStore(FIX_PLAN_STORE_PATH))




@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return service health and the RAG index status from startup indexing."""
    key=settings.googleApiKey or ""
    keyFingerprint=f"{key[:4]}...{key[-4:]}" if len(key) >= 8 else ""
    return HealthResponse(
        status="ok",
        ragIndex=getRagIndexStatus(),
        ai={
            "enabled": settings.enableAiEnrichment,
            "provider": settings.aiProvider,
            "model": settings.llmModel,
            "ollamaModel": settings.ollamaModel,
            "ollamaBaseUrl": settings.ollamaBaseUrl,
            "ollamaTimeoutSeconds": settings.ollamaTimeoutSeconds,
            "embeddingModel": settings.embeddingModel,
            "googleApiKeyConfigured": bool(key),
            "googleApiKeyFingerprint": keyFingerprint,
            "maxOutputTokens": settings.aiMaxOutputTokens,
            "maxContextChars": settings.aiMaxContextChars,
        },
    )

@app.post("/worker/analyze",response_model=WorkerResponse)
def analyze(request: AnalyzeRequest):
    """Analyze a project from a ZIP path already on disk (called by Java microservice)."""
    return runAnalysis(request.jobId,request.projectName,request.zipPath)


@app.post("/worker/analyze-upload", response_model=WorkerResponse)
async def analyze_upload(
    jobId:str=Form(min_length=1),
    projectName:str=Form(min_length=1),
    file:UploadFile=File(...),
):
    """Analyze a project from an uploaded ZIP multipart form."""
    zipPath=await saveUploadedZip(jobId,file)
    return runAnalysis(jobId,projectName,str(zipPath))

def runAnalysis(jobId,projectName,zipPath)-> WorkerResponse:
    """Run the analyze LangGraph and wrap the result as a WorkerResponse."""
    result=analyzeGraph.invoke({
        "jobId": jobId,
        "projectName": projectName,
        "zipPath": zipPath,
        "errors": []
    })
    report=result.get("report",{})
    report["inputZipPath"]=zipPath
    success=bool(report.get("dependencies") is not None)
    analysisStore[jobId]={
        "jobId":jobId,
        "projectName":projectName,
        "zipPath":zipPath,
        "report":report,
    }
    saveJsonStore(ANALYSIS_STORE_PATH,analysisStore)
    return WorkerResponse(success=success,jobId=jobId,
                         status="COMPLETED" if success else "FAILED",
                          message="Analysis completed" if success else "Analysis completed with errors",
                          report=report,
                          errors=result.get("errors",[]))



async def saveUploadedZip(jobId,file):
    """Stream-upload a ZIP with size limits; validate extension and jobId.

    Returns:
        Path to the saved ZIP file under the configured uploads directory.
    """
    orignalName=Path(file.filename or "project.zip").name
    if not orignalName.lower().endswith(".zip"):
        raise HTTPException(status_code=400,detail="Please upload zip file")
    try:
        uploadDir= safeJobPath(settings.uploads_dir,jobId)
    except ProjectExtractionError as ex:
        raise  HTTPException(status_code=400,detail=str(ex))
    uploadDir.mkdir(parents=True,exist_ok=True)
    destination=uploadDir/orignalName

    total=0
    with destination.open("wb") as output:
        while chunk :=await file.read(UPLOAD_CHUNK_SIZE):
            total+=len(chunk)
            if total>settings.maxZipBytes:
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=413,detail="Uploaded Zip exceeds limit")
            output.write(chunk)

    return destination




@app.post("/worker/fixPlan", response_model=WorkerResponse)
def fixPlan(request: FixPlanRequest):
    """Run the fix-plan graph: select findings, RAG context, AI plan, approval metadata."""
    analysis=analysisStore.get(request.analysisJobId)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Analysis report not found for jobId '{request.analysisJobId}'")

    value=request.category or ",".join(request.dependencyIds)
    result=fixPlanGraph.invoke({
        "jobId":request.jobId,
        "analysisJobId":request.analysisJobId,
        "zipPath":analysis["zipPath"],
        "report":analysis["report"],
        "fixBy":request.fixBy,
        "value":value,
        "dependencyIds":request.dependencyIds,
        "approved":False,
        "errors":[],
    })
    plan=result.get("fixPlan",{})
    success=bool(plan.get("status")=="PLANNED" and not result.get("errors"))
    if plan:
        fixPlanStore[plan.get("fixPlanId") or request.jobId]={
            "jobId":request.jobId,
            "analysisJobId":request.analysisJobId,
            "zipPath":analysis["zipPath"],
            "report":analysis["report"],
            "fixPlan":plan,
        }
        saveJsonStore(FIX_PLAN_STORE_PATH,fixPlanStore)
    return WorkerResponse(success=success,jobId=request.jobId,status="COMPLETED" if success else "FAILED",
                          message="FIX PLAN CREATED" if success else "FIX PLAN completed with errors",
                          fixPlan=plan,
                          errors=result.get("errors",[]))



@app.post("/worker/applyFix", response_model=WorkerResponse)
def applyFix(request: ApplyFixRequest):
    """Run the apply-fix graph: approval gate, apply bumps, test, rescan, self-correct loop."""
    storedPlan=fixPlanStore.get(request.fixPlanId)
    if not storedPlan:
        raise HTTPException(status_code=404, detail=f"Fix plan not found for fixPlanId '{request.fixPlanId}'")

    plan=storedPlan["fixPlan"]
    result=applyFixGraph.invoke({
        "jobId":request.jobId,
        "analysisJobId":storedPlan["analysisJobId"],
        "zipPath":storedPlan["zipPath"],
        "report":storedPlan["report"],
        "fixPlan":plan,
        "fixBy":plan.get("fixBy","ALL"),
        "value":plan.get("value",""),
        "approved":request.approved,
        "selectedDependencies":plan.get("dependencies",[]),
        "fixIteration":0,
        "errors":[],
    })
    
    fixReport=result.get("fixReport",{})
    responseFixReport=buildApplyFixResponseReport(fixReport)
    success=bool(fixReport.get("status")=="COMPLETED")
    return WorkerResponse(success=success,jobId=request.jobId,status="COMPLETED" if success else "FAILED",
                          message="FIX APPLIED" if success else "FIX NOT APPLIED DUE TO errors",
                          fixReport=responseFixReport,
                          errors=responseFixReport.get("errors",[]))


def buildApplyFixResponseReport(fixReport:dict[str,Any]) -> dict[str,Any]:
    """Return only apply-fix outcome fields needed by the caller."""
    return {
        "jobId":fixReport.get("jobId"),
        "analysisJobId":fixReport.get("analysisJobId"),
        "status":fixReport.get("status"),
        "message":fixReport.get("message"),
        "fixedDependencies":fixReport.get("fixedDependencies",[]),
        "failedDependencies":fixReport.get("failedDependencies",[]),
        "patchPath":fixReport.get("patchPath"),
        "errors":fixReport.get("errors",[]),
    }
