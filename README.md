# Dependency Upgrade Agent Backend

Spring Boot 3 backend for a personal Java dependency upgrade agent. It accepts `repo.zip` uploads, stores them on local disk, persists job metadata in PostgreSQL, and exposes analysis, fix, and report APIs. The Python LangGraph worker is represented by a mocked `WorkerClient` interface for now.

## Stack

- Java 21
- Spring Boot 3
- Maven
- Spring Web
- Spring Data JPA
- PostgreSQL
- Bean Validation

## Run

Create a PostgreSQL database and set connection variables:

```powershell
docker compose up -d postgres
$env:DB_URL="jdbc:postgresql://localhost:5432/dependency_agent"
$env:DB_USERNAME="postgres"
$env:DB_PASSWORD="postgres"
.\mvnw.cmd spring-boot:run
```

Uploaded archives are stored under `./uploads` by default. Override with:

```powershell
$env:APP_STORAGE_ROOT="C:\path\to\uploads"
```

## API

- `POST /api/jobs` multipart upload with field `file`, optional `name`. Stores the zip and starts analysis. Returns `jobId`.
- `GET /api/jobs` returns the status of all analysis jobs.
- `GET /api/jobs/{jobId}` returns the status of one analysis job.
- `GET /api/jobs/{jobId}/report` returns the analysis report for one job.
- `POST /api/jobs/{jobId}/fix` starts a fix job for an analysis job.

Fix request body:

```json
{
  "priority": "critical",
  "dependencyId": "org.springframework.boot:spring-boot-starter-web",
  "category": "version_bump"
}
```

Supported priorities: `critical`, `high`, `medium`, `low`.

Supported categories: `version_bump`, `parentUpgrade`.

## Dependency Analyzer Agent Roadmap

The target product flow is:

1. Upload repository zip.
2. Generate full dependency report.
3. View report details.
4. Start fix by category, dependency ID, and priority.
5. Run tests.
6. Rebuild report and return the updated result.

### Step 1: API Contract

Status: done for the first minimal version.

Java service endpoints:

- `POST /api/jobs`
- `GET /api/jobs`
- `GET /api/jobs/{jobId}`
- `GET /api/jobs/{jobId}/report`
- `POST /api/jobs/{jobId}/fix`

Upload response:

```json
{
  "jobId": "0d4d43ef-dac7-4b30-98d2-7006ef0d8bb6",
  "status": "ANALYSIS_COMPLETED",
  "createdAt": "2026-06-08T00:00:00Z"
}
```

Job status response:

```json
{
  "jobId": "0d4d43ef-dac7-4b30-98d2-7006ef0d8bb6",
  "status": "ANALYSIS_COMPLETED",
  "repositoryName": "my-service",
  "createdAt": "2026-06-08T00:00:00Z",
  "startedAt": "2026-06-08T00:00:01Z",
  "completedAt": "2026-06-08T00:00:10Z",
  "errorMessage": null
}
```

Fix request:

```json
{
  "priority": "critical",
  "dependencyId": "org.springframework.boot:spring-boot-starter-web",
  "category": "version_bump"
}
```

Fix response includes the fix plan, patch summary, test output, and rebuilt report JSON.

### Step 2: Job State Machine

Status: done for the first minimal version.

Supported states:

- `UPLOADED`
- `ANALYSIS_RUNNING`
- `ANALYSIS_COMPLETED`
- `ANALYSIS_FAILED`
- `FIX_RUNNING`
- `FIX_COMPLETED`
- `FIX_FAILED`
- `TEST_RUNNING`
- `TEST_COMPLETED`
- `TEST_FAILED`
- `REPORT_REBUILDING`
- `COMPLETED`
- `FAILED`

The current mock flow is synchronous. The future production flow should move worker calls to async dispatch and update these states from worker callbacks or polling.

### Step 3: Python Worker Service

Status: skeleton created in `python-worker`.

Current worker endpoints:

- `GET /health`
- `POST /analyze`
- `POST /fix`

Planned worker responsibilities:

1. Extract uploaded zip into an isolated temporary workspace.
2. Detect Maven or Gradle.
3. Build dependency inventory.
4. Use Qdrant-backed RAG over migration guides and documentation.
5. Generate the dependency report.
6. Apply focused fixes.
7. Run tests/build.
8. Rebuild and return the updated report.

### Step 4: Report Model

Status: done for the first minimal version.

Report fields:

```json
{
  "jobId": "0d4d43ef-dac7-4b30-98d2-7006ef0d8bb6",
  "repositoryName": "my-service",
  "buildTool": "maven",
  "generatedAt": "2026-06-08T00:00:00Z",
  "findings": [
    {
      "dependencyId": "org.springframework.boot:spring-boot-starter-web",
      "groupId": "org.springframework.boot",
      "artifactId": "spring-boot-starter-web",
      "currentVersion": "3.2.0",
      "recommendedVersion": "3.3.6",
      "latestVersion": "3.3.6",
      "scope": "compile",
      "usageLocation": "pom.xml",
      "priority": "medium",
      "category": "version_bump",
      "reason": "Upgrade recommended based on migration docs and compatibility checks.",
      "migrationGuideRefs": [
        {
          "title": "Spring Boot 3.3 Migration Guide",
          "source": "spring.io",
          "url": "https://github.com/spring-projects/spring-boot/wiki",
          "relevanceScore": 0.92
        }
      ],
      "fixAvailable": true
    }
  ],
  "summary": {
    "totalDependencies": 20,
    "upgradeCandidates": 5,
    "criticalCount": 1,
    "highCount": 2,
    "mediumCount": 2,
    "lowCount": 0
  }
}
```

The Java service currently persists report JSON as text. A future migration can move this to PostgreSQL `jsonb` once querying report internals becomes necessary.

## Next Engineering Steps

1. Replace the Java `MockWorkerClient` with an HTTP worker client for `python-worker`.
2. Make job execution asynchronous.
3. Add zip extraction and Maven project detection in Python.
4. Add Qdrant ingestion for migration guides and official docs.
5. Implement LangGraph nodes for inventory, RAG retrieval, risk scoring, report generation, fix planning, test execution, and report rebuild.
6. Implement Zip Extraction And Project Detection
   Worker should:
   unzip repo
   detect Maven/Gradle
   find pom.xml, parent POMs, modules
   parse dependency tree
   identify Java/Spring Boot version
   identify plugins
   identify test commands
   For Maven, start with:

mvn dependency:tree
mvn versions:display-dependency-updates
mvn versions:display-plugin-updates
Add Qdrant RAG
Store migration guides/docs as chunks with metadata:
source
framework
artifact
fromVersion
toVersion
category
url
chunkText
Good first docs:

Spring Boot migration guides
Spring Framework migration guides
Hibernate ORM migration guides
JUnit migration notes
Maven plugin docs
popular library changelogs
Build LangGraph Flow
A sensible graph:
ExtractRepo
DetectBuildTool
GenerateDependencyInventory
FindUpgradeCandidates
RetrieveMigrationDocs
AssessRiskAndPriority
GenerateReport
WaitForFixRequest
PlanFix
ApplyFix
RunTests
RebuildReport
ReturnResult
Make Fixes Narrow
For the first version, support only:
direct dependency version bump
parent POM upgrade
simple plugin version bump
Do not try broad code migrations yet.
