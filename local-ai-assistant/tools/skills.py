import logging
import requests
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

class SkillManager:
    TOOLS_SCHEMA = [
        {
            "type": "function",
            "function": {
                "name": "recherche_web",
                "description": "Recherche sur Internet pour trouver des informations récentes, des actualités ou des faits en temps réel.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Les mots-clés exacts de la recherche à envoyer au moteur de recherche."
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]

    @staticmethod
    def recherche_web(query: str) -> str:
        logger.info(f"🌐 [SKILL] Recherche web déclenchée pour : {query}")
        
        # ---------------------------------------------------------
        # NIVEAU 1 : Le hack spécial Crypto (CoinGecko)
        # ---------------------------------------------------------
        if "bitcoin" in query.lower() or "btc" in query.lower() or "crypto" in query.lower():
            try:
                logger.info("💰 [SKILL] Détection Crypto -> Bascule sur l'API CoinGecko")
                url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd,eur"
                resp = requests.get(url, timeout=3)
                resp.raise_for_status()
                data = resp.json()
                btc_usd = data.get('bitcoin', {}).get('usd', 'Inconnu')
                btc_eur = data.get('bitcoin', {}).get('eur', 'Inconnu')
                return f"Données financières directes (CoinGecko) : Le cours actuel du Bitcoin est de {btc_usd} $ (USD) ou {btc_eur} € (EUR)."
            except requests.exceptions.Timeout:
                 logger.warning("Timeout sur l'API CoinGecko.")
            except Exception as e:
                logger.warning(f"Échec API Crypto : {e}")

        # ---------------------------------------------------------
        # NIVEAU 2 : Recherche Web (DuckDuckGo - si implémenté)
        # ---------------------------------------------------------
        try:
            logger.info("🦆 [SKILL] Tentative DuckDuckGo...")
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
                if results:
                    formatted = "Voici les résultats de la recherche DuckDuckGo :\n\n"
                    for r in results:
                         formatted += f"- {r.get('title')}: {r.get('body')}\n"
                    return formatted
        except Exception as e:
             logger.warning(f"Échec DuckDuckGo : {e}")


        # ---------------------------------------------------------
        # NIVEAU 3 : Wikipedia (L'increvable)
        # ---------------------------------------------------------
        try:
            logger.info("📚 [SKILL] Bascule sur l'API Wikipedia...")
            url = f"https://fr.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&utf8=&format=json"
            response = requests.get(url, timeout=3)
            response.raise_for_status()
            search_results = response.json().get('query', {}).get('search', [])
            
            if search_results:
                formatted_results = "Voici les résultats de l'encyclopédie Wikipedia :\n\n"
                for r in search_results[:3]:
                    # Nettoyage des balises HTML bizarres que Wikipedia renvoie
                    snippet = r.get('snippet', '').replace('<span class="searchmatch">', '').replace('</span>', '').replace('&quot;', '"')
                    formatted_results += f"- {r.get('title')}: {snippet}...\n"
                return formatted_results
        except requests.exceptions.Timeout:
            logger.warning("Timeout sur l'API Wikipedia.")
        except Exception as e:
            logger.error(f"❌ Erreur Wikipedia : {e}")

        return "Je suis désolé, tous mes moteurs de recherche sont actuellement bloqués ou injoignables (Timeout ou erreur réseau). Je n'ai rien trouvé."