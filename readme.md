# LangChain Agentic Pipeline with Streaming API

A production-ready multi-agent LLM pipeline built with **LangChain**, **LangGraph**, and **FastAPI** that supports real-time streaming responses.

## 🌟 Features

- **Multi-Agent Architecture**: Router, Intent Planning, Retrieval, Generator, and Critic agents
- **Streaming Support**: Real-time Server-Sent Events (SSE) for progressive responses
- **LangGraph Orchestration**: State-based workflow with conditional routing and revision loops
- **RESTful API**: FastAPI endpoints for easy integration
- **Web Search Integration**: Tavily API for current information retrieval
- **Quality Assurance**: Built-in critic agent for answer validation
- **Conversation Memory**: Support for chat history and context

## 📋 Architecture

```
User Query
    ↓
┌─────────────────────────────────────────────────────────┐
│                    Router Agent                         │
│  (Decides: web_search, targeted_crawl, internal, calc)  │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│              Intent & Planning Agent                     │
│         (Analyzes intent, creates plan)                  │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│                 Retrieval Node                           │
│  (Fetches data: web search, crawl, vector store)        │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│                 Generator Agent                          │
│         (Synthesizes final answer)                       │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│                  Critic Agent                            │
│    (Reviews quality, checks for hallucinations)          │
└─────────────────────────────────────────────────────────┘
    ↓
    ├─ Needs Revision? → Loop back to Generator
    └─ Approved → Finalize
         ↓
    Final Answer
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or navigate to the project
cd c:\Projects\llm-framework

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
OPENAI_API_KEY=sk-your-openai-key-here
TAVILY_API_KEY=tvly-your-tavily-key-here
```

**Get API Keys:**
- OpenAI: https://platform.openai.com/api-keys
- Tavily (for web search): https://tavily.com

### 3. Run the API

```bash
# Option 1: Direct Python
python api.py

# Option 2: Using uvicorn (recommended for production)
uvicorn api:app --reload --port 8000

# Option 3: Production mode
uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at: `http://localhost:8000`

### 4. Test the API

```bash
# Run the example client
python example_client.py
```

## 📡 API Endpoints

### Health Check

```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "openai_configured": true,
  "tavily_configured": true,
  "endpoints": {
    "query": "/api/query",
    "stream": "/api/stream"
  }
}
```

### Non-Streaming Query

```bash
POST /api/query
```

**Request:**
```json
{
  "query": "What are the latest developments in AI?",
  "chat_history": [
    {"role": "user", "content": "Previous question"},
    {"role": "assistant", "content": "Previous answer"}
  ],
  "model": "gpt-4o-mini",
  "temperature": 0.7
}
```

**Response:**
```json
{
  "success": true,
  "query": "What are the latest developments in AI?",
  "final_answer": "Based on recent web searches...",
  "intent": "web_search",
  "routing_decision": "web_search",
  "citations": [0, 1, 2],
  "error": null
}
```

### Streaming Query

```bash
POST /api/stream
```

**Request:** Same as `/api/query`

**Response:** Server-Sent Events (SSE) stream

```
data: {"event": "start", "query": "..."}

data: {"node": "router", "state": {...}}

data: {"node": "generator", "state": {"draft_answer": "..."}}

data: {"event": "complete"}
```

### Unified Chat Endpoint

```bash
POST /api/chat
```

Automatically routes to streaming or non-streaming based on `stream` flag.

## 💻 Usage Examples

### Python Client

```python
from example_client import AgenticPipelineClient

client = AgenticPipelineClient("http://localhost:8000")

# Non-streaming
result = client.query("Explain quantum computing")
print(result['final_answer'])

# Streaming
for event in client.stream_query("What is machine learning?"):
    if event.get('event') == 'complete':
        print("Done!")
    elif event.get('state', {}).get('final_answer'):
        print(event['state']['final_answer'])
```

### cURL

**Non-streaming:**
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the capital of France?",
    "stream": false
  }'
```

**Streaming:**
```bash
curl -X POST http://localhost:8000/api/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "query": "Explain neural networks",
    "stream": true
  }'
```

### JavaScript/TypeScript

```javascript
// Non-streaming
const response = await fetch('http://localhost:8000/api/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'What is deep learning?',
    stream: false
  })
});
const data = await response.json();
console.log(data.final_answer);

