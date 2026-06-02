"""
==============================================================================
MAIN.PY - Application FastAPI (Phase 1 Core)
==============================================================================

Responsabilités:
1. Serveur FastAPI
2. Endpoints REST API
3. Orchestration mémoire + inférence
4. Gestion lifecycle (startup/shutdown)
5. Logging/monitoring

Endpoints Phase 1:
- GET  /health           - Health check
- GET  /info             - Infos application
- POST /infer            - Inférence texte
- GET  /history          - Historique conversations
- DELETE /history        - Clear conversations

Dépendances: FastAPI, Uvicorn
==============================================================================
"""

import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from datetime import datetime

# Imports locaux
from config import settings, setup_logging, ensure_directories
from memory import init_memory, MemoryManager
from inference import init_inference_engine, InferenceEngine, VRAMMonitor

# ==============================================================================
# LOGGING SETUP
# ==============================================================================

setup_logging()
logger = logging.getLogger(__name__)

# ==============================================================================
# GLOBAL STATE (Singletons)
# ==============================================================================

# Ces objets sont créés au startup et partagés par tous les endpoints
memory_manager: Optional[MemoryManager] = None
inference_engine: Optional[InferenceEngine] = None


# ==============================================================================
# PYDANTIC MODELS (Request/Response schemas)
# ==============================================================================

class InferenceRequest(BaseModel):
    """
    Requête inférence.
    
    Exemple:
    {
        "prompt": "Explique la programmation en Rust",
        "max_tokens": 512,
        "include_context": true
    }
    """
    prompt: str = Field(..., min_length=1, max_length=5000, description="User prompt")
    max_tokens: int = Field(default=1024, ge=10, le=2048, description="Max output tokens")
    include_context: bool = Field(default=True, description="Include conversation context")
    system_prompt: Optional[str] = Field(default=None, description="Custom system prompt")
    user_id: str = Field(default="default", description="User identifier")
    stream: bool = Field(default=False, description="Stream response")


class InferenceResponse(BaseModel):
    """
    Réponse inférence.
    """
    text: str
    tokens_used: int
    model: str
    latency_ms: int
    timestamp: datetime
    user_id: str


class HistoryMessage(BaseModel):
    """Message dans historique."""
    role: str
    content: str
    timestamp: datetime
    tokens: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    services: Dict[str, bool]
    resources: Dict[str, Any]


