"""
ChromaDB Vector Database Import Script
Alternative to FAISS with persistent storage and advanced features
"""

from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChromaDBImporter:
    """
    Handles importing data into ChromaDB vector store
    ChromaDB is more feature-rich than FAISS with built-in persistence
    """
    
    def __init__(
        self,
        collection_name: str = "langchain_docs",
        persist_directory: str = "./chroma_db",
        embeddings=None
    ):
        """
        Initialize ChromaDB importer
        
        Args:
            collection_name: Name of the collection
            persist_directory: Directory for persistent storage
            embeddings: Embedding model (defaults to OpenAI)
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embeddings = embeddings or OpenAIEmbeddings()
        self.vector_store = None
        
        logger.info(f"Initializing ChromaDB with collection: {collection_name}")
    
    def create_vector_store(
        self,
        documents: List[Document],
        metadata_keys: List[str] = None
    ) -> Chroma:
        """
        Create ChromaDB vector store from documents
        
        Args:
            documents: List of documents
            metadata_keys: Specific metadata keys to index
        
        Returns:
            Chroma vector store
        """
        logger.info(f"Creating ChromaDB vector store from {len(documents)} documents...")
        
        try:
            self.vector_store = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                collection_name=self.collection_name,
                persist_directory=self.persist_directory
            )
            
            logger.info("✅ ChromaDB vector store created successfully")
            logger.info(f"   Collection: {self.collection_name}")
            logger.info(f"   Persist directory: {self.persist_directory}")
            
            return self.vector_store
        
        except Exception as e:
            logger.error(f"❌ Failed to create vector store: {e}")
            raise
    
    def load_existing(self) -> Chroma:
        """
        Load existing ChromaDB collection
        
        Returns:
            Loaded Chroma vector store
        """
        logger.info(f"Loading existing collection: {self.collection_name}...")
        
        try:
            self.vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
            
            # Get collection stats
            collection = self.vector_store._collection
            count = collection.count()
            
            logger.info(f"✅ Collection loaded: {count} documents")
            return self.vector_store
        
        except Exception as e:
            logger.error(f"❌ Failed to load collection: {e}")
            return None
    
    def add_documents(self, documents: List[Document]):
        """
        Add documents to existing collection
        
        Args:
            documents: List of documents to add
        """
        if not self.vector_store:
            logger.error("No vector store loaded. Create or load one first.")
            return
        
        logger.info(f"Adding {len(documents)} documents to collection...")
        
        try:
            self.vector_store.add_documents(documents)
            logger.info("✅ Documents added successfully")
        except Exception as e:
            logger.error(f"❌ Failed to add documents: {e}")
    
    def delete_collection(self):
        """Delete the entire collection"""
        logger.info(f"Deleting collection: {self.collection_name}...")
        
        try:
            if self.vector_store:
                self.vector_store.delete_collection()
                logger.info("✅ Collection deleted")
        except Exception as e:
            logger.error(f"❌ Failed to delete collection: {e}")
    
    def search_with_filters(
        self,
        query: str,
        filter_dict: Dict[str, Any],
        k: int = 5
    ) -> List[Document]:
        """
        Search with metadata filters
        
        Args:
            query: Search query
            filter_dict: Metadata filters (e.g., {"category": "framework"})
            k: Number of results
        
        Returns:
            List of matching documents
        """
        if not self.vector_store:
            logger.error("No vector store loaded")
            return []
        
        logger.info(f"Searching with filters: {filter_dict}")
        
        try:
            results = self.vector_store.similarity_search(
                query,
                k=k,
                filter=filter_dict
            )
            logger.info(f"✅ Found {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection
        
        Returns:
            Dictionary with collection stats
        """
        if not self.vector_store:
            return {}
        
        collection = self.vector_store._collection
        
        stats = {
            "name": self.collection_name,
            "count": collection.count(),
            "persist_directory": self.persist_directory
        }
        
        logger.info(f"Collection stats: {stats}")
        return stats


# ============================================================================
# Example Usage
# ============================================================================

def main():
    """Main import script for ChromaDB"""
    print("=" * 80)
    print("CHROMADB VECTOR DATABASE IMPORT SCRIPT")
    print("=" * 80)
    
    # Initialize importer
    importer = ChromaDBImporter(
        collection_name="my_knowledge_base",
        persist_directory="./chroma_db"
    )
    
    # Create sample documents
    print("\n1. Creating sample documents...")
    sample_docs = [
        Document(
            page_content="ChromaDB is an open-source embedding database with built-in persistence and filtering capabilities.",
            metadata={"source": "chromadb_intro", "category": "database", "difficulty": "beginner"}
        ),
        Document(
            page_content="Unlike FAISS, ChromaDB provides automatic persistence, metadata filtering, and multi-modal support.",
            metadata={"source": "chromadb_features", "category": "database", "difficulty": "intermediate"}
        ),
        Document(
            page_content="ChromaDB supports various distance metrics including cosine similarity, L2, and inner product.",
            metadata={"source": "chromadb_metrics", "category": "technical", "difficulty": "advanced"}
        ),
    ]
    
    # Create vector store
    print("\n2. Creating vector store...")
    vector_store = importer.create_vector_store(sample_docs)
    
    # Get stats
    print("\n3. Collection statistics:")
    stats = importer.get_collection_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Test search
    print("\n4. Testing search...")
    query = "What is ChromaDB?"
    results = vector_store.similarity_search(query, k=2)
    
    print(f"\nQuery: {query}")
    print(f"Found {len(results)} results:\n")
    for i, doc in enumerate(results):
        print(f"[{i+1}] {doc.page_content}")
        print(f"    Metadata: {doc.metadata}\n")
    
    # Test filtered search
    print("\n5. Testing filtered search...")
    filtered_results = importer.search_with_filters(
        query="database features",
        filter_dict={"category": "database"},
        k=5
    )
    
    print(f"Found {len(filtered_results)} results with filter")
    
    print("\n" + "=" * 80)
    print("✅ Import complete! ChromaDB persisted to ./chroma_db")
    print("=" * 80)


if __name__ == "__main__":
    main()
