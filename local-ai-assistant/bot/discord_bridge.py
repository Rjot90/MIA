import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class APIBridge:
    def __init__(self, api_url: str, endpoint: str, timeout: int = 300, max_tokens: int = 4096):
        self.api_url = api_url.rstrip("/")
        self.endpoint = endpoint
        self.timeout = timeout
        self.max_tokens = max_tokens
        
    async def infer(self, prompt: str, user_id: str, include_context: bool = True) -> Optional[Dict[str, Any]]:
        url = f"{self.api_url}{self.endpoint}"
        payload = {
            "prompt": prompt,
            "user_id": str(user_id),
            "include_context": include_context,
            "max_tokens": self.max_tokens
        }
        
        try:
            # We use a large timeout because llama.cpp can take 20-40s
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                logger.info(f"Sending prompt to {url} for user {user_id}")
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        error_text = await response.text()
                        logger.error(f"API Error {response.status}: {error_text}")
                        return None
        except asyncio.TimeoutError:
            logger.error(f"API Timeout after {self.timeout}s for user {user_id}")
            return {"error": "timeout"}
        except Exception as e:
            logger.error(f"API Request failed: {e}")
            return None

    # LA FONCTION EST MAINTENANT BIEN SÉPARÉE À LA FIN DE LA CLASSE
    async def clear_history(self, user_id: str) -> bool:
        url = f"{self.api_url}/api/history"
        try:
            async with aiohttp.ClientSession() as session:
                # On appelle l'endpoint DELETE de ton FastAPI
                async with session.delete(url, params={"user_id": str(user_id)}) as response:
                    if response.status == 200:
                        logger.info(f"Mémoire effacée pour {user_id}")
                        return True
                    return False
        except Exception as e:
            logger.error(f"Erreur lors de l'effacement de la mémoire: {e}")
            return False