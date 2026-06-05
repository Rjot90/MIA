import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import subprocess

try:
    from llama_cpp import Llama
except ImportError:
    raise ImportError("llama-cpp-python not installed. Run: pip install llama-cpp-python")

from services.llm.prompt_builder import build_messages
from services.llm.tool_parser import intercept_search_tag, execute_search_tool, clean_output

logger = logging.getLogger(__name__)

class VRAMMonitor:
    @staticmethod
    def get_vram_usage() -> Dict[str, int]:
        try:
            result = subprocess.run([
                "nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,nounits,noheader"
            ], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                used, total = map(int, result.stdout.strip().split(','))
                return {'used_mb': used, 'total_mb': total, 'percent': (used / total) * 100 if total > 0 else 0}
        except Exception:
            pass
        return {'used_mb': 0, 'total_mb': 6144, 'percent': 0}

class InferenceEngine:
    MAX_TOKENS_DEFAULT = 2048
    
    def __init__(
        self,
        model_path: str | Path,
        n_gpu_layers: int = -1, # Offload tout par defaut
        n_threads: int = 8,
        n_batch: int = 512,
        n_ctx: int = 8192, # Optimisé pour LFM2.5
        temperature: float = 0.2,
        top_p: float = 0.95,
        timeout: int = 300
    ):
        self.model_path = Path(model_path)
        
        self.llama_params = {
            'n_gpu_layers': n_gpu_layers,
            'n_threads': n_threads,
            'n_batch': n_batch,
            'n_ctx': n_ctx,
            'flash_attn': True,
            'verbose': False
        }
        
        # Configuration LFM2.5 (MoE)
        self.gen_params = {
            'temperature': temperature,
            'top_p': top_p,
            'top_k': 80,              
            'repeat_penalty': 1.05     
        }
        
        self.llm: Optional[Llama] = None
        self.is_loaded = False
        self.load_time: Optional[float] = None
    
    def _load_model(self):
        if self.is_loaded: return
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        start_time = datetime.now()
        logger.info(f"Loading model from {self.model_path} with ctx={self.llama_params['n_ctx']}...")
        self.llm = Llama(model_path=str(self.model_path), **self.llama_params)
        self.load_time = (datetime.now() - start_time).total_seconds()
        self.is_loaded = True
        logger.info(f"Model loaded in {self.load_time:.2f}s")
    
    def infer(
        self,
        prompt: str,
        history: List[Dict[str, Any]] = None,
        context: str = "",
        max_tokens: int = MAX_TOKENS_DEFAULT,
        system_prompt: Optional[str] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        
        if not self.is_loaded:
            self._load_model()
        
        messages = build_messages(prompt, history, context, system_prompt)
        start_time = datetime.now()
        
        kwargs = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": self.gen_params['temperature'],
            "top_p": self.gen_params['top_p'],
            "top_k": self.gen_params['top_k'],
            "repeat_penalty": self.gen_params['repeat_penalty']
        }
        
        # 1. Première réflexion
        response = self.llm.create_chat_completion(**kwargs)
        text = response['choices'][0]['message']['content'].strip()
        tokens = response['usage']['completion_tokens']
        stop_reason = response['choices'][0].get('finish_reason', 'unknown')
        
        # 2. Interception Tool (Skill)
        has_search, query, _ = intercept_search_tag(text)
        
        if has_search:
            tool_result = execute_search_tool(query)
            
            messages.append({"role": "assistant", "content": text})
            messages.append({
                "role": "user", 
                "content": f"Voici les résultats d'internet :\n{tool_result}\n\nRédige maintenant ta réponse finale NORMALEMENT sans réutiliser la balise <SEARCH>."
            })
            
            logger.info("🧠 Résultats donnés à Gaston, génération de la réponse finale...")
            kwargs["messages"] = messages
            final_response = self.llm.create_chat_completion(**kwargs)
            
            text = final_response['choices'][0]['message']['content'].strip()
            tokens += final_response['usage']['completion_tokens']
            stop_reason = final_response['choices'][0].get('finish_reason', 'unknown')
        
        # 3. Nettoyage et Retour
        text = clean_output(text)
        
        latency_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return {
            'text': text,
            'tokens_used': tokens,
            'model': 'gaston-lfm2.5',
            'latency_ms': int(latency_ms),
            'stop_reason': stop_reason
        }

    def get_info(self) -> Dict[str, Any]:
        return {'loaded': self.is_loaded, 'model_path': str(self.model_path)}

def init_inference_engine(model_path: str | Path, **kwargs) -> InferenceEngine:
    return InferenceEngine(model_path, **kwargs)