# Agentic AI Dependency Upgrade Assistant

Python worker for analyzing Java/Maven dependency risk, creating an AI-assisted fix plan, and applying approved dependency version updates.

The FastAPI worker extracts projects, analyzes dependencies, creates fix plans, applies changes, and returns patch artifacts. These three APIs drive the dependency upgrade flow:

1. `POST /worker/analyze`
2. `POST /worker/fixPlan`
3. `POST /worker/applyFix`

## Worker Flow

```text
Project ZIP
   |
   v
/worker/analyze
   - extracts project
   - detects Maven root
   - generates SBOM
   - detects upgrade candidates
   - scans vulnerabilities
   - builds dependency report
   - stores report by jobId
   |
   v
/worker/fixPlan
   - reads stored analysis report
   - selects dependencies by IDS, CATEGORY, or ALL
   - retrieves migration/RAG context
   - creates planned dependency changes
   - stores fix plan by fixPlanId
   |
   v
/worker/applyFix
   - reads stored fix plan
   - requires approved=true
   - prepares isolated fix workspace
   - applies planned pom.xml updates
   - writes patch artifact
   - returns compact fix result
```

The original uploaded project is not edited directly. Fixes are applied in a copied workspace and returned as a patch file.

## Persistence

The Python worker keeps analysis reports and fix plans in memory while running, and also persists them under:

```text
data/state/analysis-store.json
data/state/fix-plan-store.json
```

On worker restart, these files are loaded back into memory.

That means after a restart you can call `/worker/applyFix` with an existing `fixPlanId` without rerunning `/worker/analyze` and `/worker/fixPlan`, as long as the `data` directory is preserved.

Generated artifacts are written under:

```text
data/artifacts/<fixJobId>/upgrade.patch
data/workspaces/<fixJobId>/fix-source/
```

Inside Docker these paths appear as:

```text
/app/data/artifacts/<fixJobId>/upgrade.patch
/app/data/workspaces/<fixJobId>/fix-source/
```

## API 1: Analyze

Creates a dependency report from a project ZIP that already exists on disk.

```http
POST /worker/analyze
Content-Type: application/json
```

Request:

```json
{
  "jobId": "job3",
  "projectName": "sample-maven-app",
  "zipPath": "/app/data/uploads/job3/project.zip"
}
```

Response:

```json
{
  "success": true,
  "jobId": "job3",
  "status": "COMPLETED",
  "message": "Analysis completed",
  "report": {
    "jobId": "job3",
    "projectName": "sample-maven-app",
    "dependencies": []
  },
  "fixReport": null,
  "fixPlan": null,
  "errors": []
}
```

What it does:

- Validates the ZIP path.
- Extracts the ZIP into `data/workspaces/<jobId>/source`.
- Detects the Maven reactor root.
- Generates dependency evidence.
- Builds a report.
- Stores the report using `jobId`.

Command:

```bash
curl -X POST http://localhost:8123/worker/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "jobId": "job3",
    "projectName": "sample-maven-app",
    "zipPath": "/app/data/uploads/job3/project.zip"
  }'
```

PowerShell:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8123/worker/analyze" `
  -ContentType "application/json" `
  -Body '{
    "jobId": "job3",
    "projectName": "sample-maven-app",
    "zipPath": "/app/data/uploads/job3/project.zip"
  }'
```

## API 2: Fix Plan

Creates a fix plan from a previously stored analysis report.

```http
POST /worker/fixPlan
Content-Type: application/json
```

Request by dependency IDs:

```json
{
  "jobId": "fixPlanjob1",
  "analysisJobId": "job3",
  "fixBy": "IDS",
  "dependencyIds": [
    "org.apache.logging.log4j:log4j-core"
  ],
  "category": null
}
```

Request by category:

```json
{
  "jobId": "fixPlanjob2",
  "analysisJobId": "job3",
  "fixBy": "CATEGORY",
  "dependencyIds": [],
  "category": "SECURITY"
}
```

Request for all vulnerable dependencies:

```json
{
  "jobId": "fixPlanjob3",
  "analysisJobId": "job3",
  "fixBy": "ALL",
  "dependencyIds": [],
  "category": null
}
```

Response:

```json
{
  "success": true,
  "jobId": "fixPlanjob1",
  "status": "COMPLETED",
  "message": "FIX PLAN CREATED",
  "report": null,
  "fixReport": null,
  "fixPlan": {
    "fixPlanId": "fixPlanjob1",
    "analysisJobId": "job3",
    "fixBy": "IDS",
    "value": "org.apache.logging.log4j:log4j-core",
    "status": "PLANNED",
    "dependencyIds": [
      "org.apache.logging.log4j:log4j-core"
    ],
    "plannedChanges": [
      {
        "file": "pom.xml",
        "dependency": "org.apache.logging.log4j:log4j-core",
        "fromVersion": "2.14.1",
        "toVersion": "2.25.4",
        "changeType": "DEPENDENCY_VERSION_UPDATE"
      }
    ],
    "requiresApproval": true
  },
  "errors": []
}
```

What it does:

- Loads the analysis report using `analysisJobId`.
- Selects target dependencies by `fixBy`.
- Creates normalized `plannedChanges`.
- Requires approval before applying.
- Stores the plan using `fixPlanId`.

