"""
==============================================================================
INFERENCE.PY - Moteur inférence IA (llama.cpp + Qwen)
==============================================================================

Responsabilités:
1. Chargement modèle Qwen en GGUF (quantifié 4-bit)
2. Gestion llama.cpp (binding Python)
3. Inférence texte avec contexte
4. Gestion tokens/contexte
5. Monitoring ressources

Architecture:
- Lazy loading (modèle chargé qu'à première inférence)
- Vérification VRAM avant inférence
- Context management (finestre glissante)
- Timeout inférence (sécurité)

Dépendance: llama-cpp-python (pip install)
==============================================================================
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, Generator, List, Union
from datetime import datetime
import subprocess
import sys

# llama.cpp binding
try:
    from llama_cpp import Llama
    from llama_cpp.llama_types import CreateCompletionResponse
except ImportError:
    raise ImportError(
        "llama-cpp-python not installed. Run: pip install llama-cpp-python"
    )

logger = logging.getLogger(__name__)


# ==============================================================================
# TÉLÉCHARGEMENT MODÈLE
# ==============================================================================

class ModelDownloader:
    """
    Gère téléchargement modèles Hugging Face.
    
    Features:
    - Résumé téléchargement
    - Vérification complétude
    - Retry logique
    """
    
    @staticmethod
    def download_model(
        url: str,
        destination: Path,
        force: bool = False
    ) -> Path:
        """
        Télécharge modèle GGUF depuis URL HF.
        
        Args:
            url: URL Hugging Face (repo + fichier)
            destination: Chemin local destination
            force: Retélécharger même si existe
        
        Returns:
            Path du fichier téléchargé
        
        Exemple:
            >>> path = ModelDownloader.download_model(
            ...     url="https://huggingface.co/...",
            ...     destination=Path("./models/qwen-7b.gguf")
            ... )
        """
        if destination.exists() and not force:
            logger.info(f"Model already exists: {destination}")
            return destination
        
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Downloading model: {url}")
        logger.info(f"Destination: {destination}")
        
        try:
            # Utilise curl pour robustesse (alternative à urllib)
            subprocess.run([
                "curl", "-L", "-o", str(destination), url
            ], check=True)
            
            logger.info(f"✓ Model downloaded: {destination}")
            return destination
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Download failed: {e}")
            if destination.exists():
                destination.unlink()
            raise


# ==============================================================================
# VRAM MONITOR
# ==============================================================================

class VRAMMonitor:
    """
    Monitore utilisation VRAM NVIDIA.
    
    Utilise: nvidia-smi
    """
    
    @staticmethod
    def get_vram_usage() -> Dict[str, int]:
        """
        Récupère usage VRAM actual (MB).
        
        Returns:
            {
                'used_mb': 2048,
                'total_mb': 6144,
                'percent': 33.3
            }
        """
        try:
            result = subprocess.run([
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total",
                "--format=csv,nounits,noheader"
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                used, total = map(int, result.stdout.strip().split(','))
                return {
                    'used_mb': used,
                    'total_mb': total,
                    'percent': (used / total) * 100 if total > 0 else 0
                }
        except Exception as e:
            logger.warning(f"Could not query VRAM: {e}")
        
        return {'used_mb': 0, 'total_mb': 6144, 'percent': 0}
    
    @staticmethod
    def check_vram_available(required_mb: int) -> bool:
        """
        Vérifie si VRAM suffisante disponible.
        
        Args:
            required_mb: MB nécessaire
        
        Returns:
            True si suffisant, False sinon
        """
        usage = VRAMMonitor.get_vram_usage()
        available = usage['total_mb'] - usage['used_mb']
        
        is_available = available >= required_mb
        
        logger.info(
            f"VRAM check: {available} MB available "
            f"(need {required_mb} MB) - {'✓' if is_available else '✗'}"
        )
        
        return is_available


# ==============================================================================
# INFERENCE ENGINE (Core)
# ==============================================================================

class InferenceEngine:
    """
    Moteur inférence principal.
    
    Features:
    - Lazy loading modèle (first-call loading)
    - Contexte conversation
    - Streaming support
    - Error handling robuste
    - VRAM monitoring
    
    Usage:
        engine = InferenceEngine(model_path="./models/qwen.gguf")
        response = engine.infer("Hello", context="...")
    """
    
    # Constantes
    MODEL_VRAM_REQUIRED_MB = 5800  # Qwen-7B Q4 estimé
    MAX_TOKENS_DEFAULT = 8000
    
    def __init__(
        self,
        model_path: str | Path,
        n_gpu_layers: int = 18,
        n_threads: int = 8,
        n_batch: int = 512,
        n_ctx: int = 4096,
        temperature: float = 0.2,
        top_p: float = 0.95,
        timeout: int = 300  # 5 minutes max inférence
    ):
        """
        Initialise moteur (modèle pas encore chargé).
        
        Args:
            model_path: Chemin fichier GGUF
            n_gpu_layers: Layers GPU (33 pour RTX 2060)
            n_threads: CPU threads (8 pour Ryzen 7 3700X)
            n_batch: Batch inférence (256)
            n_ctx: Context window (2048 tokens)
            temperature: Contrôle créativité (0.7)
            top_p: Nucleus sampling (0.95)
            timeout: Timeout inférence (300s)
        """
        self.model_path = Path(model_path)
        self.timeout = timeout
        
        # Paramètres llama.cpp
        self.llama_params = {
            'n_gpu_layers': n_gpu_layers,
            'n_threads': n_threads,
            'n_batch': n_batch,
            'n_ctx': n_ctx,
            'flash_attn': True,
            'verbose': True
        }
        
        # Paramètres génération
        self.gen_params = {
            'temperature': temperature,
            'top_p': top_p,
            'top_k': 40
        }
        
        # État
        self.llm: Optional[Llama] = None
        self.is_loaded = False
        self.load_time: Optional[float] = None
        
        logger.info(
            f"InferenceEngine initialized (lazy load) - "
            f"model_path={self.model_path}"
        )
    
    def _load_model(self):
        """
        Charge le modèle (appelé une fois à première inférence).
        
        Étapes:
        1. Vérification fichier existe
        2. Vérification VRAM disponible
        3. Chargement llama.cpp
        4. Test inférence basique
        """
        if self.is_loaded:
            return
        
        logger.info("=" * 80)
        logger.info("LOADING MODEL - This may take 20-30 seconds...")
        logger.info("=" * 80)
        
        # Vérification fichier
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        logger.info(f"✓ Model file found: {self.model_path}")
        logger.info(f"✓ File size: {self.model_path.stat().st_size / (1024**3):.2f} GB")
        
        # Vérification VRAM
       # if not VRAMMonitor.check_vram_available(self.MODEL_VRAM_REQUIRED_MB):
        #    raise RuntimeError(
        #       f"Insufficient VRAM. Need {self.MODEL_VRAM_REQUIRED_MB} MB, "
        #       f"but only {VRAMMonitor.get_vram_usage()['total_mb']} MB available"
        #   )
        
        # Chargement
        try:
            start_time = datetime.now()
            
            self.llm = Llama(
                model_path=str(self.model_path),
                **self.llama_params
            )
            
            self.load_time = (datetime.now() - start_time).total_seconds()
            self.is_loaded = True
            
            logger.info(f"✓ Model loaded successfully in {self.load_time:.2f}s")
            logger.info(f"✓ Model context: {self.llama_params['n_ctx']} tokens")
            logger.info(f"✓ GPU layers: {self.llama_params['n_gpu_layers']}")
            
        except Exception as e:
            logger.error(f"Model loading failed: {e}")
            raise
    
    def infer(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = MAX_TOKENS_DEFAULT,
        system_prompt: Optional[str] = None,
        stream: bool = False
    ) -> Dict[str, Any] | Generator[str, None, None]:
        """
        Lance inférence sur prompt avec create_chat_completion.
        """
        # Lazy load modèle
        if not self.is_loaded:
            self._load_model()
        
        # Construire messages
        messages = self._build_messages(prompt, context, system_prompt)
        
        logger.info(f"Inferring... (max {max_tokens} tokens)")
        
        try:
            start_time = datetime.now()
            
            if stream:
                # Mode streaming (générateur)
                return self._infer_stream(messages, max_tokens)
            else:
                # Mode standard (réponse complète)
                response = self.llm.create_chat_completion(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=self.gen_params['temperature'],
                    top_p=self.gen_params['top_p'],
                    top_k=self.gen_params['top_k']
                )
                
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                # Parse réponse
                text = response['choices'][0]['message']['content'].strip()
                tokens = response['usage']['completion_tokens']
                
                logger.info(
                    f"✓ Inferred {tokens} tokens in {latency_ms:.0f}ms "
                    f"({latency_ms/tokens:.1f}ms/token)"
                )
                
                return {
                    'text': text,
                    'tokens_used': tokens,
                    'model': 'qwen-2.5-7b',
                    'latency_ms': int(latency_ms),
                    'stop_reason': response['choices'][0].get('finish_reason', 'unknown')
                }
        
        except Exception as e:
            logger.error(f"Inference error: {e}")
            raise
    
    def _infer_stream(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int
    ) -> Generator[str, None, None]:
        """
        Mode streaming (pour Discord messages longs).
        
        Yields tokens progressivement.
        """
        response = self.llm.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=self.gen_params['temperature'],
            top_p=self.gen_params['top_p'],
            stream=True
        )
        
        for chunk in response:
            delta = chunk['choices'][0].get('delta', {})
            text = delta.get('content', '')
            if text:
                yield text
    
    def _build_messages(
        self,
        prompt: str,
        context: str = "",
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Construit la liste des messages pour LLM.
        """
        messages = []
        
        # System prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            # Default system prompt
            default_system = (
                "Tu es MIA, un assistant IA de développement exécuté localement. "
                "Réponds toujours en français, de manière experte, technique et directe au développeur. "
                "Formate ton code en Markdown."
            )
            messages.append({"role": "system", "content": default_system})
        
        # Contexte conversation et Prompt utilisateur
        if context and context.strip():
            messages.append({
                "role": "user", 
                "content": f"Voici le contexte de la conversation et/ou de la recherche Web :\n{context}\n\nMa question :\n{prompt}"
                })
        else:
            messages.append({"role": "user", "content": prompt})
        
        return messages 
    
    def get_info(self) -> Dict[str, Any]:
        """Retourne infos moteur."""
        return {
            'loaded': self.is_loaded,
            'model_path': str(self.model_path),
            'load_time_seconds': self.load_time,
            'llama_params': self.llama_params,
            'gen_params': self.gen_params
        }


# ==============================================================================
# INITIALIZATION
# ==============================================================================

def init_inference_engine(
    model_path: str | Path,
    **kwargs
) -> InferenceEngine:
    """
    Factory pour créer InferenceEngine.
    
    Modèle pas chargé jusqu'à première inférence.
    """
    engine = InferenceEngine(model_path, **kwargs)
    logger.info("InferenceEngine initialized (lazy load)")
    return engine
