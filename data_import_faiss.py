"""
FAISS Vector Database Import Script
Imports documents from various sources into FAISS vector store
"""

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    DirectoryLoader,
    CSVLoader,
    UnstructuredMarkdownLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List
import os
from pathlib import Path
import logging

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FAISSDataImporter:
    """
    Handles importing data into FAISS vector store from various sources
    """
    
    def __init__(self, embeddings=None, persist_directory="./vector_store"):
        """
        Initialize the importer
        
        Args:
            embeddings: Embedding model (defaults to OpenAI)
            persist_directory: Directory to save FAISS index
        """
        self.embeddings = embeddings or OpenAIEmbeddings()
        self.persist_directory = persist_directory
        self.vector_store = None
        
        # Create persist directory if it doesn't exist
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
    
    def load_from_text_files(self, file_paths: List[str]) -> List[Document]:
        """
        Load documents from text files
        
        Args:
            file_paths: List of text file paths
        
        Returns:
            List of documents
        """
        logger.info(f"Loading {len(file_paths)} text files...")
        
        documents = []
        for file_path in file_paths:
            try:
                loader = TextLoader(file_path, encoding='utf-8')
                docs = loader.load()
                documents.extend(docs)
                logger.info(f"✅ Loaded: {file_path}")
            except Exception as e:
                logger.error(f"❌ Failed to load {file_path}: {e}")
        
        return documents
    
    def load_from_directory(
        self,
        directory_path: str,
        glob_pattern: str = "**/*.txt",
        loader_cls=TextLoader
    ) -> List[Document]:
        """
        Load all documents from a directory
        
        Args:
            directory_path: Path to directory
            glob_pattern: File pattern to match (e.g., "**/*.txt", "**/*.pdf")
            loader_cls: Loader class to use
        
        Returns:
            List of documents
        """
        logger.info(f"Loading documents from {directory_path} with pattern {glob_pattern}...")
        
        try:
            loader = DirectoryLoader(
                directory_path,
                glob=glob_pattern,
                loader_cls=loader_cls,
                show_progress=True
            )
            documents = loader.load()
            logger.info(f"✅ Loaded {len(documents)} documents from directory")
            return documents
        except Exception as e:
            logger.error(f"❌ Failed to load directory: {e}")
            return []
    
    def load_from_pdf(self, pdf_paths: List[str]) -> List[Document]:
        """
        Load documents from PDF files
        
        Args:
            pdf_paths: List of PDF file paths
        
        Returns:
            List of documents
        """
        logger.info(f"Loading {len(pdf_paths)} PDF files...")
        
        documents = []
        for pdf_path in pdf_paths:
            try:
                loader = PyPDFLoader(pdf_path)
                docs = loader.load()
                documents.extend(docs)
                logger.info(f"✅ Loaded: {pdf_path}")
            except Exception as e:
                logger.error(f"❌ Failed to load {pdf_path}: {e}")
        
        return documents
    
    def load_from_csv(self, csv_path: str, source_column: str = None) -> List[Document]:
        """
        Load documents from CSV file
        
        Args:
            csv_path: Path to CSV file
            source_column: Column to use as document content
        
        Returns:
            List of documents
        """
        logger.info(f"Loading CSV: {csv_path}...")
        
        try:
            loader = CSVLoader(
                file_path=csv_path,
                source_column=source_column
            )
            documents = loader.load()
            logger.info(f"✅ Loaded {len(documents)} rows from CSV")
            return documents
        except Exception as e:
            logger.error(f"❌ Failed to load CSV: {e}")
            return []
    
    def load_from_markdown(self, md_paths: List[str]) -> List[Document]:
        """
        Load documents from Markdown files
        
        Args:
            md_paths: List of Markdown file paths
        
        Returns:
            List of documents
        """
        logger.info(f"Loading {len(md_paths)} Markdown files...")
        
        documents = []
        for md_path in md_paths:
            try:
                loader = UnstructuredMarkdownLoader(md_path)
                docs = loader.load()
                documents.extend(docs)
                logger.info(f"✅ Loaded: {md_path}")
            except Exception as e:
                logger.error(f"❌ Failed to load {md_path}: {e}")
        
        return documents
    
    def create_sample_documents(self) -> List[Document]:
        """
        Create sample documents for testing
        
        Returns:
            List of sample documents
        """
        logger.info("Creating sample documents...")
        
        sample_docs = [
            Document(
                page_content="LangChain is a framework for developing applications powered by language models. It provides tools for prompt management, chains, agents, and memory.",
                metadata={"source": "langchain_intro", "category": "framework", "topic": "langchain"}
            ),
            Document(
                page_content="Vector stores enable semantic search by storing embeddings of documents. Popular options include FAISS, Pinecone, Weaviate, and ChromaDB.",
                metadata={"source": "vector_stores", "category": "technology", "topic": "vector_databases"}
            ),
            Document(
                page_content="Agents in LangChain can use tools to interact with external systems. They decide which tools to use based on the user's query and available context.",
                metadata={"source": "agents_guide", "category": "framework", "topic": "agents"}
            ),
            Document(
                page_content="RAG (Retrieval Augmented Generation) combines retrieval from a knowledge base with LLM generation to provide accurate, grounded responses.",
                metadata={"source": "rag_explained", "category": "technique", "topic": "rag"}
            ),
            Document(
                page_content="Embeddings are vector representations of text that capture semantic meaning. OpenAI, Cohere, and HuggingFace provide embedding models.",
                metadata={"source": "embeddings_101", "category": "technology", "topic": "embeddings"}
            ),
            Document(
                page_content="FastAPI is a modern web framework for building APIs with Python. It provides automatic validation, serialization, and documentation.",
                metadata={"source": "fastapi_intro", "category": "framework", "topic": "fastapi"}
            ),
            Document(
                page_content="LangGraph is a library for building stateful, multi-actor applications with LLMs. It extends LangChain with graph-based workflows.",
                metadata={"source": "langgraph_guide", "category": "framework", "topic": "langgraph"}
            ),
            Document(
                page_content="Streaming responses improve user experience by providing incremental results. Server-Sent Events (SSE) is a common protocol for streaming.",
                metadata={"source": "streaming_guide", "category": "technique", "topic": "streaming"}
            ),
        ]
        
        logger.info(f"✅ Created {len(sample_docs)} sample documents")
        return sample_docs
    
    def split_documents(
        self,
        documents: List[Document],
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[Document]:
        """
        Split documents into smaller chunks
        
        Args:
            documents: List of documents to split
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks
        
        Returns:
            List of split documents
        """
        logger.info(f"Splitting {len(documents)} documents...")
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        split_docs = text_splitter.split_documents(documents)
        logger.info(f"✅ Split into {len(split_docs)} chunks")
        
        return split_docs
    
    def create_vector_store(self, documents: List[Document]) -> FAISS:
        """
        Create FAISS vector store from documents
        
        Args:
            documents: List of documents
        
        Returns:
            FAISS vector store
        """
        logger.info(f"Creating FAISS vector store from {len(documents)} documents...")
        
        try:
            self.vector_store = FAISS.from_documents(
                documents,
                self.embeddings
            )
            logger.info("✅ Vector store created successfully")
            return self.vector_store
        except Exception as e:
            logger.error(f"❌ Failed to create vector store: {e}")
            raise
    
    def add_documents(self, documents: List[Document]):
        """
        Add documents to existing vector store
        
        Args:
            documents: List of documents to add
        """
        if not self.vector_store:
            logger.error("No vector store exists. Create one first.")
            return
        
        logger.info(f"Adding {len(documents)} documents to vector store...")
        
        try:
            self.vector_store.add_documents(documents)
            logger.info("✅ Documents added successfully")
        except Exception as e:
            logger.error(f"❌ Failed to add documents: {e}")
    
    def save(self, index_name: str = "faiss_index"):
        """
        Save FAISS index to disk
        
        Args:
            index_name: Name of the index file
        """
        if not self.vector_store:
            logger.error("No vector store to save")
            return
        
        save_path = os.path.join(self.persist_directory, index_name)
        logger.info(f"Saving FAISS index to {save_path}...")
        
        try:
            self.vector_store.save_local(save_path)
            logger.info(f"✅ Index saved to {save_path}")
        except Exception as e:
            logger.error(f"❌ Failed to save index: {e}")
    
    def load(self, index_name: str = "faiss_index") -> FAISS:
        """
        Load FAISS index from disk
        
        Args:
            index_name: Name of the index file
        
        Returns:
            Loaded FAISS vector store
        """
        load_path = os.path.join(self.persist_directory, index_name)
        logger.info(f"Loading FAISS index from {load_path}...")
        
        try:
            self.vector_store = FAISS.load_local(
                load_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            logger.info("✅ Index loaded successfully")
            return self.vector_store
        except Exception as e:
            logger.error(f"❌ Failed to load index: {e}")
            return None


# ============================================================================
# Example Usage & Main Script
# ============================================================================

def main():
    """Main import script"""
    print("=" * 80)
    print("FAISS VECTOR DATABASE IMPORT SCRIPT")
    print("=" * 80)
    
    # Initialize importer
    importer = FAISSDataImporter(persist_directory="./vector_store")
    
    # Option 1: Create sample documents (for testing)
    print("\n1. Creating sample documents...")
    sample_docs = importer.create_sample_documents()
    
    # Option 2: Load from text files
    # text_files = ["doc1.txt", "doc2.txt"]
    # documents = importer.load_from_text_files(text_files)
    
    # Option 3: Load from directory
    # documents = importer.load_from_directory(
    #     "./documents",
    #     glob_pattern="**/*.txt"
    # )
    
    # Option 4: Load from PDFs
    # pdf_files = ["manual.pdf", "guide.pdf"]
    # documents = importer.load_from_pdf(pdf_files)
    
    # Option 5: Load from CSV
    # documents = importer.load_from_csv("data.csv", source_column="content")
    
    # Split documents into chunks
    print("\n2. Splitting documents...")
    split_docs = importer.split_documents(sample_docs, chunk_size=500, chunk_overlap=50)
    
    # Create vector store
    print("\n3. Creating vector store...")
    vector_store = importer.create_vector_store(split_docs)
    
    # Save to disk
    print("\n4. Saving to disk...")
    importer.save("faiss_index")
    
    # Test search
    print("\n5. Testing search...")
    query = "What is LangChain?"
    results = vector_store.similarity_search(query, k=3)
    
    print(f"\nQuery: {query}")
    print(f"Found {len(results)} results:\n")
    for i, doc in enumerate(results):
        print(f"[{i+1}] {doc.page_content[:100]}...")
        print(f"    Metadata: {doc.metadata}\n")
    
    print("=" * 80)
    print("✅ Import complete! Vector store saved to ./vector_store/faiss_index")
    print("=" * 80)


if __name__ == "__main__":
    main()
