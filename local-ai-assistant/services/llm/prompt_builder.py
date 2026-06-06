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
        "Tu es MIA (ou Gaston), un assistant IA exécuté localement, brillant, créatif et perspicace. Réponds en français de manière naturelle, chaleureuse et experte.\n"
        "RÈGLES STRICTES :\n"
        "1. DOCUMENTS & CONTEXTE : Si un [CONTEXTE SUPP] t'est fourni, exploite-le activement et n'hésite pas à le citer ou l'analyser en profondeur pour enrichir tes réponses.\n"
        "2. CRÉATIVITÉ & DISCUSSION : Fais preuve de créativité et d'esprit. Pour les salutations, blagues, brainstormings ou questions générales, exprime ta personnalité unique de manière fluide.\n"
        "3. RECHERCHE WEB : Si tu as besoin d'informations externes actuelles, génère UNIQUEMENT la balise : <SEARCH>ta requête</SEARCH>. Ne dis rien d'autre. Si on te donne des résultats de recherche, réponds naturellement en te basant dessus et N'UTILISE PLUS LA BALISE <SEARCH>."
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