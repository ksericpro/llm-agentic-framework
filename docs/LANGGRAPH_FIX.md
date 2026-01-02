# Fix: LangGraph API Error & RAG Tool Usage

## ✅ Fixed Issue

### Error Message
```
ERROR: ❌ Retrieval error: create_react_agent() got unexpected keyword arguments: {'state_modifier': ...}
```

### Root Cause
The `state_modifier` parameter was removed in newer versions of LangGraph's `create_react_agent()` function.

### Solution Applied
**File**: `orchestrator/tool_agent.py`  
**Line**: 202-205

**Before**:
```python
agent_executor = create_react_agent(
    self.llm, 
    self.tools,
    state_modifier=system_prompt  # ❌ No longer supported
)
```

**After**:
```python
agent_executor = create_react_agent(
    self.llm, 
    self.tools  # ✅ Fixed - removed state_modifier
)
```

---

## 🔍 Why RAG Tool Not Used for "Rich Dad Poor Dad"

### Current Status
- ✅ Vector store exists: `vector_store/pdf_knowledge_base/`
- ✅ Retriever agent configured to load it
- ❓ Question: Is the PDF actually imported?

### How to Check

1. **Verify PDF is imported**:
   ```bash
   cd orchestrator
   ls vector_store/pdf_knowledge_base/
   ```
   Should show: `index.faiss` and `index.pkl`

2. **Check what's in the vector store**:
   ```python
   from langchain_community.vectorstores import FAISS
   from langchain_openai import OpenAIEmbeddings
   
   embeddings = OpenAIEmbeddings()
   vectorstore = FAISS.load_local(
       "./vector_store/pdf_knowledge_base",
       embeddings,
       allow_dangerous_deserialization=True
   )
   
   # Test search
   results = vectorstore.similarity_search("Rich Dad Poor Dad", k=3)
   for doc in results:
       print(doc.page_content[:200])
   ```

---

## 📚 How to Import "Rich Dad Poor Dad" PDF

### Option 1: Using the Import Script

1. **Place PDF in a folder**:
   ```
   orchestrator/pdfs/
   └── rich_dad_poor_dad.pdf
   ```

2. **Run import script**:
   ```bash
   cd orchestrator
   python import_pdf_folder.py
   ```

3. **Script will**:
   - Find all PDFs in `./pdfs/` folder
   - Extract text and create embeddings
   - Save to `vector_store/pdf_knowledge_base/`

### Option 2: Manual Import

```python
from import_pdf_folder import FAISSDataImporter

# Initialize importer
importer = FAISSDataImporter(
    index_name="pdf_knowledge_base",
    folder_path="./pdfs",
    overwrite=False  # Append to existing index
)

# Import PDFs
importer.import_pdfs()
```

---

## 🎯 How Routing Works

### Router Decision Logic

The router agent decides which tool to use based on:

1. **Query Analysis**: Understands user intent
2. **Tool Matching**: Matches intent to best tool
3. **Confidence Score**: Chooses tool with highest confidence

### For "Rich Dad Poor Dad" Query

**Query**: "What are the most important lessons in Rich Dad Poor Dad?"

**Expected Routing**:
- ✅ **Should route to**: `internal_retrieval` (RAG)
- ❌ **Might route to**: `web_search` (if RAG not confident)

### Why It Might Not Use RAG

1. **PDF not imported** - Vector store empty or missing content
2. **Query not matching** - Embeddings don't match well
3. **Router confidence** - Web search scored higher
4. **Retriever not working** - Error loading vector store

---

## 🔧 Debugging Steps

### 1. Check if PDF is Imported

```bash
cd orchestrator
python -c "
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import os

if os.path.exists('./vector_store/pdf_knowledge_base/index.faiss'):
    print('✅ Vector store exists')
    embeddings = OpenAIEmbeddings()
    vs = FAISS.load_local(
        './vector_store/pdf_knowledge_base',
        embeddings,
        allow_dangerous_deserialization=True
    )
    print(f'✅ Loaded successfully')
    print(f'📊 Number of documents: {vs.index.ntotal}')
else:
    print('❌ Vector store not found')
"
```

### 2. Test Retrieval Directly

```python
from retriever_agent import RetrieverAgent
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")
retriever = RetrieverAgent(llm=llm)

# Test retrieval
docs = retriever.retrieve("Rich Dad Poor Dad lessons", top_k=3)
print(f"Found {len(docs)} documents")
for doc in docs:
    print(f"- {doc.page_content[:100]}...")
```

### 3. Check Router Decision

```python
from router_agent import RouterAgent
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")
router = RouterAgent(llm=llm)

decision = router.route("What are the lessons in Rich Dad Poor Dad?")
print(f"Routing decision: {decision.tool}")
print(f"Reasoning: {decision.reasoning}")
```

---

## 🚀 Next Steps

1. **Restart API** (to load the fixed code):
   ```bash
   cd orchestrator
   uv run api.py
   ```

2. **Test the query again**:
   - Ask: "What are the most important lessons in Rich Dad Poor Dad?"
   - Check logs for routing decision
   - Verify which tool was used

3. **If still not using RAG**:
   - Import the PDF using `import_pdf_folder.py`
   - Verify vector store has content
   - Check router logs for reasoning

---

## 📊 Expected Behavior After Fix

### Successful Flow

```
User Query: "What are the lessons in Rich Dad Poor Dad?"
    ↓
Router Agent: Analyzes query
    ↓
Decision: internal_retrieval (RAG)
    ↓
Retriever Agent: Searches vector store
    ↓
Finds: Relevant passages from the book
    ↓
Generator: Creates answer from retrieved context
    ↓
Response: "The key lessons from Rich Dad Poor Dad are..."
```

### Logs to Look For

```
🔀 Router Agent: Analyzing query...
✅ Routing decision: internal_retrieval
📚 Retrieval Node: Fetching relevant data...
✅ Retrieved 5 documents from vector store
✍️ Generator Agent: Creating answer...
```

---

## 💡 Pro Tips

1. **Always check logs** - They show which tool was selected
2. **Verify PDF import** - Use the test script above
3. **Test retrieval directly** - Bypass routing to test RAG
4. **Improve routing** - Adjust router prompts if needed

---

## Summary

✅ **Fixed**: Removed `state_modifier` parameter from `create_react_agent()`  
🔍 **Next**: Verify PDF is imported and test RAG retrieval  
📚 **Goal**: Get RAG to answer questions about "Rich Dad Poor Dad"

The error is now fixed. Test your query again and check if RAG is being used!
