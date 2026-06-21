"""Application configuration loaded from environment variables and .env."""

from pathlib import Path
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Environment-backed settings for paths, limits, LLM, RAG, and Qdrant."""

    worker_host:str ="0.0.0.0"
    worker_port: int= 8123
    data_dir:Path=Path("./data")
    commandTimeoutSeconds:int = Field(default=600, validation_alias="COMMAND_TIMEOUT_SECONDS")
    maxZipBytes:int=Field(default=200*1024*1024, validation_alias="MAX_ZIP_BYTES")
    maxUnzippedBytes:int=Field(default=700*1024*1024, validation_alias="MAX_UNZIPPED_BYTES")
    maxZipEntries:int=Field(default=20_000, validation_alias="MAX_ZIP_ENTRIES")
    enableAiEnrichment:bool =Field(default=True, validation_alias="ENABLE_AI_ENRICHMENT")
    aiProvider:str=Field(default="gemini", validation_alias="AI_PROVIDER")
    llmModel:str=Field(default="gemini-2.0-flash", validation_alias="LLM_MODEL")
    ollamaBaseUrl:str=Field(default="http://host.docker.internal:11434", validation_alias="OLLAMA_BASE_URL")
    ollamaModel:str=Field(default="llama3.1:8b", validation_alias="OLLAMA_MODEL")
    ollamaTimeoutSeconds:int=Field(default=90, validation_alias="OLLAMA_TIMEOUT_SECONDS")
    googleApiKey: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    )
    embeddingModel:str =Field(default="models/gemini-embedding-001", validation_alias="EMBEDDING_MODEL")
    qdrantUrl: str = Field(default="http://qdrant:6333", validation_alias="QDRANT_URL")
    qdrantCollection: str = Field(default="dependency_upgrade_docs", validation_alias="QDRANT_COLLECTION")
    ragDocsDir:Path = Field(default=Path("./rag-docs"), validation_alias="RAG_DOCS_DIR")
    ragTopK:int=Field(default=4, validation_alias="RAG_TOP_K")
    ragChunkSize:int=Field(default=1000, validation_alias="RAG_CHUNK_SIZE")
    ragChunkOverlap:int =Field(default=150, validation_alias="RAG_CHUNK_OVERLAP")
    aiMaxDependencies:int=Field(default=12, validation_alias="AI_MAX_DEPENDENCIES")
    aiMaxContextChars:int=Field(default=1200, validation_alias="AI_MAX_CONTEXT_CHARS")
    aiMaxLogChars:int=Field(default=3000, validation_alias="AI_MAX_LOG_CHARS")
    aiMaxOutputTokens:int=Field(default=768, validation_alias="AI_MAX_OUTPUT_TOKENS")
    aiCompactReport:bool=Field(default=True, validation_alias="AI_COMPACT_REPORT")
    maxFixIterations:int =Field(default=3, validation_alias="MAX_FIX_ITERATIONS")
    ragIndexStatePath:Path =Field(default=Path("./data/rag-index-state.json"), validation_alias="RAG_INDEX_STATE_PATH")
    model_config=SettingsConfigDict(env_ignore_empty=False,case_sensitive=False,populate_by_name=True,extra="ignore")

    @property
    def uploads_dir(self):
        """Directory for uploaded ZIP files: ``data_dir/uploads``."""
        return self.data_dir/"uploads"

    @property
    def workspaces_dir(self):
        """Directory for extracted project workspaces: ``data_dir/workspaces``."""
        return self.data_dir/"workspaces"

    @property
    def artifacts_dir(self):
        """Directory for patches, logs, and snapshots: ``data_dir/artifacts``."""
        return self.data_dir/"artifacts"


settings=Settings()