// Streaming with EventSource
const eventSource = new EventSource(
  'http://localhost:8000/api/stream?' + 
  new URLSearchParams({
    query: 'Explain transformers',
    stream: true
  })
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

## 🔧 Configuration Options

### Request Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | **required** | User's question or query |
| `chat_history` | array | `[]` | Previous conversation messages |
| `stream` | boolean | `false` | Enable streaming response |
| `model` | string | `gpt-4o-mini` | OpenAI model to use |
| `temperature` | float | `0.7` | LLM temperature (0.0-2.0) |

### Supported Models

- `gpt-4o-mini` (default, fast and cost-effective)
- `gpt-4o` (most capable)
- `gpt-4-turbo`
- `gpt-3.5-turbo`

## 🏗️ Project Structure

```
llm-framework/
├── api.py                      # FastAPI application
├── langchain_pipeline.py       # LangGraph pipeline implementation
├── router_agent.py             # Router agent
├── intentplanning_agent.py     # Intent & planning agent
├── generator_agent.py          # Answer generator agent
├── critic_agent.py             # Quality assurance agent
├── retriever_agent.py          # Vector store retrieval agent (NEW)
├── tool_agent.py               # Tool execution agent (NEW)
├── WebAgentWithGoogle.py       # Web search agent
├── example_client.py           # Example client code
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
└── README.md                   # This file
```

## 🔍 Agent Details

### 1. Router Agent
- **Purpose**: Determines the best tool/approach for the query
- **Decisions**: `web_search`, `targeted_crawl`, `internal_retrieval`, `calculator`
- **Output**: Routing decision with reasoning

### 2. Intent & Planning Agent
- **Purpose**: Analyzes user intent and creates execution plan
- **Output**: Intent classification and step-by-step plan

### 3. Retriever Agent (NEW)
- **Purpose**: Handles vector store and document retrieval
- **Features**: 
  - Multiple search strategies (similarity, MMR, reranking)
  - Support for FAISS, ChromaDB, Pinecone, etc.
  - Metadata filtering
  - Document formatting
- **Output**: Retrieved documents with metadata

### 4. Tool Agent (NEW)
- **Purpose**: Manages and executes various tools
- **Tools**:
  - Web search (Tavily API)
  - Calculator (math expressions)
  - Web scraper (URL content extraction)
  - API caller (HTTP requests)
  - Custom tools (extensible)
- **Output**: Tool execution results

### 5. Generator Agent
- **Purpose**: Synthesizes final answer from context
- **Features**: Citation extraction, format control, confidence scoring
- **Output**: Draft answer with citations

### 6. Critic Agent
- **Purpose**: Quality assurance and hallucination detection
- **Checks**: Factual consistency, completeness, safety
- **Output**: Pass/fail verdict with correction instructions

## 🔄 Workflow Features

### Revision Loop
The pipeline includes an automatic revision mechanism:
1. Generator creates draft answer
2. Critic reviews for quality
3. If issues found → Generator revises (max 2 iterations)
4. Final answer approved and returned

### State Management
LangGraph maintains state throughout the pipeline:
- Query and chat history
- Routing decisions
- Retrieved context
- Draft and final answers
- Critique feedback
- Error tracking

### Streaming Events
Real-time updates for each pipeline stage:
- Router decision
- Intent classification
- Data retrieval progress
- Answer generation
- Quality review
- Final completion

## 🧪 Testing

```bash
# Run example client
python example_client.py

# Test health endpoint
curl http://localhost:8000/health

# Test with specific query
python -c "
from example_client import AgenticPipelineClient
client = AgenticPipelineClient()
result = client.query('What is LangChain?')
print(result['final_answer'])
"
```

## 🚨 Error Handling

The API includes comprehensive error handling:

- **Validation errors**: Invalid request parameters
- **API key errors**: Missing or invalid credentials
- **LLM errors**: OpenAI API failures
- **Tool errors**: Web search or retrieval failures
- **Timeout errors**: Long-running operations

All errors return structured JSON responses:

```json
{
  "success": false,
  "error": "Error description",
  "detail": "Detailed error message"
}
```

## 📊 Performance Tips

1. **Use streaming** for long-running queries to improve UX
2. **Choose appropriate models**: `gpt-4o-mini` for speed, `gpt-4o` for quality
3. **Adjust temperature**: Lower (0.3) for factual, higher (0.9) for creative
4. **Limit chat history**: Keep last 5-10 messages for context
5. **Enable caching**: Consider adding Redis for repeated queries

## 🔐 Security Considerations

- Store API keys in `.env`, never commit to version control
- Use environment-specific configurations
- Implement rate limiting for production
- Add authentication/authorization as needed
- Validate and sanitize user inputs

## 📝 License

This project is provided as-is for educational and commercial use.

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional agent types (SQL, code execution, etc.)
- More retrieval sources (Pinecone, Weaviate, etc.)
- Advanced caching strategies
- Monitoring and observability
- Unit and integration tests

## 📞 Support

For issues or questions:
1. Check the example client code
2. Review API documentation at `/docs` (FastAPI auto-generated)
3. Enable debug logging: `LOG_LEVEL=DEBUG` in `.env`

---

**Built with ❤️ using LangChain, LangGraph, and FastAPI**

# how to run

# server
uv run api.py

# ui
uv run streamlit run ui/app.py
