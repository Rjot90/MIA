"""
==============================================================================
CONFIG.PY - Configuration centralisée de l'application
==============================================================================

Ce fichier gère :
- Chemins fichiers/répertoires
- Variables d'environnement
- Paramètres modèle IA
- Limites ressources
- Logging

Toute modification de config passera par ici (single source of truth).
==============================================================================
"""

import os
import logging
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


# ==============================================================================
# PYDANTIC SETTINGS (gestion env + validation)
# ==============================================================================

class AppSettings(BaseSettings):
    """
    Configuration applicative chargée depuis variables d'environnement
    et .env file (via python-dotenv)
    
    Priority :
    1. Variables d'environnement systèmes
    2. Fichier .env local
    3. Valeurs par défaut ci-dessous
    """
    
    # ========================================================================
    # APPLICATION
    # ========================================================================
    app_name: str = "Local AI Assistant"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # ========================================================================
    # API SERVEUR
    # ========================================================================
    api_host: str = "0.0.0.0"  # Écoute tous les interfaces (Docker)
    api_port: int = 8000
    api_workers: int = 1  # Pas de concurrence (inférence sequential)
    
    # ========================================================================
    # CHEMINS RÉPERTOIRES
    # ========================================================================
    # Utilise /app par défaut (Docker), ou cwd localement
    data_path: Path = Field(default_factory=lambda: Path(os.getenv("DATA_PATH", "./data")))
    models_path: Path = Field(default_factory=lambda: Path(os.getenv("MODELS_PATH", "./models")))
    documents_path: Path = Field(default_factory=lambda: Path(os.getenv("DOCUMENTS_PATH", "./documents")))
    logs_path: Path = Field(default_factory=lambda: Path(os.getenv("LOG_PATH", "./logs")))
    
    # ========================================================================
    # BASE DE DONNÉES
    # ========================================================================
    db_path: Path = Field(default_factory=lambda: Path(os.getenv("DATA_PATH", "./data")) / "memory.db")
    db_echo: bool = False  # Logs SQL queries (dev only)
    
    # ========================================================================
    # MODÈLE IA
    # ========================================================================
    model_name: str = "LFM2.5-8B-Uncensored-Gaston"
    model_file: str = "LFM2.5-8B-A1B-Uncensored-Gaston-Q5_K_M.gguf"
    model_url: str = (
        "https://huggingface.co/gaston-parravicini/LFM2.5-8B-A1B-Uncensored-Gaston-GGUF/resolve/main/LFM2.5-8B-A1B-Uncensored-Gaston-Q5_K_M.gguf"
    )
    
    # Paramètres llama.cpp (optimisés RTX 2060 6 Go)
    # ⚠️ GPU/CPU OFFLOADING STRATEGY ⚠️
    n_gpu_layers: int = 18  # Layers GPU (20-25) + CPU (8-13)
                            # Balance: stable (pas de CUDA OOM) vs performance
                            # Ajuster si VRAM issues ou pour plus de perf
    n_threads: int = 10     # CPU threads (AMD Ryzen 7 3700X = 8 cores)
    n_batch: int = 512      # Batch size (256 OK)
    n_ctx: int = 4096       # Context window (1024 = stable, 2048 = risky)
    
    # Paramètres génération
    max_tokens: int = 2048
    temperature: float = 0.2
    top_p: float = 0.95
    top_k: int = 40
    
    # ========================================================================
    # RESSOURCES SYSTÈME
    # ========================================================================
    # Limites mémoire (sécurité)
    max_ram_mb: int = 10000  # 10 Go max
    max_vram_mb: int = 5800  # 5.8 Go (RTX 2060 6 Go limite)
    
    # ========================================================================
    # LOGGING
    # ========================================================================
    log_file: str = "app.log"
    log_format: str = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"  # Permet fields supplémentaires
        protected_namespaces = () # Fix Pydantic V2 warnings for fields starting with model_


# ==============================================================================
# INSTANCE SETTINGS GLOBALE
# ==============================================================================

from pydantic import Field

settings = AppSettings()


# ==============================================================================
# CRÉATION RÉPERTOIRES
# ==============================================================================

def ensure_directories():
    """
    Crée les répertoires nécessaires s'ils n'existent pas.
    Called au startup de l'app.
    """
    dirs = [
        settings.data_path,
        settings.models_path,
        settings.documents_path,
        settings.logs_path,
    ]
    
    for directory in dirs:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✓ Directory ensured: {directory}")


# ==============================================================================
# LOGGING SETUP
# ==============================================================================

def setup_logging():
    """
    Configure le logging avec handlers fichier + console.
    Logging format: INFO - classe - message
    """
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.log_level))
    
    # Format
    formatter = logging.Formatter(settings.log_format)
    
    # Handler Console (stdout)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, settings.log_level))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler Fichier
    log_file = settings.logs_path / settings.log_file
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(getattr(logging, settings.log_level))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    logger.info(f"Logging configured - level: {settings.log_level}")


# ==============================================================================
# VALIDATION AU IMPORT
# ==============================================================================

if __name__ == "__main__":
    # Test config quand run directement
    print("=" * 80)
    print("CONFIGURATION VERIFICATION")
    print("=" * 80)
    print(f"App: {settings.app_name} v{settings.app_version}")
    print(f"Debug: {settings.debug}")
    print(f"API: {settings.api_host}:{settings.api_port}")
    print(f"Model: {settings.model_name}")
    print(f"Data path: {settings.data_path}")
    print(f"Models path: {settings.models_path}")
    print(f"Max VRAM: {settings.max_vram_mb} MB")
    print("=" * 80)
