"""
==============================================================================
MAIN.PY - Application FastAPI Unifiée (Core + RAG Historique)
==============================================================================
"""

import logging
import sys
import threading
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Imports Clean Architecture
from core.config import settings, setup_logging, ensure_directories
from services.memory.manager import init_memory, MemoryManager
from services.llm.engine import init_inference_engine, InferenceEngine, VRAMMonitor
from services.rag.indexer import CodeKnowledgeBase

# Configuration globale des logs
setup_logging()
logger = logging.getLogger(__name__)

# Singletons partagés par l'application
memory_manager: Optional[MemoryManager] = None
inference_engine: Optional[InferenceEngine] = None
code_kb: Optional[CodeKnowledgeBase] = None
rag_indexing_lock = threading.Lock()

# ==============================================================================
# SCHÉMAS DE DONNÉES (Pydantic V2)
# ==============================================================================
class InferenceRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=5000, description="User prompt")
    max_tokens: int = Field(default=2048, ge=10, le=4096, description="Max output tokens")
    include_context: bool = Field(default=True, description="Include conversation context")
    system_prompt: Optional[str] = Field(default=None, description="Custom system prompt")
    user_id: str = Field(default="default", description="User identifier")
    stream: bool = Field(default=False, description="Stream response")

class InferenceResponse(BaseModel):
    text: str
    tokens_used: int
    model: str
    latency_ms: int
    timestamp: datetime
    user_id: str

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    services: Dict[str, bool]
    resources: Dict[str, Any]

# ==============================================================================
# GESTION DU LIFECYCLE (Startup / Shutdown)
# ==============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialisation sécurisée des services au démarrage"""
    logger.info("=" * 80)
    logger.info("STARTING LOCAL AI ASSISTANT (CLEAN ARCHITECTURE)")
    logger.info("=" * 80)
    
    global memory_manager, inference_engine, code_kb
    
    try:
        ensure_directories()
        
        # Initialisation de la persistance SQLite
        memory_manager = init_memory(settings.db_path)
        logger.info("✓ Memory manager initialized")
        
        # Initialisation résiliente du RAG
        try:
            code_kb = CodeKnowledgeBase()
            logger.info("✓ Code Knowledge Base (RAG) initialized")
        except Exception as e:
            logger.error(f"⚠️ Erreur de chargement du RAG (sentence-transformers manquant) : {e}")
            
        # Initialisation du moteur llama.cpp
        model_path = settings.models_path / settings.model_file
        if not model_path.exists():
            logger.warning(f"⚠️ Modèle introuvable à l'emplacement : {model_path}")
            
        inference_engine = init_inference_engine(
            model_path=model_path,
            n_gpu_layers=settings.n_gpu_layers,
            n_threads=settings.n_threads,
            n_batch=settings.n_batch,
            n_ctx=settings.n_ctx,
            temperature=settings.temperature,
            top_p=settings.top_p
        )
        logger.info("✓ Inference engine initialized (lazy load)")
        logger.info("=" * 80)
        logger.info("✓ APPLICATION READY")
        logger.info("=" * 80)
    except Exception as e:
        logger.error(f"Critical Startup Error: {e}", exc_info=True)
        raise
        
    yield
    logger.info("Shutting down core API... Cleanup complete.")

# Instance de l'application
app = FastAPI(
    title=settings.app_name,
    description="Local AI Assistant - Clean Architecture",
    version=settings.app_version,
    lifespan=lifespan
)

# ==============================================================================
# ENDPOINTS CENTRALISÉS
# ==============================================================================
@app.get("/api/health", response_model=HealthResponse, summary="Health check", tags=["System"])
async def health_check() -> HealthResponse:
    vram = {'used_mb': 0, 'total_mb': 0, 'percent': 0}
    try:
        vram = VRAMMonitor.get_vram_usage()
    except Exception:
        pass
        
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        services={
            "memory": memory_manager is not None,
            "inference": inference_engine is not None,
            "gpu": vram.get('total_mb', 0) > 0,
            "rag": code_kb is not None
        },
        resources={
            "vram_used_mb": vram.get('used_mb', 0),
            "vram_total_mb": vram.get('total_mb', 0),
            "vram_percent": vram.get('percent', 0)
        }
    )

