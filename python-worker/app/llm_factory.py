"""Factory for Google Gemini chat and embedding clients."""

import json
from urllib import request

from app.config import settings


class OllamaChat:
    """Small LangChain-like wrapper for local Ollama chat generation."""

    def __init__(self, base_url:str, model:str):
        self.base_url=base_url.rstrip("/")
        self.model=model

    def invoke(self, prompt:str):
        payload=json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
                "num_predict": settings.aiMaxOutputTokens,
                "num_ctx": 2048,
                "num_thread": 4,
            },
        }).encode("utf-8")
        req=request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type":"application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=settings.ollamaTimeoutSeconds) as response:
            data=json.loads(response.read().decode("utf-8"))
        return type("OllamaResponse", (), {"content": data.get("response","")})()


def buildLLM():
    """Construct the configured chat client."""
    if settings.aiProvider.lower()=="ollama":
        return OllamaChat(settings.ollamaBaseUrl,settings.ollamaModel)

    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=settings.llmModel,
        temperature=0,
        max_output_tokens=settings.aiMaxOutputTokens,
        google_api_key=settings.googleApiKey or None,
    )


def buildEmbeddings():
    """Construct a GoogleGenerativeAIEmbeddings client for Qdrant RAG."""
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(
        model=settings.embeddingModel,
        google_api_key=settings.googleApiKey or None,
    )
