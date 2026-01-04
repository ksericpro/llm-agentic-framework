# Knowledge Bot Agentic Pipeline

A production-ready multi-agent LLM pipeline built with **LangChain**, **LangGraph**, and **FastAPI** that supports real-time streaming responses and async background processing with Redis.

## Applied AI or AI engineering:

- Using AI models (LLMs) as components
- Building systems around them (agents, memory, tools)
- Operating them reliably (queues, monitoring, MLOps)
- Improving them systematically (DSPy, evaluation)

## 🌟 New Features (v2 Alpha)

- **DSPy Integration (Phase 1)**: The **Router Agent** is now powered by **DSPy**, an advanced framework for optimizing LM prompts.
  - **Self-Improving**: The system can "compile" itself to learn better routing logic from examples.
  - **Hybrid Architecture**: Combines the determinism of LangChain with the optimization power of DSPy.


## 🌟 Features

- **Multi-Agent Architecture**: Router, Intent Planning, Retrieval, Translator, Generator, and Critic agents.
- **Async Job Queue**: Robust background processing using **Redis Queue** and Workers, decoupling execution from API connections.
- **Advanced Web Crawling**: Integration with **Crawl4AI** for JavaScript rendering and clean Markdown extraction.
- **Multilingual Support**: Built-in **Translation Agent** for universal output in Chinese, Spanish, French, German, and Japanese.
- **Hierarchical Memory**: Scalable conversation history using multi-level summarization for 100+ message sessions.
- **Observability**: Full tracing and monitoring integrated with **Langfuse**.
- **Real-time Streaming**: Progressive responses via Server-Sent Events (SSE) (supports both direct and queued modes).
- **Persistent Feedback**: Built-in thumbs up/down system with MongoDB storage and analytics.
- **Unified UI/UX**: Custom branding (Avatars, Titles) and consistent feature set (History, Deletion, Streaming) across both Next.js and Streamlit apps.
- **Smart UI**: Modern Streamlit dashboard with sticky headers, session history (24h filter), and tool-usage badges.

## 📋 Architecture

![Architecture Diagram](main_pipeline.png)

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or navigate to the project
cd c:\Projects\llm-framework\orchestrator

# Install dependencies using uv (recommended for speed)
uv pip install -r requirements.txt

# Install Playwright browsers (for Advanced Crawler)
uv run playwright install chromium
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
MONGO_URL=your-mongo-url-here
REDIS_URL=redis://localhost:6379/0  # Required for Queue/Worker
LANGFUSE_PUBLIC_KEY=your-public-key
LANGFUSE_SECRET_KEY=your-secret-key
```

**Get API Keys:**
- OpenAI: https://platform.openai.com/api-keys
- Tavily (for web search): https://tavily.com
- MongoDB: https://www.mongodb.com
- Langfuse: https://langfuse.com

### 3. Running the System

To run the full system with the reliable Redis Queue architecture, you need to run three components:

**1. Redis Server**
Ensure you have a Redis server running locally or accessible via `REDIS_URL`.

**2. API Server (Terminal 1)**
Handles HTTP requests and queues jobs.
```bash
cd orchestrator && uv run python -m uvicorn api:app --reload --port 8000
```

**3. Background Worker (Terminal 2)**
Processes jobs from the queue and publishes updates.
```bash
cd orchestrator && uv run python worker.py
```

**4. Frontend UI (Terminal 3)**
Choose *one* of the available frontends:

**Option A: Streamlit (Python)**
Great for quick visualizations and data science.
![Streamlit UI](streamlit_ui.png)
```bash
cd ui/streamlit-ui && uv run python -m streamlit run app.py
```

**Option B: Next.js (React/TypeScript)**
Modern, responsive web application.
![Next.js UI](nextjs_ui.png)
```bash
cd ui/nextjs-app
npm install  # First time only
npm run dev
```


### 5. Scaling Workers (Optional)

To handle higher traffic, you can start multiple worker processes. They will automatically coordinate using the Redis Queue.

**How it works:**
- **Load Balancing**: Workers use a "First Come, First Served" model (competing consumer pattern) via Redis `BLPOP`.
- **Concurrency**: If you have 10 workers, you can process 10 AI queries simultaneously.
- **Auto-Distribution**: Idle workers instantly pick up new jobs. If a worker crashes, the others keep running.

To scale, simply open more terminals and run the worker command again:
```bash
# Terminal 4, 5, 6...
cd orchestrator && uv run python worker.py
```

*Note: In production (e.g., Docker/K8s), simply increase the replica count for the worker container.*


## 📡 API Endpoints

### Async Queue Query (Recommended)

1. **Submit Job**:
```bash
POST /api/queue
{ "query": "..." }
```
Response:
```json
{ "success": true, "request_id": "uuid...", "stream_url": "/api/stream/uuid..." }
```

2. **Listen for Updates**:
```bash
GET /api/stream/{request_id}
```

### Legacy Endpoints

- `POST /api/chat`: Dual-mode (stream/sync) endpoint.
- `POST /api/query`: Synchronous (blocking) endpoint.
- `POST /api/stream`: Direct SSE streaming endpoint.

## 💻 Usage Examples

### Python Client (Async Queue)

```python
import requests
import sseclient

