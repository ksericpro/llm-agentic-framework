# Vector Database & Import Scripts - Quick Reference

## 🎯 What We're Using

### **Primary Vector Database: FAISS**

**Why FAISS?**
- ✅ Fast in-memory similarity search
- ✅ No external dependencies or API costs
- ✅ Can persist to disk
- ✅ Perfect for development and small-medium datasets
- ✅ Easy to switch to other databases later

### **Alternative: ChromaDB** (Also Supported)
- Better for persistent storage
- Built-in metadata filtering
- Easier to query and manage

---

## 📥 Import Scripts Provided

### 1. **`data_import_faiss.py`** - FAISS Import Script

**Features:**
- Import from text files, PDFs, CSVs, Markdown
- Import entire directories
- Automatic document splitting
- Save/load from disk
- Sample documents for testing

**Quick Start:**
```bash
# Run with sample data
python data_import_faiss.py

# Creates: ./vector_store/faiss_index
```

**Import Your Own Data:**
```python
from data_import_faiss import FAISSDataImporter

importer = FAISSDataImporter()

# Option 1: From directory
docs = importer.load_from_directory("./my_docs", glob_pattern="**/*.txt")

# Option 2: From PDFs
docs = importer.load_from_pdf(["manual.pdf", "guide.pdf"])

# Option 3: From CSV
docs = importer.load_from_csv("data.csv", source_column="content")

# Split and create index
split_docs = importer.split_documents(docs, chunk_size=1000)
vector_store = importer.create_vector_store(split_docs)
importer.save("my_index")
```

### 2. **`data_import_chroma.py`** - ChromaDB Import Script

**Features:**
- Automatic persistence (no manual save needed)
- Advanced metadata filtering
- Collection management
- Statistics and monitoring

**Quick Start:**
```bash
# Install ChromaDB first
pip install chromadb

# Run import
python data_import_chroma.py

# Creates: ./chroma_db/
```

---

## 🔧 Integration with Pipeline

### Update `retriever_agent.py` to Use Your Data

Replace the `_init_fallback_store()` method:

```python
def _init_fallback_store(self):
    """Load your custom vector store"""
    try:
        from langchain_community.vectorstores import FAISS
        
        # Load your index
        self.vector_store = FAISS.load_local(
            "./vector_store/my_index",  # Your index name
            self.embeddings,
            allow_dangerous_deserialization=True
        )
        logger.info("✅ Loaded custom knowledge base")
    except Exception as e:
        logger.error(f"Failed to load index: {e}")
        # Create empty store as fallback
        from langchain_community.vectorstores import FAISS
        from langchain_core.documents import Document
        
        sample_doc = [Document(page_content="No data loaded")]
        self.vector_store = FAISS.from_documents(sample_doc, self.embeddings)
```

---

## 📊 Supported File Formats

| Format | Extension | Loader | Notes |
|--------|-----------|--------|-------|
| Text | `.txt` | TextLoader | UTF-8 encoding |
| PDF | `.pdf` | PyPDFLoader | Requires pypdf |
| CSV | `.csv` | CSVLoader | Specify source column |
| Markdown | `.md` | UnstructuredMarkdownLoader | Preserves structure |
| Directory | N/A | DirectoryLoader | Batch import |

---

## 🚀 Workflow

### 1. **Prepare Documents**
```
my_documents/
├── user_guide.pdf
├── faq.txt
├── api_docs.md
└── data.csv
```

### 2. **Run Import Script**
```bash
python data_import_faiss.py
```

Or customize:
```python
from data_import_faiss import FAISSDataImporter

importer = FAISSDataImporter()

# Load all your documents
pdf_docs = importer.load_from_pdf(["user_guide.pdf"])
text_docs = importer.load_from_directory("./docs", glob_pattern="**/*.txt")

all_docs = pdf_docs + text_docs
split_docs = importer.split_documents(all_docs, chunk_size=1000)

vector_store = importer.create_vector_store(split_docs)
importer.save("my_knowledge_base")
```

### 3. **Update Pipeline**
Modify `retriever_agent.py` to load your index (see above)

### 4. **Test**
```bash
# Test retriever directly
python retriever_agent.py

# Or test full pipeline
python api.py
```

### 5. **Query via API**
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I configure the system?", "stream": false}'
```

---

## 📝 Configuration Options

### Chunk Size Guidelines

| Document Type | Recommended Chunk Size | Overlap |
|---------------|----------------------|---------|
| Code snippets | 300-500 | 50-100 |
| Technical docs | 800-1000 | 150-200 |
| Long articles | 1500-2000 | 200-300 |
| FAQs | 500-800 | 100-150 |

### Example:
```python
split_docs = importer.split_documents(
    documents,
    chunk_size=1000,      # Characters per chunk
    chunk_overlap=200     # Overlap between chunks
)
```

---

## 🔄 Updating Your Vector Store

### Add New Documents
```python
# Load existing
importer = FAISSDataImporter()
vector_store = importer.load("my_index")

# Add new docs
new_docs = importer.load_from_text_files(["new_doc.txt"])
split_new = importer.split_documents(new_docs)

importer.vector_store = vector_store
importer.add_documents(split_new)
importer.save("my_index")
```

### Rebuild Completely
```python
import shutil
shutil.rmtree("./vector_store/my_index", ignore_errors=True)

# Re-run import script
```

---

## 🎯 Quick Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Create sample FAISS index
python data_import_faiss.py

# Create sample ChromaDB collection
python data_import_chroma.py

# Test retriever
python retriever_agent.py

# Start API with retrieval
python api.py

# Test query
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "stream": false}'
```

---

## 📚 Files Reference

| File | Purpose |
|------|---------|
| `data_import_faiss.py` | FAISS import script |
| `data_import_chroma.py` | ChromaDB import script |
| `retriever_agent.py` | Retrieval agent (uses vector store) |
| `VECTOR_DATABASE_GUIDE.md` | Detailed documentation |
| `./vector_store/` | FAISS index storage |
| `./chroma_db/` | ChromaDB storage |

---

## ✅ Summary

**Vector Database:** FAISS (default), ChromaDB (alternative)  
**Import Scripts:** ✅ Provided for both  
**Supported Formats:** Text, PDF, CSV, Markdown  
**Integration:** ✅ Ready to use with RetrieverAgent  
**Documentation:** ✅ Complete guide available  

**You're all set to import and use your own data! 🚀**
