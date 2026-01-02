"""
Import all PDF files from a folder into FAISS vector database
"""

from dotenv import load_dotenv
from data_import_faiss import FAISSDataImporter
from pathlib import Path
import os

# Load environment variables from .env file
load_dotenv()


def import_all_pdfs_from_folder(
    pdf_folder_path: str, 
    index_name: str = "pdf_knowledge_base",
    overwrite_existing: bool = True
):
    """
    Import all PDF files from a specified folder
    
    Args:
        pdf_folder_path: Path to folder containing PDF files
        index_name: Name for the saved vector store index
        overwrite_existing: If True, replace old index. If False, append to existing index.
    """
    print("=" * 80)
    print("PDF FOLDER IMPORT SCRIPT")
    print("=" * 80)
    
    # Check if folder exists
    if not os.path.exists(pdf_folder_path):
        print(f"❌ Error: Folder '{pdf_folder_path}' does not exist!")
        return
    
    # Get all PDF files in the folder
    pdf_folder = Path(pdf_folder_path)
    pdf_files = list(pdf_folder.glob("**/*.pdf"))  # Recursively find all PDFs
    
    if not pdf_files:
        print(f"❌ No PDF files found in '{pdf_folder_path}'")
        return
    
    print(f"\n📁 Found {len(pdf_files)} PDF file(s) in '{pdf_folder_path}':")
    for pdf in pdf_files:
        print(f"   - {pdf.name}")
    
    # Initialize importer
    print("\n🔧 Initializing importer...")
    importer = FAISSDataImporter(persist_directory="./vector_store")
    
    # Check if index already exists
    index_path = os.path.join("./vector_store", index_name)
    index_exists = os.path.exists(index_path)
    
    if index_exists and not overwrite_existing:
        print(f"\n📂 Loading existing index '{index_name}' to append new documents...")
        existing_store = importer.load(index_name)
        if existing_store:
            print("✅ Existing index loaded successfully")
        else:
            print("⚠️  Failed to load existing index, will create new one")
            index_exists = False
    elif index_exists and overwrite_existing:
        print(f"\n🗑️  Overwriting existing index '{index_name}'...")
    else:
        print(f"\n📝 Creating new index '{index_name}'...")
    
    # Convert Path objects to strings
    pdf_paths = [str(pdf) for pdf in pdf_files]
    
    # Load all PDFs
    print(f"\n📥 Loading {len(pdf_paths)} PDF files...")
    documents = importer.load_from_pdf(pdf_paths)
    
    if not documents:
        print("❌ No documents were loaded!")
        return
    
    print(f"✅ Loaded {len(documents)} document(s)")
    
    # Split documents into chunks
    print("\n✂️  Splitting documents into chunks...")
    split_docs = importer.split_documents(
        documents,
        chunk_size=1000,      # Adjust based on your needs
        chunk_overlap=200     # Overlap for better context
    )
    
    # Create vector store
    if index_exists and not overwrite_existing:
        # Append to existing store
        print("\n🔨 Adding documents to existing vector store...")
        importer.add_documents(split_docs)
        vector_store = importer.vector_store
    else:
        # Create new store (overwrite or first time)
        print("\n🔨 Creating new vector store...")
        vector_store = importer.create_vector_store(split_docs)
    
    # Save to disk
    print(f"\n💾 Saving to disk as '{index_name}'...")
    importer.save(index_name)
    
    # Test search
    print("\n🔍 Testing search...")
    test_query = "What is this document about?"
    results = vector_store.similarity_search(test_query, k=3)
    
    print(f"\nTest Query: '{test_query}'")
    print(f"Found {len(results)} results:\n")
    for i, doc in enumerate(results, 1):
        content_preview = doc.page_content[:150].replace('\n', ' ')
        print(f"[{i}] {content_preview}...")
        print(f"    Source: {doc.metadata.get('source', 'Unknown')}\n")
    
    print("=" * 80)
    action = "replaced" if overwrite_existing else "appended to existing"
    print(f"✅ SUCCESS! PDFs {action} in vector store: './vector_store/{index_name}'")
    print("=" * 80)
    print("\n📝 Next steps:")
    print(f"   1. Update retriever_agent.py to load this index: '{index_name}'")
    print("   2. Restart your API: python api.py")
    print("   3. Test queries against your PDF knowledge base!")
    print()


if __name__ == "__main__":
    # ========================================================================
    # CONFIGURATION - Edit these values
    # ========================================================================
    
    # Path to your PDF folder (change this to your folder path)
    PDF_FOLDER = "./pdf"  # Example: "./my_pdfs" or "C:/Documents/PDFs"
    
    # Name for the vector store index
    INDEX_NAME = "pdf_knowledge_base"
    
    # Overwrite existing index or append to it?
    # True  = Replace old index completely (fresh start)
    # False = Add new PDFs to existing index (keep old + add new)
    OVERWRITE_EXISTING = True
    
    # ========================================================================
    # Run the import
    # ========================================================================
    
    import_all_pdfs_from_folder(PDF_FOLDER, INDEX_NAME, OVERWRITE_EXISTING)
