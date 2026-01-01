# Vector Database Guide

## 📊 Current Setup

### Default Vector Database: **FAISS**

We're using **FAISS (Facebook AI Similarity Search)** as the default vector database because:

✅ **Lightweight** - No external dependencies  
✅ **Fast** - Optimized for similarity search  
✅ **In-memory** - Quick startup and testing  
✅ **Persistent** - Can save/load from disk  
✅ **Free** - No API costs  

### Alternative Options Supported

The `RetrieverAgent` is designed to work with **any LangChain-compatible vector store**:

| Vector DB | Best For | Pros | Cons |
|-----------|----------|------|------|
| **FAISS** | Development, Testing | Fast, lightweight, free | In-memory, no built-in filtering |
| **ChromaDB** | Small-Medium projects | Easy setup, persistent, filtering | Limited scale |
| **Pinecone** | Production, Scale | Managed, scalable, fast | Paid service |
| **Weaviate** | Enterprise | Feature-rich, GraphQL | Complex setup |
| **Qdrant** | High performance | Fast, filtering, cloud/local | Newer ecosystem |

---

## 🚀 Quick Start

### Option 1: Use FAISS (Recommended for Getting Started)

```bash
# 1. Run the import script
python data_import_faiss.py

# 2. This creates sample documents and saves to ./vector_store/faiss_index
```

### Option 2: Use ChromaDB (Better Persistence)

```bash
# 1. Install ChromaDB
pip install chromadb

# 2. Run the import script
python data_import_chroma.py

# 3. Data persists automatically to ./chroma_db
```

---

## 📥 Import Scripts Available

### 1. **FAISS Import** (`data_import_faiss.py`)

Comprehensive script for importing data into FAISS:

```python
from data_import_faiss import FAISSDataImporter

# Initialize
importer = FAISSDataImporter(persist_directory="./vector_store")

# Import from various sources
documents = importer.load_from_directory("./my_docs", glob_pattern="**/*.txt")
# OR
documents = importer.load_from_pdf(["manual.pdf", "guide.pdf"])
# OR
documents = importer.load_from_csv("data.csv", source_column="content")
# OR
documents = importer.create_sample_documents()  # For testing

# Split into chunks
split_docs = importer.split_documents(documents, chunk_size=1000)

# Create vector store
vector_store = importer.create_vector_store(split_docs)

# Save to disk
importer.save("faiss_index")
```

**Supported File Types:**
- ✅ Text files (`.txt`)
- ✅ PDF files (`.pdf`)
- ✅ CSV files (`.csv`)
- ✅ Markdown files (`.md`)
- ✅ Entire directories

### 2. **ChromaDB Import** (`data_import_chroma.py`)

Script for ChromaDB with automatic persistence:

```python
from data_import_chroma import ChromaDBImporter

# Initialize
importer = ChromaDBImporter(
    collection_name="my_knowledge_base",
    persist_directory="./chroma_db"
)

# Create vector store (auto-persists)
vector_store = importer.create_vector_store(documents)

# Search with filters
results = importer.search_with_filters(
    query="LangChain tutorial",
    filter_dict={"category": "framework"},
    k=5
)
```

---

## 🔧 Integration with Pipeline

### Using FAISS in Your Pipeline

```python
from retriever_agent import RetrieverAgent
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

# Load existing FAISS index
embeddings = OpenAIEmbeddings()
vector_store = FAISS.load_local(
    "./vector_store/faiss_index",
    embeddings,
    allow_dangerous_deserialization=True
)

# Create retriever agent with loaded store
retriever = RetrieverAgent(
    llm=llm,
    vector_store=vector_store,
    top_k=5
)

# Use in pipeline
docs = retriever.retrieve("How do I use LangChain?")
```

### Using ChromaDB in Your Pipeline

```python
from retriever_agent import RetrieverAgent
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

# Load existing ChromaDB collection
embeddings = OpenAIEmbeddings()
vector_store = Chroma(
    collection_name="my_knowledge_base",
    embedding_function=embeddings,
    persist_directory="./chroma_db"
)

# Create retriever agent
retriever = RetrieverAgent(
    llm=llm,
    vector_store=vector_store,
    top_k=5
)
```

---

## 📝 Step-by-Step: Import Your Own Data

### Step 1: Prepare Your Documents

Organize your documents in a directory:
```
my_documents/
├── manuals/
│   ├── user_guide.pdf
│   └── api_reference.pdf
├── faqs/
│   ├── common_questions.txt
│   └── troubleshooting.md
└── data/
    └── knowledge_base.csv
```

### Step 2: Run Import Script

```python
from data_import_faiss import FAISSDataImporter

# Initialize importer
importer = FAISSDataImporter(persist_directory="./vector_store")

# Load all text files
text_docs = importer.load_from_directory(
    "./my_documents/faqs",
    glob_pattern="**/*.txt"
)

# Load PDFs
pdf_docs = importer.load_from_pdf([
    "./my_documents/manuals/user_guide.pdf",
    "./my_documents/manuals/api_reference.pdf"
])

# Combine all documents
all_docs = text_docs + pdf_docs

# Split into chunks
split_docs = importer.split_documents(
    all_docs,
    chunk_size=1000,
    chunk_overlap=200
)

# Create and save vector store
vector_store = importer.create_vector_store(split_docs)
importer.save("my_knowledge_base")

print(f"✅ Imported {len(split_docs)} document chunks")
```

