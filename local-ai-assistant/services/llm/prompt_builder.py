"""
Construit le prompt système et assemble les messages.
"""
from typing import List, Dict, Any, Optional

def build_messages(
    prompt: str,
    history: List[Dict[str, Any]] = None,
    context: str = "",
    system_prompt: Optional[str] = None
) -> List[Dict[str, str]]:
    messages = []
    
    # Prompt système optimisé pour ne pas fuiter les balises
    base_system = (
        "Tu es MIA (ou Gaston), un assistant IA exécuté localement. Réponds en français de manière naturelle et experte.\n"
        "RÈGLES STRICTES :\n"
        "1. DOCUMENTS : Si un [CONTEXTE SUPP] t'est fourni, base ta réponse dessus. Ne cherche pas sur le web.\n"
        "2. DISCUSSION : Pour les salutations, blagues ou questions générales, réponds normalement sans balise.\n"
        "3. RECHERCHE WEB : Si tu as besoin d'informations externes (actualité, météo, cours de la bourse), génère UNIQUEMENT la balise exacte : <SEARCH>ta requête</SEARCH>. Ne dis rien d'autre. Si on te redonne des résultats de recherche, réponds naturellement en te basant dessus et N'UTILISE PLUS JAMAIS LA BALISE <SEARCH>."
    )
    
    if system_prompt:
        messages.append({"role": "system", "content": f"{base_system}\n{system_prompt}"})
    else:
        messages.append({"role": "system", "content": base_system})
    
    if history:
        # history est déjà trié chronologiquement par MemoryManager.get_conversation_history
        for msg in history:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    
    final_prompt = prompt
    if context and context.strip():
        final_prompt = f"[CONTEXTE SUPP]\n{context}\n\nQuestion actuelle :\n{prompt}"
        
    messages.append({"role": "user", "content": final_prompt})
    return messages