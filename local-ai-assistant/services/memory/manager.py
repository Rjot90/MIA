"""
==============================================================================
MEMORY.PY - Couche de persistance mémoire (SQLite)
==============================================================================

Responsabilités :
1. Stockage conversations (historique)
2. Métadonnées utilisateur
3. Indexation searches
4. Compression/archivage automatique

Architecture:
- SQLAlchemy ORM (abstraction DB)
- SQLite (léger, pas de serveur)
- Async safe (thread-safe pour FastAPI)

Tables:
- conversations : historique messages
- user_metadata : infos utilisateur
- documents : index documents locaux
==============================================================================
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from contextlib import contextmanager

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, 
    Float, Boolean, Index, event, func
)
from sqlalchemy.orm import (
    declarative_base, sessionmaker, Session, scoped_session
)
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)


# ==============================================================================
# BASE SQLALCHEMY
# ==============================================================================

Base = declarative_base()


# ==============================================================================
# MODÈLES ORM
# ==============================================================================

class Conversation(Base):
    """
    Modèle pour stocker les messages de conversation.
    
    Structure:
    - id: identifiant unique
    - user_id: qui a écrit (pour multi-user futur)
    - role: "user" ou "assistant"
    - content: contenu message
    - timestamp: quand créé
    - tokens_used: coût inférence (estimation)
    - metadata: JSON futures extensions
    """
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), default="default", index=True)
    role = Column(String(50), index=True)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    tokens_used = Column(Integer, default=0)
    model_name = Column(String(255), default="qwen-2.5-7b")
    
    # Index composé pour recherche rapide user + timestamp
    __table_args__ = (
        Index("idx_user_timestamp", "user_id", "timestamp"),
    )
    
    def __repr__(self):
        return (
            f"<Conversation(id={self.id}, user={self.user_id}, "
            f"role={self.role}, tokens={self.tokens_used})>"
        )


class UserMetadata(Base):
    """
    Métadonnées utilisateur (contexte, préférences).
    
    Permet de :
    - Mémoriser style/ton préféré
    - Stocker contexte utilisateur
    - Tracker stats usage
    """
    __tablename__ = "user_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), unique=True, index=True)
    
    # Contexte
    language = Column(String(10), default="fr")
    timezone = Column(String(50), default="UTC")
    
    # Stats
    total_messages = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    last_interaction = Column(DateTime, default=datetime.utcnow)
    
    # Preferences JSON (future)
    preferences = Column(Text, default="{}")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return (
            f"<UserMetadata(user={self.user_id}, "
            f"messages={self.total_messages}, tokens={self.total_tokens})>"
        )


class DocumentIndex(Base):
    """
    Index des documents locaux consultables.
    
    Utilisé en Phase 3 pour RAG.
    """
    __tablename__ = "document_index"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(512), unique=True, index=True)
    filepath = Column(Text)
    file_type = Column(String(50))  # "pdf", "md", "txt", "code"
    size_bytes = Column(Integer)
    
    # Indexation
    indexed_at = Column(DateTime, default=datetime.utcnow)
    chunk_count = Column(Integer, default=0)
    
    # Métadonnées
    title = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<DocumentIndex(filename={self.filename}, chunks={self.chunk_count})>"


# ==============================================================================
# MEMORY MANAGER (Interface haute niveau)
# ==============================================================================

class MemoryManager:
    """
    Manager de mémoire persistante.
    
    Responsa:
    - Conversation CRUD
    - User metadata
    - Archivage/compression
    - Cleanup ancien contenu
    
    Thread-safe pour AsyncIO + FastAPI.
    """
    
    def __init__(self, db_path: str | Path):
        """
        Initialise le manager avec chemin DB SQLite.
        
        Args:
            db_path: Chemin vers fichier memory.db
        
        Exemple:
            >>> manager = MemoryManager("./data/memory.db")
        """
        self.db_path = Path(db_path)
        self.db_url = f"sqlite:///{self.db_path}"
        
        # Engine SQLite (StaticPool = pas de pool threads en SQLite)
        self.engine = create_engine(
            self.db_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False  # Set to True pour debug SQL
        )
        
        # Session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        # Scoped sessions pour thread-safety
        self.Session = scoped_session(self.SessionLocal)
        
        # Création tables
        self._init_db()
        
        logger.info(f"MemoryManager initialized - DB: {self.db_path}")
    
    def _init_db(self):
        """Crée tables si n'existent pas."""
        Base.metadata.create_all(bind=self.engine)
        logger.debug("Database tables created/verified")
    
    @contextmanager
    def get_session(self) -> Session:
        """
        Context manager pour sessions DB.
        
        Usage:
            with manager.get_session() as session:
                convs = session.query(Conversation).all()
        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Session error: {e}")
            raise
        finally:
            session.close()
    
    # ========================================================================
    # CONVERSATION METHODS
    # ========================================================================
    
    def add_message(
        self,
        role: str,
        content: str,
        user_id: str = "default",
        tokens_used: int = 0,
        model_name: str = "qwen-2.5-7b"
    ) -> int:
        """
        Ajoute un message à l'historique.
        
        Args:
            role: "user" ou "assistant"
            content: Contenu message
            user_id: Utilisateur (default=solo)
            tokens_used: Nombre tokens utilisés
            model_name: Quel modèle a généré
        
        Returns:
            ID du message inséré
        """
        with self.get_session() as session:
            msg = Conversation(
                user_id=user_id,
                role=role,
                content=content,
                tokens_used=tokens_used,
                model_name=model_name
            )
            session.add(msg)
            session.flush()
            msg_id = msg.id
        
        logger.debug(
            f"Message stored - role={role}, user={user_id}, tokens={tokens_used}"
        )
        return msg_id
    
    def get_conversation_history(
        self,
        user_id: str = "default",
        max_tokens: int = 2000
    ) -> List[Dict[str, Any]]:
        """
        Récupère l'historique conversations en respectant une limite de tokens (Sliding Window).
        
        Args:
            user_id: Utilisateur
            max_tokens: Nombre maximum de tokens pour l'historique retourné.
        
        Returns:
            List de dicts {role, content, timestamp, tokens_used}
        """
        with self.get_session() as session:
            # Récupérer les messages du plus récent au plus ancien
            messages = session.query(Conversation).filter(
                Conversation.user_id == user_id
            ).order_by(
                Conversation.timestamp.desc()
            ).all()
        
            history = []
            current_tokens = 0
            
            for m in messages:
                # Approximation des tokens si non fourni par le LLM (surtout pour les messages user)
                msg_tokens = m.tokens_used if m.tokens_used > 0 else len(m.content) // 4
                
                if current_tokens + msg_tokens > max_tokens:
                    break # La fenêtre glissante est pleine
                
                current_tokens += msg_tokens
                history.append({
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                    "tokens": m.tokens_used,
                    "model": m.model_name
                })
            
            # Retourner dans l'ordre chronologique (du plus ancien de la fenêtre au plus récent)
            return history[::-1]
    
    def get_conversation_context(
        self,
        user_id: str = "default",
        max_tokens: int = 2000
    ) -> str:
        """
        Reconstruit le contexte conversation pour inférence.
        
        Retourne format prêt à envoyer au LLM :
        "User: message 1\nAssistant: réponse 1\nUser: message 2\n..."
        """
        messages = self.get_conversation_history(
            user_id=user_id,
            max_tokens=max_tokens
        )
        
        if not messages:
            return ""
        
        # Construit contexte (simples heuristiques tokens)
        context = []
        for msg in messages:
            role = msg["role"].capitalize()
            context.append(f"{role}: {msg['content']}")
        
        return "\n".join(context)
    
    def clear_conversation(self, user_id: str = "default"):
        """Efface tout historique utilisateur."""
        with self.get_session() as session:
            session.query(Conversation).filter(
                Conversation.user_id == user_id
            ).delete()
        
        logger.info(f"Conversation cleared for user: {user_id}")
    
    # ========================================================================
    # METADATA METHODS
    # ========================================================================
    
    def get_or_create_user(self, user_id: str = "default") -> Dict[str, Any]:
        """Récupère ou crée utilisateur."""
        with self.get_session() as session:
            user = session.query(UserMetadata).filter(
                UserMetadata.user_id == user_id
            ).first()
            
            if not user:
                user = UserMetadata(user_id=user_id)
                session.add(user)
                session.flush()
            
            return {
                "user_id": user.user_id,
                "messages": user.total_messages,
                "tokens": user.total_tokens,
                "language": user.language
            }
    
    def update_user_stats(
        self,
        user_id: str = "default",
        tokens_used: int = 0
    ):
        """Met à jour stats utilisateur après inférence."""
        with self.get_session() as session:
            user = session.query(UserMetadata).filter(
                UserMetadata.user_id == user_id
            ).first()
            
            if user:
                user.total_messages += 2  # User + assistant
                user.total_tokens += tokens_used
                user.last_interaction = datetime.utcnow()
    
    # ========================================================================
    # ARCHIVAGE / NETTOYAGE
    # ========================================================================
    
    def archive_old_conversations(self, days: int = 30):
        """
        Archive (delete) conversations > N jours.
        
        Utile pour:
        - Limiter taille DB
        - Privacy (effacer données anciennes)
        - Perf DB
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        with self.get_session() as session:
            deleted = session.query(Conversation).filter(
                Conversation.timestamp < cutoff_date
            ).delete()
        
        logger.info(f"Archived {deleted} messages older than {days} days")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne stats DB."""
        with self.get_session() as session:
            total_messages = session.query(func.count(Conversation.id)).scalar()
            total_users = session.query(func.count(UserMetadata.id)).scalar()
            total_tokens = session.query(
                func.sum(Conversation.tokens_used)
            ).scalar() or 0
        
        return {
            "total_messages": total_messages,
            "total_users": total_users,
            "total_tokens": total_tokens,
            "db_size_mb": self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0
        }


# ==============================================================================
# INITIALIZATION (appel au démarrage)
# ==============================================================================

def init_memory(db_path: str | Path) -> MemoryManager:
    """Factory pour créer et initialiser MemoryManager."""
    manager = MemoryManager(db_path)
    stats = manager.get_stats()
    logger.info(f"Memory stats: {stats}")
    return manager