### Step 3: Update RetrieverAgent

Modify `retriever_agent.py` to load your index by default:

```python
# In RetrieverAgent.__init__
if not self.vector_store:
    # Load your custom index instead of creating sample docs
    try:
        from langchain_community.vectorstores import FAISS
        self.vector_store = FAISS.load_local(
            "./vector_store/my_knowledge_base",
            self.embeddings,
            allow_dangerous_deserialization=True
        )
        logger.info("Loaded custom knowledge base")
    except:
        logger.warning("Custom index not found, using fallback")
        self._init_fallback_store()
```

### Step 4: Test Your Setup

```python
from retriever_agent import RetrieverAgent
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")
retriever = RetrieverAgent(llm=llm)

# Test retrieval
docs = retriever.retrieve("How do I configure the API?", top_k=3)

for i, doc in enumerate(docs):
    print(f"\n[{i+1}] {doc.page_content[:200]}...")
    print(f"Source: {doc.metadata.get('source', 'Unknown')}")
```

---

## 🎯 Common Use Cases

### Use Case 1: Company Knowledge Base

```python
# Import company docs
importer = FAISSDataImporter()

# Load from SharePoint/OneDrive export
docs = importer.load_from_directory(
    "./company_docs",
    glob_pattern="**/*.{txt,md,pdf}"
)

split_docs = importer.split_documents(docs, chunk_size=800)
vector_store = importer.create_vector_store(split_docs)
importer.save("company_kb")
```

### Use Case 2: Customer Support FAQs

```python
# Import FAQ CSV
importer = FAISSDataImporter()

docs = importer.load_from_csv(
    "support_faqs.csv",
    source_column="answer"  # Column with FAQ answers
)

vector_store = importer.create_vector_store(docs)
importer.save("support_kb")
```

### Use Case 3: Technical Documentation

```python
# Import API docs and guides
importer = FAISSDataImporter()

# Load markdown docs
md_docs = importer.load_from_markdown([
    "docs/getting_started.md",
    "docs/api_reference.md",
    "docs/examples.md"
])

# Split with smaller chunks for code snippets
split_docs = importer.split_documents(md_docs, chunk_size=500)

vector_store = importer.create_vector_store(split_docs)
importer.save("tech_docs_kb")
```

---

## 🔄 Updating Your Vector Store

### Add New Documents

```python
from data_import_faiss import FAISSDataImporter

# Load existing index
importer = FAISSDataImporter()
vector_store = importer.load("my_knowledge_base")

# Add new documents
new_docs = importer.load_from_text_files(["new_doc.txt"])
split_new_docs = importer.split_documents(new_docs)

# Add to existing store
importer.vector_store = vector_store
importer.add_documents(split_new_docs)

# Save updated index
importer.save("my_knowledge_base")
```

### Rebuild from Scratch

```python
# Delete old index
import shutil
shutil.rmtree("./vector_store/my_knowledge_base", ignore_errors=True)

# Re-import all documents
# ... (run import script again)
```

---

## 📊 Performance Tips

### 1. **Chunk Size**
- **Small chunks (300-500)**: Better for precise answers, code snippets
- **Medium chunks (800-1000)**: Balanced, good default
- **Large chunks (1500-2000)**: Better context, but less precise

### 2. **Chunk Overlap**
- Use 10-20% of chunk size
- Ensures context isn't lost at boundaries

### 3. **Metadata**
- Add rich metadata for filtering:
  ```python
  Document(
      page_content="...",
      metadata={
          "source": "user_guide.pdf",
          "page": 42,
          "category": "installation",
          "version": "2.0",
          "last_updated": "2024-01-15"
      }
  )
  ```

### 4. **Embeddings**
- **OpenAI** (default): High quality, paid
- **HuggingFace**: Free, local, various models
- **Cohere**: Good quality, paid

---

## 🚨 Troubleshooting

### Issue: "No module named 'faiss'"
```bash
pip install faiss-cpu
# OR for GPU support
pip install faiss-gpu
```

### Issue: "No module named 'chromadb'"
```bash
pip install chromadb
```

### Issue: "Failed to load index"
- Check if index file exists
- Verify embeddings model matches the one used to create index
- Use `allow_dangerous_deserialization=True` for FAISS

### Issue: "Out of memory"
- Reduce chunk size
- Process documents in batches
- Use disk-based vector stores (ChromaDB, Qdrant)

---

## 📚 Additional Resources

- **FAISS Documentation**: https://github.com/facebookresearch/faiss
- **ChromaDB Documentation**: https://docs.trychroma.com/
- **LangChain Vector Stores**: https://python.langchain.com/docs/modules/data_connection/vectorstores/

---

## ✅ Summary

**Current Setup:**
- ✅ Default: FAISS (in-memory, fast, free)
- ✅ Import scripts provided for FAISS and ChromaDB
- ✅ Support for: Text, PDF, CSV, Markdown
- ✅ Easy to switch to other vector databases

**Next Steps:**
1. Run `python data_import_faiss.py` to create sample index
2. Import your own documents using the scripts
3. Update `retriever_agent.py` to load your index
4. Test with `python retriever_agent.py`

**Your vector database is ready to power intelligent retrieval! 🚀**
