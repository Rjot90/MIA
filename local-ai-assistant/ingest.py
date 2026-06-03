from rag_manager import CodeKnowledgeBase

if __name__ == "__main__":
    print("=== Démarrage de l'indexation du projet ===")
    kb = CodeKnowledgeBase()
    # On lui demande de scanner tout le code présent dans le conteneur (/app)
    kb.index_codebase("/app")
    print("=== Opération terminée ! MIA connait ton code. ===")