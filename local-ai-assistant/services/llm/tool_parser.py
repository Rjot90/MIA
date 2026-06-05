"""
Parse and handle special tags in LLM output.
"""
import re
import logging
from typing import Tuple, Optional
from tools.skills import SkillManager

logger = logging.getLogger(__name__)

def intercept_search_tag(text: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Check if the text contains a <SEARCH> tag.
    Returns (has_search, query, stripped_text).
    """
    if "<SEARCH>" in text and "</SEARCH>" in text:
        try:
            query = text.split("<SEARCH>")[1].split("</SEARCH>")[0].strip()
            return True, query, None
        except Exception as e:
            logger.error(f"Error parsing SEARCH tag: {e}")
            
    return False, None, text

def execute_search_tool(query: str) -> str:
    """Execute the search tool."""
    logger.info(f"🛠️ GASTON VEUT CHERCHER SUR LE WEB : {query}")
    try:
        return SkillManager.recherche_web(query)
    except Exception as e:
         logger.error(f"Tool execution failed: {e}")
         return "Erreur lors de l'exécution de la recherche."

def clean_output(text: str) -> str:
    """Remove any remaining search tags for safety."""
    cleaned = re.sub(r'<SEARCH>.*?</SEARCH>', '', text, flags=re.DOTALL).strip()
    if not cleaned:
        return "*(Je suis en pleine réflexion, peux-tu reformuler ta question ?)*"
    return cleaned