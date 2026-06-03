import os
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import LanguageParser
from langchain.text_splitter import Language, RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

class CodeKnowledgeBase:
    def __init__(self, persist_dir="/app/data/chroma_db"):
        self.persist_dir = persist_dir
        print("Chargement du modèle d'embedding (ça peut prendre 1 min la 1ère fois)...")
        # all-MiniLM-L6-v2 est petit, rapide, et parfait pour tourner sur CPU
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.db = Chroma(persist_directory=self.persist_dir, embedding_function=self.embeddings)

    def index_codebase(self, source_folder="/app"):
        """Lit et indexe tout le code Python du dossier cible."""
        print(f"Analyse du dossier : {source_folder}")
        
        # 1. Charger les fichiers Python (en ignorant les environnements virtuels)
        loader = GenericLoader.from_filesystem(
            source_folder,
            glob="**/*.py",
            exclude=["venv", "env", "__pycache__"],
            parser=LanguageParser(language=Language.PYTHON, parser_threshold=500)
        )
        documents = loader.load()
        print(f"{len(documents)} blocs de code trouvés. Découpage en cours...")

        # 2. Découper intelligemment pour ne pas casser les fonctions/classes
        python_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.PYTHON, chunk_size=1000, chunk_overlap=200
        )
        texts = python_splitter.split_documents(documents)
        print(f"{len(texts)} chunks générés. Insertion dans ChromaDB...")

        # 3. Sauvegarder dans la base vectorielle locale
        self.db.add_documents(texts)
        print("Indexation terminée avec succès ! La base de données est à jour.")

    def search(self, query, top_k=3):
        """Cherche les morceaux de code les plus pertinents par rapport à la question."""
        results = self.db.similarity_search(query, k=top_k)
        
        # Formater les résultats pour les injecter dans le prompt de MIA
        context = ""
        for i, doc in enumerate(results):
            source = doc.metadata.get('source', 'Fichier inconnu')
            context += f"\n--- Extrait {i+1} (Fichier: {source}) ---\n"
            context += doc.page_content + "\n"
        
        return context