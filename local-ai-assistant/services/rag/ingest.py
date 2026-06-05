from services.rag.indexer import CodeKnowledgeBase

if __name__ == "__main__":
    print("=== Démarrage de l'indexation de tes documents personnels ===")
    kb = CodeKnowledgeBase()
    # On lui demande de scanner uniquement le dossier prévu pour ça
    kb.index_documents("/app/documents")
    print("=== Opération terminée ! Gaston a mémorisé tes fichiers. ===")