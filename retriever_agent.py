"""
Retriever Agent - Handles data retrieval from various sources
Supports: Vector stores, document databases, internal knowledge bases
"""

from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
import logging
from logger_config import setup_logger

logger = setup_logger("retriever")


class RetrieverAgent:
    """
    Specialist agent for retrieving information from internal sources.
    Supports vector stores, document databases, and knowledge bases.
    """
    
    def __init__(
        self,
        llm=None,
        vector_store: Optional[VectorStore] = None,
        embeddings: Optional[Embeddings] = None,
        top_k: int = 5
    ):
        """
        Initialize the Retriever Agent
        
        Args:
            llm: Language model (optional, for query refinement)
            vector_store: Vector store instance (Pinecone, Chroma, FAISS, etc.)
            embeddings: Embedding model for vector search
            top_k: Number of documents to retrieve
        """
        self.llm = llm
        self.vector_store = vector_store
        self.embeddings = embeddings or OpenAIEmbeddings()
        self.top_k = top_k
        
        # Initialize default vector store if none provided
        if not self.vector_store:
            logger.warning("No vector store provided. Using in-memory fallback.")
            self._init_fallback_store()
    
    def _init_fallback_store(self):
        """Initialize vector store - tries to load pdf_knowledge_base, falls back to sample docs"""
        try:
            from langchain_community.vectorstores import FAISS
            from langchain_core.documents import Document
            import os
            
            # First, try to load the pdf_knowledge_base index
            index_path = os.path.join("./vector_store", "pdf_knowledge_base")
            
            if os.path.exists(index_path):
                try:
                    logger.info(f"Loading pdf_knowledge_base index from {index_path}...")
                    self.vector_store = FAISS.load_local(
                        index_path,
                        self.embeddings,
                        allow_dangerous_deserialization=True
                    )
                    logger.info("✅ Successfully loaded pdf_knowledge_base index")
                    return
                except Exception as e:
                    logger.warning(f"Failed to load pdf_knowledge_base: {e}. Using fallback sample documents.")
            else:
                logger.warning(f"pdf_knowledge_base not found at {index_path}. Using fallback sample documents.")
            
            # Fallback: Create some sample documents
            sample_docs = [
                Document(
                    page_content="LangChain is a framework for developing applications powered by language models.",
                    metadata={"source": "internal_docs", "topic": "langchain"}
                ),
                Document(
                    page_content="Vector stores enable semantic search by storing embeddings of documents.",
                    metadata={"source": "internal_docs", "topic": "vector_stores"}
                ),
                Document(
                    page_content="Agents can use tools to interact with external systems and APIs.",
                    metadata={"source": "internal_docs", "topic": "agents"}
                )
            ]
            
            self.vector_store = FAISS.from_documents(sample_docs, self.embeddings)
            logger.info("Initialized fallback FAISS vector store with sample documents")
        
        except Exception as e:
            logger.error(f"Failed to initialize fallback vector store: {e}")
            self.vector_store = None
    
    def retrieve(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None
    ) -> List[Document]:
        """
        Retrieve relevant documents based on query
        
        Args:
            query: Search query
            filters: Optional metadata filters
            top_k: Number of documents to retrieve (overrides default)
        
        Returns:
            List of relevant documents
        """
        if not self.vector_store:
            logger.warning("No vector store available. Returning empty results.")
            return []
        
        k = top_k or self.top_k
        
        try:
            logger.info(f"Retrieving top {k} documents for query: {query[:100]}...")
            
            # Perform similarity search
            if filters:
                docs = self.vector_store.similarity_search(
                    query,
                    k=k,
                    filter=filters
                )
            else:
                docs = self.vector_store.similarity_search(query, k=k)
            
            logger.info(f"Retrieved {len(docs)} documents")
            return docs
        
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return []
    
    def retrieve_with_scores(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
        score_threshold: float = 0.0
    ) -> List[tuple[Document, float]]:
        """
        Retrieve documents with relevance scores
        
        Args:
            query: Search query
            filters: Optional metadata filters
            top_k: Number of documents to retrieve
            score_threshold: Minimum relevance score (0.0 to 1.0)
        
        Returns:
            List of (document, score) tuples
        """
        if not self.vector_store:
            logger.warning("No vector store available. Returning empty results.")
            return []
        
        k = top_k or self.top_k
        
        try:
            logger.info(f"Retrieving documents with scores for: {query[:100]}...")
            
            # Perform similarity search with scores
            docs_with_scores = self.vector_store.similarity_search_with_score(
                query,
                k=k,
                filter=filters
            )
            
            # Filter by score threshold
            filtered_docs = [
                (doc, score) for doc, score in docs_with_scores
                if score >= score_threshold
            ]
            
            logger.info(f"Retrieved {len(filtered_docs)} documents above threshold {score_threshold}")
            return filtered_docs
        
        except Exception as e:
            logger.error(f"Retrieval with scores error: {e}")
            return []
    
    def retrieve_with_reranking(
        self,
        query: str,
        top_k: Optional[int] = None,
        rerank_top_n: int = 3
    ) -> List[Document]:
        """
        Retrieve and rerank documents using LLM
        
        Args:
            query: Search query
            top_k: Initial number of documents to retrieve
            rerank_top_n: Number of top documents after reranking
        
        Returns:
            Reranked list of documents
        """
        # First, retrieve more documents than needed
        initial_k = (top_k or self.top_k) * 2
        docs = self.retrieve(query, top_k=initial_k)
        
        if not docs or not self.llm:
            return docs[:rerank_top_n]
        
        try:
            logger.info(f"Reranking {len(docs)} documents...")
            
            # Use LLM to score relevance
            scored_docs = []
            for doc in docs:
                relevance_prompt = f"""
                Query: {query}
                Document: {doc.page_content[:500]}
                
                Rate the relevance of this document to the query on a scale of 0-10.
                Respond with only a number.
                """
                
                try:
                    score = float(self.llm.invoke(relevance_prompt).content.strip())
                    scored_docs.append((doc, score))
                except:
                    scored_docs.append((doc, 5.0))  # Default score
            
            # Sort by score and return top N
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            reranked = [doc for doc, score in scored_docs[:rerank_top_n]]
            
            logger.info(f"Reranked to top {len(reranked)} documents")
            return reranked
        
        except Exception as e:
            logger.error(f"Reranking error: {e}")
            return docs[:rerank_top_n]
    
    def retrieve_mmr(
        self,
        query: str,
        top_k: Optional[int] = None,
        fetch_k: int = 20,
        lambda_mult: float = 0.5
    ) -> List[Document]:
        """
        Retrieve using Maximum Marginal Relevance (MMR) for diversity
        
        Args:
            query: Search query
            top_k: Number of documents to return
            fetch_k: Number of documents to fetch before MMR
            lambda_mult: Diversity parameter (0=max diversity, 1=max relevance)
        
        Returns:
            Diverse list of relevant documents
        """
        if not self.vector_store:
            logger.warning("No vector store available. Returning empty results.")
            return []
        
        k = top_k or self.top_k
        
        try:
            logger.info(f"Retrieving with MMR (diversity={1-lambda_mult})...")
            
            docs = self.vector_store.max_marginal_relevance_search(
                query,
                k=k,
                fetch_k=fetch_k,
                lambda_mult=lambda_mult
            )
            
            logger.info(f"Retrieved {len(docs)} diverse documents")
            return docs
        
        except Exception as e:
            logger.error(f"MMR retrieval error: {e}")
            # Fallback to regular search
            return self.retrieve(query, top_k=k)
    
    def format_documents(self, docs: List[Document]) -> List[str]:
        """
        Format documents for context injection
        
        Args:
            docs: List of documents
        
        Returns:
            List of formatted strings
        """
        formatted = []
        for i, doc in enumerate(docs):
            source = doc.metadata.get("source", "Unknown")
            content = doc.page_content
            formatted.append(f"[Document {i+1}] (Source: {source})\n{content}")
        
        return formatted
    
    def add_documents(self, documents: List[Document]) -> bool:
        """
        Add new documents to the vector store
        
        Args:
            documents: List of documents to add
        
        Returns:
            Success status
        """
        if not self.vector_store:
            logger.error("No vector store available for adding documents")
            return False
        
        try:
            logger.info(f"Adding {len(documents)} documents to vector store...")
            self.vector_store.add_documents(documents)
            logger.info("Documents added successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            return False
    
    def search_by_metadata(
        self,
        filters: Dict[str, Any],
        top_k: Optional[int] = None
    ) -> List[Document]:
        """
        Search documents by metadata filters only
        
        Args:
            filters: Metadata filters (e.g., {"source": "manual", "category": "API"})
            top_k: Maximum number of documents to return
        
        Returns:
            List of matching documents
        """
        if not self.vector_store:
            logger.warning("No vector store available. Returning empty results.")
            return []
        
        try:
            logger.info(f"Searching by metadata: {filters}")
            
            # Use a generic query with strict filters
            docs = self.vector_store.similarity_search(
                "",  # Empty query to rely on filters
                k=top_k or self.top_k,
                filter=filters
            )
            
            logger.info(f"Found {len(docs)} documents matching filters")
            return docs
        
        except Exception as e:
            logger.error(f"Metadata search error: {e}")
            return []


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Example: Using the retriever agent
    from langchain_openai import ChatOpenAI
    
    # Initialize
    llm = ChatOpenAI(model="gpt-4o-mini")
    retriever = RetrieverAgent(llm=llm)
    
    # Retrieve documents
    query = "How do agents work in LangChain?"
    docs = retriever.retrieve(query, top_k=3)
    
    print(f"Retrieved {len(docs)} documents:")
    for i, doc in enumerate(docs):
        print(f"\n[{i+1}] {doc.page_content[:200]}...")
    
    # Format for context
    formatted = retriever.format_documents(docs)
    print(f"\nFormatted context:\n{formatted[0][:300]}...")
