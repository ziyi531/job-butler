import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np

from backend.app.config import settings
from backend.app.services import llm_service

logger = logging.getLogger(__name__)

class SimpleVectorStore:
    """
    A lightweight, pure-Python vector database saved as a JSON file.
    Designed to prevent compiling/linking issues on Windows (which often happen with ChromaDB/HNSWLib).
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.data: List[Dict[str, Any]] = []  # items look like: {"project_name": str, "text": str, "vector": List[float]}
        self.load()

    def load(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                logger.info(f"Loaded {len(self.data)} vector entries from {self.db_path}")
            except Exception as e:
                logger.error(f"Error loading vector store JSON: {e}")
                self.data = []
        else:
            self.data = []

    def save(self):
        # Ensure directories exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(self.data)} vector entries to {self.db_path}")
        except Exception as e:
            logger.error(f"Error saving vector store JSON: {e}")

    def clear(self):
        self.data = []
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception as e:
                logger.error(f"Error deleting vector store file: {e}")

    def add_vectors(self, project_name: str, texts: List[str], vectors: List[List[float]]):
        for text, vec in zip(texts, vectors):
            self.data.append({
                "project_name": project_name,
                "text": text,
                "vector": vec
            })

    def query(self, query_vector: List[float], top_k: int = 4) -> List[Dict[str, Any]]:
        if not self.data or not query_vector:
            return []

        q_vec = np.array(query_vector)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []

        results: List[Tuple[float, Dict[str, Any]]] = []
        for item in self.data:
            i_vec = np.array(item["vector"])
            i_norm = np.linalg.norm(i_vec)
            if i_norm == 0:
                similarity = 0.0
            else:
                similarity = float(np.dot(q_vec, i_vec) / (q_norm * i_norm))
            results.append((similarity, item))

        # Sort by similarity descending
        results.sort(key=lambda x: x[0], reverse=True)
        
        # Return top K formatted
        top_results = []
        for sim, item in results[:top_k]:
            top_results.append({
                "project_name": item["project_name"],
                "text": item["text"],
                "score": sim
            })
        return top_results


# Singleton instance of vector store
vector_store = SimpleVectorStore(settings.VECTOR_DB_PATH)


def _chunk_text(text: str, max_words: int = 250, overlap: int = 50) -> List[str]:
    """Helper to chunk markdown text into overlapping segments."""
    # Split by double newline to preserve paragraph structure where possible
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_word_count = 0

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
            
        words = paragraph.split()
        p_word_count = len(words)
        
        # If a single paragraph is extremely long, split it by words
        if p_word_count > max_words:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_word_count = 0
            
            # Segment the single long paragraph
            for i in range(0, p_word_count, max_words - overlap):
                sub_words = words[i:i + max_words]
                chunks.append(" ".join(sub_words))
            continue

        if current_word_count + p_word_count > max_words:
            chunks.append("\n\n".join(current_chunk))
            # keep overlap (simple: just clear and start new, or keep last paragraph if it fits overlap)
            current_chunk = [paragraph]
            current_word_count = p_word_count
        else:
            current_chunk.append(paragraph)
            current_word_count += p_word_count

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def index_projects() -> Dict[str, Any]:
    """
    Scans the settings.PROJECTS_KB_DIR directory for all markdown files,
    chunks them, generates embeddings, and saves them to the local vector store.
    """
    kb_path = Path(settings.PROJECTS_KB_DIR)
    if not kb_path.exists():
        os.makedirs(kb_path, exist_ok=True)
        return {"status": "success", "indexed_files": 0, "chunks": 0}

    # Clear previous database state
    vector_store.clear()
    
    indexed_files = 0
    total_chunks = 0
    
    # Process markdown files
    for filepath in kb_path.glob("*.md"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            project_name = filepath.stem
            chunks = _chunk_text(content)
            
            if chunks:
                # Generate embeddings in batch
                embeddings = llm_service.get_embeddings(chunks)
                vector_store.add_vectors(project_name, chunks, embeddings)
                indexed_files += 1
                total_chunks += len(chunks)
                
        except Exception as e:
            logger.error(f"Error processing KB file {filepath}: {e}")
            raise RuntimeError(f"Error indexing {filepath.name}: {str(e)}")

    # Save to disk
    vector_store.save()
    return {
        "status": "success",
        "indexed_files": indexed_files,
        "chunks": total_chunks
    }


def query_projects(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """
    Search the personal project database for entries matching the query.
    """
    # Force reload of DB in case index changed
    vector_store.load()
    
    if not vector_store.data:
        # DB is empty, try to index first
        try:
            index_projects()
        except Exception as e:
            logger.error(f"Auto-index failed: {e}")
            return []

    try:
        # Generate query vector
        query_vectors = llm_service.get_embeddings([query])
        if query_vectors:
            return vector_store.query(query_vectors[0], top_k=top_k)
    except Exception as e:
        logger.error(f"Error querying projects RAG: {e}")
        
    return []