@app.get("/api/info", summary="Application info", tags=["System"])
async def app_info() -> Dict[str, Any]:
    if not memory_manager or not inference_engine:
        raise HTTPException(status_code=503, detail="Services not ready")
    return {
        "app": {"name": settings.app_name, "version": settings.app_version, "debug": settings.debug},
        "config": {"model": settings.model_name, "context_size": settings.n_ctx, "max_tokens": settings.max_tokens},
        "memory": memory_manager.get_stats(),
        "inference": inference_engine.get_info(),
        "gpu": VRAMMonitor.get_vram_usage()
    }

@app.post("/api/infer", response_model=InferenceResponse, tags=["Inference"])
async def infer(request: InferenceRequest) -> InferenceResponse:
    if not memory_manager or not inference_engine:
        raise HTTPException(status_code=503, detail="Services not initialized")
        
    try:
        logger.info(f"Infer request - prompt_len={len(request.prompt)}, user={request.user_id}")
        
        # 1. Historique via Sliding Window par Tokens
        history = []
        if request.include_context:
            history = memory_manager.get_conversation_history(user_id=request.user_id, max_tokens=2048)
            
        # 2. Extraction du contexte RAG
        rag_context = ""
        if code_kb:
            snippets = code_kb.search(request.prompt, top_k=3)
            if snippets and snippets.strip():
                rag_context = snippets
                
        # 3. Persistance immédiate du message utilisateur
        memory_manager.add_message(role="user", content=request.prompt, user_id=request.user_id)
        
        # 4. Inférence (L'engine gère la recherche web en interne)
        result = inference_engine.infer(
            prompt=request.prompt,
            history=history,
            context=rag_context,
            max_tokens=request.max_tokens,
            system_prompt=request.system_prompt,
            stream=False
        )
        
        # 5. Persistance de la réponse finale
        if "text" in result:
            memory_manager.add_message(
                role="assistant",
                content=result["text"],
                user_id=request.user_id,
                tokens_used=result.get('tokens_used', 0)
            )
            
        memory_manager.update_user_stats(user_id=request.user_id, tokens_used=result.get('tokens_used', 0))
        
        return InferenceResponse(
            text=result['text'],
            tokens_used=result.get('tokens_used', 0),
            model=result.get('model', settings.model_name),
            latency_ms=result.get('latency_ms', 0),
            timestamp=datetime.utcnow(),
            user_id=request.user_id
        )
    except Exception as e:
        logger.error(f"Inference error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history", tags=["Memory"])
async def get_history(user_id: str = "default", max_tokens: int = 2048) -> List[Dict[str, Any]]:
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory service unavailable")
    return memory_manager.get_conversation_history(user_id=user_id, max_tokens=max_tokens)

@app.delete("/api/history", tags=["Memory"])
async def clear_history(user_id: str = "default") -> Dict[str, str]:
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory service unavailable")
    memory_manager.clear_conversation(user_id=user_id)
    return {"message": f"History cleared for user {user_id}"}

def _reload_rag_task():
    global code_kb
    if not code_kb:
         logger.error("RAG is not initialized.")
         return
    
    if not rag_indexing_lock.acquire(blocking=False):
        logger.warning("RAG reload is already in progress.")
        return
        
    try:
        logger.info("Starting background RAG reload...")
        code_kb.index_documents("/app/documents")
        logger.info("Background RAG reload completed successfully.")
    except Exception as e:
        logger.error(f"Error during RAG reload: {e}", exc_info=True)
    finally:
        rag_indexing_lock.release()

@app.post("/api/rag/reload", tags=["RAG"])
async def reload_rag(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Déclenche la ré-indexation ChromaDB en tâche de fond (Hot-Reload)."""
    if not code_kb:
        raise HTTPException(status_code=503, detail="RAG service is disabled or unavailable")
        
    if rag_indexing_lock.locked():
         return {"message": "Indexation déjà en cours. Veuillez patienter."}
         
    background_tasks.add_task(_reload_rag_task)
    return {"message": "Re-indexation RAG lancée en arrière-plan. Cela peut prendre quelques minutes."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app=app, host=settings.api_host, port=settings.api_port)