# 1. Submit Job
response = requests.post("http://localhost:8000/api/queue", json={"query": "Hello"})
req_id = response.json()['request_id']

# 2. Listen
messages = sseclient.SSEClient(f"http://localhost:8000/api/stream/{req_id}")
for msg in messages:
    print(msg.data)
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
| `target_language` | string | `English` | Global translation (Chinese, Spanish, French, etc.) |

### Supported Models

- `gpt-4o-mini` (default, fast and cost-effective)
- `gpt-4o` (most capable)
- `gpt-4-turbo`
- `gpt-3.5-turbo`

## 🏗️ Project Structure

```
llm-agentic/
├── docs/                       # Project documentation
├── orchestrator/               # Backend & Core Agents
│   ├── api.py                  # FastAPI application
│   ├── worker.py               # Background Worker Process
│   ├── redis_client.py         # Redis utility (Queue/PubSub)
│   ├── langchain_pipeline.py   # LangGraph pipeline implementation
│   ├── router_agent.py         # Router agent
│   ├── intentplanning_agent.py # Intent & planning agent
│   ├── translation_agent.py    # Translation agent
│   ├── generator_agent.py      # Answer generator agent
│   ├── critic_agent.py         # Quality assurance agent
│   ├── retriever_agent.py      # Vector store retrieval agent
│   ├── tool_agent.py           # Tool execution agent
│   ├── crawler_agent.py        # Advanced Crawl4AI implementation
│   ├── example_client.py       # Example client code
│   ├── requirements.txt        # Python dependencies
│   └── .env.example            # Environment variables template
├── postman/                    # API Testing Collections
├── ui/                         # Frontend Applications
│   ├── streamlit-ui/           # Streamlit dashboard
│   │   ├── app.py              # Main dashboard script
│   │   └── bot-icon.png        # Custom AI avatar
│   └── nextjs-app/             # Modern React/Next.js App
│       ├── public/             
│       │   └── bot-icon.png    # Custom AI avatar
│       └── src/                # Next.js source code
├── main_pipeline.png           # Architecture diagram source
└── README.md                   # This file
```

## 🔍 Agent Details

### 1. Router Agent (DSPy Optimized)
- **Purpose**: Determines the best tool/approach for the query
- **Technology**: Built with **DSPy** for self-optimizing classification.
- **Decisions**: `web_search`, `targeted_crawl`, `internal_retrieval`, `calculator`, `translate`
- **Output**: Routing decision with reasoning and target metadata
- **Auto-Compilation**: Automatically compiles improved prompts on the first run.

### 2. Intent & Planning Agent
- **Purpose**: Analyzes user intent and creates execution plan
- **Output**: Intent classification and step-by-step plan

### 3. Retriever Agent
- **Purpose**: Handles vector store and document retrieval
- **Features**: 
  - Multiple search strategies (similarity, MMR, reranking)
  - Support for FAISS, ChromaDB, Pinecone, etc.
  - Metadata filtering
  - Document formatting
- **Output**: Retrieved documents with metadata

### 4. Tool Agent
- **Purpose**: Manages and executes various tools
- **Advanced Crawler**: Uses **Crawl4AI** for high-quality Markdown scraping with JS rendering.
- **Tools**:
  - Web search (Tavily Python API - updated version)
  - Calculator (safe mathematical evaluation)
  - API caller (standard HTTP requests)
- **Output**: Tool execution results formatted for LLMs.

### 5. Memory Management
- **Hierarchical Summarization**: Prevents context loss in extremely long conversations by summarizing previous summaries.
- **Context Clearing**: Supports `/forget` command to reset memory while maintaining session persistence.
- **Visual Warnings**: UI alerts when conversation length may impact performance.

### 6. Translation Agent
- **Purpose**: Specialized linguistic agent for high-quality translation.
- **Features**: 
  - Preserves Markdown formatting.
  - Maintains tone and nuances.
  - Supports Universal UI Translation (Global Toggle).
  - Standalone "Translate Tool" for fast direct queries.

### 7. Generator Agent
- **Purpose**: Synthesizes final answer from context
- **Features**: Citation extraction, format control, confidence scoring
- **Output**: Draft answer with citations

### 8. Critic Agent
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

This project is licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for details.

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



**Built with ❤️ using LangChain, LangGraph, LangFuse, SSE, Redis, MongoDB, Redis Queue, UV, Ruff, and FastAPI**

**Author:** Eric See  
**Email:** ksericpro@gmail.com  
**Last Updated:** 2026-01-04 (Phase 1: DSPy Router Integrated)
