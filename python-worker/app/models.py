"""Pydantic request/response schemas shared with the Java microservice."""

from typing import Any,Literal

from pydantic import BaseModel, Field



class AnalyzeRequest(BaseModel):
    """Request to analyze a Maven project from a ZIP path on disk."""

    jobId: str = Field()
    projectName: str = Field()
    zipPath: str = Field()

class FixPlanRequest(BaseModel):
    """Request to create a fix plan from a stored analysis report."""

    jobId:str = Field()
    analysisJobId: str=Field()
    fixBy: Literal["IDS","CATEGORY","ALL"]
    dependencyIds: list[str] = []
    category: str | None = None

class ApplyFixRequest(BaseModel):
    """Request to execute a stored fix plan."""

    jobId:str = Field()
    fixPlanId: str=Field()
    approved: bool=False


class HealthResponse(BaseModel):
    """Health check response with service status and RAG index status."""

    status: str
    
    ragIndex: dict[str, Any]
    ai: dict[str, Any] = {}


class WorkerResponse(BaseModel):
    """Unified API response envelope for analyze, fix-plan, and apply-fix jobs."""

    success: bool
    jobId: str
    status: Literal["COMPLETED","FAILED"]
    message:str
    report: dict[str,Any] | None=None
    fixReport: dict[str,Any] | None=None
    fixPlan: dict[str,Any] | None=None
    errors: list[str]=[]
