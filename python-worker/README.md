# Python Worker Service

FastAPI skeleton for the dependency analyzer worker. This service will later host the LangChain/LangGraph pipeline, Qdrant retrieval, RAG over migration guides, repository extraction, fixes, tests, and report rebuilds.

## Current Scope

- Mock `POST /analyze`
- Mock `POST /fix`
- `GET /health`
- Shared report/request response schema with the Java microservice

## Planned Stack

- Python 3.12+
- FastAPI
- LangChain
- LangGraph
- Qdrant
- RAG over migration guides and official documentation

## Run

```powershell
cd python-worker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8090
```

## Worker Flow

1. Receive repository storage path from Java.
2. Extract zip into an isolated temporary workspace.
3. Detect build tool and Java ecosystem metadata.
4. Generate dependency inventory.
5. Retrieve migration docs from Qdrant.
6. Produce a structured dependency report.
7. Accept fix request by `jobId`, `dependencyId`, `priority`, and `category`.
8. Apply focused fix.
9. Run tests/build.
10. Rebuild report and return updated result.
