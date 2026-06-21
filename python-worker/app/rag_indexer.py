"""RAG document indexing into Qdrant at application startup.

Indexes markdown migration guides from ``ragDocsDir`` and tracks index version
so re-indexing happens only when docs or embedding config change.
"""

from __future__ import annotations
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
from threading import Lock
from typing import Any

from app.config import settings
from app.llm_factory import buildEmbeddings

_index_lock=Lock()
_index_checked=False
_last_status: dict[str, Any] = {
    "enabled": settings.enableAiEnrichment,
    "status":"NOT_CHECKED"
}


def ensureRagIndex():
    """Ensure local RAG docs are indexed exactly once per app process.

    Re-indexing happens only when docs, config, or embedding model change,
    or when the Qdrant collection is missing.
    """
    global _index_checked, _last_status
    with _index_lock:
        if _index_checked and _last_status.get("status") == "READY":
            # Only cache if we have a successful status
            return _last_status
        
        _last_status = ensureRagIndexUncached()
        if _last_status.get("status") == "READY":
            # Only mark as checked if successful
            _index_checked = True
        return _last_status


def getRagIndexStatus():
    """Return the last RAG indexing status (used by ``GET /health``)."""
    return _last_status

def ensureRagIndexUncached():
    """Check prerequisites and rebuild the Qdrant index when stale or missing."""
    if not settings.enableAiEnrichment:
        return {
            "enabled":False,
            "status":"SKIPPED",
            "reason":"enabled AI encrichment is off"
        }
    
    if not settings.googleApiKey:
        return {
            "enabled":True,
            "status":"SKIPPED",
            "reason":"GOOGLE_API_KEY is not configured"
        }
    
    markdownFiles=getRagMarkdownFiles()
    if not markdownFiles:
        return {
            "enabled":True,
            "status":"SKIPPED",
            "reason":"Markdown files missing"
        }
    
    currentVersion=computeRagIndexVersion(markdownFiles)
    savedState=loadIndexState()
    try:
        collectionExists=qdrantCollectionExists()
        if collectionExists and savedState.get("indexVersion")==currentVersion:
            return{

                **savedState,
                "enabled":True,
                "status":"READY",
                "reindexed":False,
                "reason":"RAG index is already current"
            }
        
        # If collection exists but state doesn't match, skip rebuilding if it has content
        # This prevents unnecessary re-indexing on container restarts after volume persistence
        if collectionExists:
            point_count = getCollectionPointCount()
            if point_count > 0:
                # Collection has data, assume it's valid and return without rebuilding
                return {
                    "enabled": True,
                    "status": "READY",
                    "reindexed": False,
                    "reason": f"RAG index with {point_count} points already exists in Qdrant",
                    "pointCount": point_count,
                }
        
        indexed=rebuildRagIndex(markdownFiles,currentVersion)
        saveIndexState(indexed)
        return{
            **indexed,
            "enabled":True,
            "status":"READY",
            "reindexed":True,
            "reason":"RAG index rebuilt because docs/config changed or collection was missing"
        }
    except Exception as ex:
        return{
            "enabled":True,
            "status":"FAILED",
            "reason":f"RAG indexing failed:{ex}",
            "collection":settings.qdrantCollection,
            "docsDir":str(settings.ragDocsDir),
            "indexVersion":currentVersion
        }


def getRagMarkdownFiles():
    """List all ``*.md`` files under the configured RAG docs directory."""
    return sorted(Path(settings.ragDocsDir).glob("*md"))

def computeRagIndexVersion(markdownFiles):
    """Compute a SHA-256 fingerprint of docs plus chunk/embedding config."""
    digest=hashlib.sha256()
    config={
        "embeddingModel":settings.embeddingModel,
        "collection":settings.qdrantCollection,
        "chunkSize":settings.ragChunkSize,
        "chunkOverlap":settings.ragChunkOverlap
    }

    digest.update(json.dumps(config,sort_keys=True).encode("utf-8"))
    docsRoot=Path(settings.ragDocsDir).resolve()
    for path in markdownFiles:
        resolved=path.resolve()
        try:
            relative=str(resolved.relative_to(docsRoot))
        except ValueError:
            relative=str(resolved)
        digest.update(relative.encode("utf-8"))
        digest.update(path.read_bytes())
    
    return digest.hexdigest()


def loadIndexState():
    """Load persisted index metadata from ``ragIndexStatePath``."""
    path=Path(settings.ragIndexStatePath)
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return  {}

def saveIndexState(state):
    """Persist index metadata after a successful rebuild."""
    path=Path(settings.ragIndexStatePath)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(state,indent=2,sort_keys=True),encoding="utf-8")


def qdrantCollectionExists():
    """Return whether the configured Qdrant collection exists."""
    from qdrant_client import QdrantClient
    import time
    
    # Retry up to 60 seconds to connect to Qdrant (handles startup race condition)
    for attempt in range(30):
        try:
            client = QdrantClient(url=settings.qdrantUrl, timeout=5.0)
            return client.collection_exists(settings.qdrantCollection)
        except Exception:
            if attempt < 29:
                time.sleep(2)
            else:
                raise

def getCollectionPointCount():
    """Get the number of vectors in the Qdrant collection."""
    from qdrant_client import QdrantClient
    
    try:
        client = QdrantClient(url=settings.qdrantUrl, timeout=5.0)
        collection_info = client.get_collection(settings.qdrantCollection)
        return collection_info.points_count
    except Exception:
        return 0

def rebuildRagIndex(markdownFiles,indexVersion):
    """Chunk markdown docs, embed with Google Generative AI, and recreate the Qdrant collection."""
    from langchain_core.documents import Document
    from langchain_qdrant import QdrantVectorStore
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from app.llm_factory import buildEmbeddings

    documents=[
        Document(
            page_content=path.read_text(encoding="utf-8"),
            metadata={
                "source":str(path),
                "fileName":path.name,
                "indexVersion":indexVersion
            },
        )
        for path in markdownFiles
    ]

    splitter=RecursiveCharacterTextSplitter(
        chunk_size=settings.ragChunkSize,
        chunk_overlap=settings.ragChunkSize
    )

    chunks=splitter.split_documents(documents)
    embeddings=buildEmbeddings()
    QdrantVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        url=settings.qdrantUrl,
        collection_name=settings.qdrantCollection,
        force_recreate=True
        )
    
    return {
        "indexVersion":indexVersion,
        "collection":settings.qdrantCollection,
        "embeddingModel":settings.embeddingModel,
        "chunkSize":settings.ragChunkSize,
        "chunkOverlap":settings.ragChunkOverlap,
        "documentCount":len(documents),
        "chunkCount":len(chunks),
        "indexedAt":datetime.now(timezone.utc).isoformat(),
        "docsDir":str(settings.ragDocsDir),
        "sources":[str(path) for path in markdownFiles]
    }


    

    
    