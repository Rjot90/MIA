import os
import logging
from langchain_community.document_loaders import PyPDFLoader, TextLoader, DirectoryLoader
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import LanguageParser
from langchain.text_splitter import Language, RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

logger = logging.getLogger(__name__)

class CodeKnowledgeBase:
    def __init__(self, persist_dir="/app/data/chroma_db"):
        self.persist_dir = persist_dir
        logger.info("Chargement du modèle d'embedding (ça peut prendre 1 min la 1ère fois)...")
        # all-MiniLM-L6-v2 est petit, rapide, et parfait pour tourner sur CPU
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.db = Chroma(persist_directory=self.persist_dir, embedding_function=self.embeddings)

    def index_documents(self, source_folder="/app/documents"):
        """Lit et indexe les PDF, TXT, MD et PY du dossier cible."""
        logger.info(f"Analyse du dossier : {source_folder}")
        all_documents = []
        
        # 1. Charger les PDFs (Récursif)
        try:
            pdf_loader = DirectoryLoader(source_folder, glob="**/*.pdf", loader_cls=PyPDFLoader, recursive=True)
            all_documents.extend(pdf_loader.load())
        except Exception as e:
            logger.warning(f"Erreur lors du chargement des PDF : {e}")

        # 2. Charger les fichiers Markdown et Textes (Récursif)
        try:
            md_loader = DirectoryLoader(source_folder, glob="**/*.md", loader_cls=TextLoader, recursive=True)
            txt_loader = DirectoryLoader(source_folder, glob="**/*.txt", loader_cls=TextLoader, recursive=True)
            all_documents.extend(md_loader.load())
            all_documents.extend(txt_loader.load())
        except Exception as e:
            logger.warning(f"Erreur lors du chargement des fichiers texte : {e}")

        # 3. Charger le code (Python, C/C++, JS, TS - Récursif)
        common_exclude = ["venv", "env", "__pycache__", ".git", "node_modules", "dist", "build"]
        
        try:
            py_loader = GenericLoader.from_filesystem(
                source_folder, glob="**/*.py",
                suffixes=[".py"],
                exclude=common_exclude,
                parser=LanguageParser(language=Language.PYTHON, parser_threshold=500)
            )
            all_documents.extend(py_loader.load())
        except Exception as e:
            logger.warning(f"Erreur lors du chargement du code Python : {e}")

        # C / C++
        try:
            cpp_loader = GenericLoader.from_filesystem(
                source_folder, glob="**/*",
                suffixes=[".c", ".cpp", ".h", ".hpp"],
                exclude=common_exclude,
                parser=LanguageParser(language=Language.CPP, parser_threshold=500)
            )
            all_documents.extend(cpp_loader.load())
        except Exception as e:
            logger.warning(f"Erreur lors du chargement du code C/C++ : {e}")

        # JavaScript / React
        try:
            js_loader = GenericLoader.from_filesystem(
                source_folder, glob="**/*",
                suffixes=[".js", ".jsx"],
                exclude=common_exclude,
                parser=LanguageParser(language=Language.JS, parser_threshold=500)
            )
            all_documents.extend(js_loader.load())
        except Exception as e:
            logger.warning(f"Erreur lors du chargement du code JS : {e}")

        # TypeScript / React
        try:
            ts_loader = GenericLoader.from_filesystem(
                source_folder, glob="**/*",
                suffixes=[".ts", ".tsx"],
                exclude=common_exclude,
                parser=LanguageParser(language=Language.TS, parser_threshold=500)
            )
            all_documents.extend(ts_loader.load())
        except Exception as e:
            logger.warning(f"Erreur lors du chargement du code TS : {e}")

        if not all_documents:
            logger.info("Aucun document trouvé à indexer.")
            return

        logger.info(f"{len(all_documents)} documents/fichiers trouvés. Découpage en cours...")

        # Découper intelligemment les documents en morceaux (chunks)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_documents(all_documents)
        
        logger.info(f"{len(texts)} chunks générés. Insertion dans ChromaDB...")

        # Sauvegarder dans la base vectorielle locale
        self.db.add_documents(texts)
        logger.info("Indexation terminée avec succès ! La base de données est à jour.")

    def search(self, query, top_k=3):
        """Cherche les extraits les plus pertinents par rapport à la question."""
        results = self.db.similarity_search(query, k=top_k)
        
        context = ""
        for i, doc in enumerate(results):
            source = doc.metadata.get('source', 'Fichier inconnu')
            context += f"\n--- Extrait {i+1} (Source: {source}) ---\n"
            context += doc.page_content + "\n"
        
        return context