Supported `fixBy` values:

- `IDS`: fix only dependencies listed in `dependencyIds`.
- `CATEGORY`: fix dependencies matching `category`.
- `ALL`: fix all vulnerable dependencies in the report.

Command:

```bash
curl -X POST http://localhost:8123/worker/fixPlan \
  -H "Content-Type: application/json" \
  -d '{
    "jobId": "fixPlanjob1",
    "analysisJobId": "job3",
    "fixBy": "IDS",
    "dependencyIds": [
      "org.apache.logging.log4j:log4j-core"
    ],
    "category": null
  }'
```

PowerShell:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8123/worker/fixPlan" `
  -ContentType "application/json" `
  -Body '{
    "jobId": "fixPlanjob1",
    "analysisJobId": "job3",
    "fixBy": "IDS",
    "dependencyIds": [
      "org.apache.logging.log4j:log4j-core"
    ],
    "category": null
  }'
```

## API 3: Apply Fix

Applies a stored fix plan. The request body stays small and only approves an existing plan.

```http
POST /worker/applyFix
Content-Type: application/json
```

Request:

```json
{
  "jobId": "applyFixjob1",
  "fixPlanId": "fixPlanjob1",
  "approved": true
}
```

Response:

```json
{
  "success": true,
  "jobId": "applyFixjob1",
  "status": "COMPLETED",
  "message": "FIX APPLIED",
  "report": null,
  "fixReport": {
    "jobId": "applyFixjob1",
    "analysisJobId": "job3",
    "status": "COMPLETED",
    "message": "Applied 1 planned changes; 0 failed to update",
    "fixedDependencies": [
      {
        "file": "pom.xml",
        "dependency": "org.apache.logging.log4j:log4j-core",
        "fromVersion": "2.14.1",
        "toVersion": "2.25.4",
        "changeType": "DEPENDENCY_VERSION_UPDATE"
      }
    ],
    "failedDependencies": [],
    "patchPath": "/app/data/artifacts/applyFixjob1/upgrade.patch",
    "errors": []
  },
  "fixPlan": null,
  "errors": []
}
```

What it does:

- Loads the stored fix plan using `fixPlanId`.
- Verifies `approved=true`.
- Re-extracts the original analysis ZIP.
- Creates an original snapshot.
- Copies the project into a fix workspace.
- Updates matching `pom.xml` dependency versions.
- Generates `upgrade.patch`.
- Returns only the compact fix outcome.

To view the patch inside Docker:

```bash
docker exec -it dependency-agent-worker cat /app/data/artifacts/applyFixjob1/upgrade.patch
```

To inspect the fixed `pom.xml` inside Docker:

```bash
docker exec -it dependency-agent-worker cat /app/data/workspaces/applyFixjob1/fix-source/pom.xml
```

Command:

```bash
curl -X POST http://localhost:8123/worker/applyFix \
  -H "Content-Type: application/json" \
  -d '{
    "jobId": "applyFixjob1",
    "fixPlanId": "fixPlanjob1",
    "approved": true
  }'
```

PowerShell:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8123/worker/applyFix" `
  -ContentType "application/json" `
  -Body '{
    "jobId": "applyFixjob1",
    "fixPlanId": "fixPlanjob1",
    "approved": true
  }'
```

## Approval Behavior

If `approved` is false, the worker does not apply changes.

```json
{
  "jobId": "applyFixjob1",
  "fixPlanId": "fixPlanjob1",
  "approved": false
}
```

The plan remains available, but the apply step is blocked by approval guardrails.

## Health

```http
GET /health
```

Returns service status, RAG index status, and AI provider configuration.

Command:

```bash
curl http://localhost:8123/health
```

PowerShell:

```powershell
Invoke-RestMethod -Uri "http://localhost:8123/health"
```

## Useful Docker Commands

Start the Python worker stack from the worker folder:

```bash
cd python-worker
docker compose up --build
```

Run in the background:

```bash
cd python-worker
docker compose up -d --build
```

View worker logs:

```bash
docker logs -f dependency-agent-worker
```

Open a shell inside the worker:

```bash
docker exec -it dependency-agent-worker sh
```

View persisted worker stores:

```bash
docker exec -it dependency-agent-worker cat /app/data/state/analysis-store.json
docker exec -it dependency-agent-worker cat /app/data/state/fix-plan-store.json
```

View generated patch:

```bash
docker exec -it dependency-agent-worker cat /app/data/artifacts/applyFixjob1/upgrade.patch
```

View fixed project file:

```bash
docker exec -it dependency-agent-worker cat /app/data/workspaces/applyFixjob1/fix-source/pom.xml
```

## Run Locally

```powershell
cd python-worker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8123
```

## Important Files

```text
python-worker/app/main.py              FastAPI endpoints and persisted worker stores
python-worker/app/graph.py             Analyze, fix-plan, and apply-fix graph nodes
python-worker/app/models.py            Request/response schemas
python-worker/app/tools/file_tools.py  ZIP extraction and workspace preparation
python-worker/app/tools/fix_tools.py   POM version edits and patch generation
```