# ==============================================================================
# LIFECYCLE EVENTS
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gère lifecycle de l'application.
    
    on_startup: Initialise mémoire + inférence
    on_shutdown: Cleanup ressources
    """
    
    # ========================================================================
    # STARTUP
    # ========================================================================
    logger.info("=" * 80)
    logger.info("STARTING LOCAL AI ASSISTANT")
    logger.info("=" * 80)
    
    try:
        # Créer répertoires
        ensure_directories()
        
        # Initialiser mémoire
        global memory_manager
        memory_manager = init_memory(settings.db_path)
        logger.info("✓ Memory manager initialized")
        
        # Initialiser inférence (lazy load modèle)
        global inference_engine
        
        # Vérifier modèle existe, sinon télécharger
        model_path = settings.models_path / settings.model_file
        
        if not model_path.exists():
            logger.warning(
                f"Model not found: {model_path}\n"
                f"Téléchargement requis pour première utilisation."
            )
        
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
        logger.info(f"✓ API listening on {settings.api_host}:{settings.api_port}")
        logger.info(f"✓ Docs: http://localhost:{settings.api_port}/docs")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Startup error: {e}", exc_info=True)
        raise
    
    yield
    
    # ========================================================================
    # SHUTDOWN
    # ========================================================================
    logger.info("Shutting down...")
    logger.info("✓ Cleanup complete")


# ==============================================================================
# FASTAPI APP INSTANCE
# ==============================================================================

app = FastAPI(
    title=settings.app_name,
    description="Local AI Assistant - Phase 1",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# ==============================================================================
# HEALTH & INFO ENDPOINTS
# ==============================================================================

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["System"]
)
async def health_check() -> HealthResponse:
    """
    Vérifie l'état de l'application.
    
    Retourne:
    - Status global (healthy/degraded/unhealthy)
    - État chaque service (memory, inference, gpu)
    - Ressources utilisées (RAM, VRAM)
    """
    try:
        vram = VRAMMonitor.get_vram_usage()
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            services={
                "memory": memory_manager is not None,
                "inference": inference_engine is not None,
                "gpu": vram['total_mb'] > 0
            },
            resources={
                "vram_used_mb": vram['used_mb'],
                "vram_total_mb": vram['total_mb'],
                "vram_percent": vram['percent']
            }
        )
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@app.get("/info", summary="Application info", tags=["System"])
async def app_info() -> Dict[str, Any]:
    """
    Retourne infos application.
    
    - Version
    - Config
    - État services
    - Stats mémoire
    """
    if not memory_manager or not inference_engine:
        raise HTTPException(status_code=503, detail="Services not ready")
    
    return {
        "app": {
            "name": settings.app_name,
            "version": settings.app_version,
            "debug": settings.debug
        },
        "config": {
            "model": settings.model_name,
            "context_size": settings.n_ctx,
            "max_tokens": settings.max_tokens
        },
        "memory": memory_manager.get_stats(),
        "inference": inference_engine.get_info(),
        "gpu": VRAMMonitor.get_vram_usage()
    }


# ==============================================================================
# INFERENCE ENDPOINT (Core)
# ==============================================================================

@app.post(
    "/infer",
    response_model=InferenceResponse,
    summary="Run inference",
    tags=["Inference"],
    responses={
        200: {"description": "Inference successful"},
        400: {"description": "Invalid request"},
        503: {"description": "Service unavailable"}
    }
)
async def infer(request: InferenceRequest) -> InferenceResponse:
    """
    Lance inférence IA.
    
    Flux:
    1. Récupère contexte conversation (si enabled)
    2. Lance inférence
    3. Stocke question + réponse en mémoire
    4. Retourne réponse
    
    Temps réponse: ~20-30s (latence llama.cpp)
    
    Exemple:
    ```
    POST /infer
    {
        "prompt": "Explique la programmation fonctionnelle",
        "max_tokens": 512
    }
    ```
    """
    
    if not memory_manager or not inference_engine:
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    try:
        logger.info(f"Infer request - prompt_len={len(request.prompt)}, user={request.user_id}")
        
        # Récupère contexte conversation si demandé
        context = ""
        if request.include_context:
            context = memory_manager.get_conversation_context(
                user_id=request.user_id,
                window_messages=5
            )
        
        # Stocke la question en mémoire
        memory_manager.add_message(
            role="user",
            content=request.prompt,
            user_id=request.user_id
        )
        
        # Inférence
        result = inference_engine.infer(
            prompt=request.prompt,
            context=context,
            max_tokens=request.max_tokens,
            system_prompt=request.system_prompt,
            stream=False
        )
        
        # Stocke la réponse
        memory_manager.add_message(
            role="assistant",
            content=result['text'],
            user_id=request.user_id,
            tokens_used=result['tokens_used']
        )
        
        # Met à jour stats utilisateur
        memory_manager.update_user_stats(
            user_id=request.user_id,
            tokens_used=result['tokens_used']
        )
        
        logger.info(
            f"✓ Inference complete - "
            f"tokens={result['tokens_used']}, "
            f"latency={result['latency_ms']}ms"
        )
        
        return InferenceResponse(
            text=result['text'],
            tokens_used=result['tokens_used'],
            model=result['model'],
            latency_ms=result['latency_ms'],
            timestamp=datetime.utcnow(),
            user_id=request.user_id
        )
    
    except Exception as e:
        logger.error(f"Inference error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")


# ==============================================================================
# HISTORY ENDPOINTS
# ==============================================================================

@app.get(
    "/history",
    summary="Get conversation history",
    tags=["Memory"]
)
async def get_history(user_id: str = "default", limit: int = 50) -> List[Dict[str, Any]]:
    """
    Récupère l'historique conversations.
    
    Query params:
    - user_id: Utilisateur (default: "default")
    - limit: Nombre dernier messages (default: 50)
    
    Returns:
    Liste des messages {role, content, timestamp, tokens}
    """
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory service unavailable")
    
    try:
        history = memory_manager.get_conversation_history(
            user_id=user_id,
            limit=limit
        )
        logger.info(f"History retrieved - user={user_id}, count={len(history)}")
        return history
    
    except Exception as e:
        logger.error(f"History retrieval error: {e}")
        raise HTTPException(status_code=500, detail="History retrieval failed")


@app.delete(
    "/history",
    summary="Clear conversation history",
    tags=["Memory"]
)
async def clear_history(user_id: str = "default") -> Dict[str, str]:
    """
    Efface l'historique utilisateur.
    
    ⚠️ IRRÉVERSIBLE
    """
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory service unavailable")
    
    try:
        memory_manager.clear_conversation(user_id=user_id)
        logger.info(f"✓ History cleared - user={user_id}")
        return {"message": f"History cleared for user {user_id}"}
    
    except Exception as e:
        logger.error(f"History clear error: {e}")
        raise HTTPException(status_code=500, detail="Clear failed")


# ==============================================================================
# ERROR HANDLERS
# ==============================================================================

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Gère exceptions non-traitées."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting Uvicorn on {settings.api_host}:{settings.api_port}")
    
    uvicorn.run(
        app=app,
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,  # 1 = pas de multiprocessing
        log_level=settings.log_level.lower(),
        access_log=True
    )
