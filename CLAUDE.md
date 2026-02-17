# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is a full-stack **RAG (Retrieval-Augmented Generation) Chatbot System** that answers questions about course materials. The architecture has two main parts:

### Backend Architecture (Python/FastAPI)
- **entry point**: `backend/app.py` - FastAPI application with two main endpoints
  - `POST /api/query` - Process user queries
  - `GET /api/courses` - Get course statistics
- **RAG Pipeline**: `backend/rag_system.py` - Orchestrates the retrieval and generation flow
  - Manages document processing, vector search, and AI generation
  - Handles session management for conversation continuity
- **AI Integration**: `backend/ai_generator.py` - Claude API client
  - Uses tool use pattern: Claude decides if a search is needed before answering
  - Two-step process: Claude chooses search → executes tool → generates final answer
- **Vector Search**: `backend/vector_store.py` - ChromaDB wrapper
  - Stores course metadata and content as embeddings
  - Searches using semantic similarity
- **Document Processing**: `backend/document_processor.py`
  - Parses structured course documents with lesson markers
  - Chunks text with overlap for context preservation
  - Extracts course metadata (title, instructor, links)
- **Supporting modules**:
  - `search_tools.py` - Implements the search tool Claude can use
  - `session_manager.py` - Manages conversation history per session
  - `models.py` - Pydantic data models
  - `config.py` - Configuration from environment variables

### Frontend Architecture (Vanilla JavaScript)
- `frontend/index.html` - UI layout
- `frontend/script.js` - Client-side logic
  - Sends queries to `/api/query` endpoint
  - Manages session state and conversation history
  - Displays responses with collapsible source references
- `frontend/style.css` - Styling

### Data Flow
1. Frontend sends user query to `/api/query` with optional session_id
2. FastAPI creates new session if needed, calls `RAGSystem.query()`
3. RAG system passes query to Claude with search tool available
4. Claude decides autonomously whether to search or answer from knowledge
5. If search needed: ChromaDB searches course content using embeddings
6. Claude gets search results and generates final answer
7. Backend returns answer + sources + session_id to frontend
8. Frontend displays answer with collapsible sources list

## Key Design Patterns

### Tool Use Pattern
Claude API is called with tool definitions. Claude autonomously decides if a search is needed:
- **General questions**: Answered using Claude's knowledge (no search)
- **Course-specific questions**: Claude triggers search first, then answers
This avoids unnecessary searches and improves response quality.

### Document Format
Course documents in `docs/` folder must follow this structure:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [instructor]

Lesson 0: [lesson title]
Lesson Link: [optional url]
[lesson content...]

Lesson 1: [lesson title]
[lesson content...]
```

The system recognizes "Lesson N:" markers to structure content hierarchically.

### Session Management
Conversations are tracked per session. Each session stores up to `MAX_HISTORY` (default 2) message exchanges for context. Sessions are created on first query and passed back to frontend.

### Chunking Strategy
Text is split into sentence-based chunks with overlap:
- Chunks built by combining sentences until reaching `CHUNK_SIZE` (800 chars)
- `CHUNK_OVERLAP` (100 chars) preserved between chunks for context
- Smart sentence splitting handles abbreviations and common edge cases
- First chunk of lesson includes lesson context for better retrieval

## Development Commands

### Critical: Use uv for All Dependency Management and Python Execution
**Never use pip, conda, or any other package manager.** Always use `uv` exclusively for:
- Installing dependencies (`uv sync`, `uv add`)
- Removing dependencies (`uv remove`)
- Running Python commands (`uv run python script.py`)
- Running Python files (`uv run python -m module_name`)
- Installing the project (`uv install`)

**All Python execution must go through `uv run`** - never run Python directly. This ensures consistent dependency resolution, lock file integrity, and environment reproducibility across all development environments.

Examples:
```bash
uv run python backend/app.py
uv run python -c "print('hello')"
uv run pytest tests/
```

### Running the Application
```bash
# Quick start (from root directory)
./run.sh

# Manual start (from root directory)
cd backend && uv run uvicorn app:app --reload --port 8000
```

The server starts on http://localhost:8000 with:
- Web UI at root `/`
- API docs at `/docs` (Swagger interactive explorer)
- Startup event loads all documents from `docs/` folder into vector database

### Installing Dependencies
```bash
# Install from pyproject.toml
uv sync

# Add new package
uv add package_name

# Run any command with uv (never use pip)
uv run python script.py
```

### Configuration
All configuration is in `backend/config.py` via environment variables:
- `ANTHROPIC_API_KEY` - Required for Claude API
- `ANTHROPIC_MODEL` - Claude model to use (default: claude-sonnet-4-20250514)
- `CHUNK_SIZE` - Text chunk size in characters
- `CHUNK_OVERLAP` - Overlap between chunks
- `MAX_RESULTS` - Max search results per query
- `MAX_HISTORY` - Messages to keep in conversation history
- `CHROMA_PATH` - Where to store vector database

Set these in `.env` file in root directory.

### Testing the API
Use the interactive API docs at `http://localhost:8000/docs` to test endpoints:
- **POST /api/query**: Send `{"query": "Your question", "session_id": null}`
- **GET /api/courses**: Get list of loaded courses

## Important Implementation Details

### Vector Store Collections
ChromaDB uses two collections:
- `course_catalog` - Course metadata (titles, instructors)
- `course_content` - Actual lesson content (searchable chunks)

### Embedding Model
Uses `all-MiniLM-L6-v2` from sentence-transformers. This is downloaded on first use (~60MB).

### Claude API Configuration
- **Temperature**: 0 (deterministic responses)
- **Max tokens**: 800
- **Tool choice**: "auto" (Claude decides if tool is needed)
- **System prompt**: Instructs Claude to search only for course-specific questions

### Error Handling
- Missing `.env` file will fail at startup with missing ANTHROPIC_API_KEY
- Invalid course document format is logged but non-fatal (chunk count = 0)
- Tool execution errors are caught and formatted as readable messages
- API returns 500 status with error detail on exceptions

## Modifying the System

### Adding a New API Endpoint
1. Create endpoint function in `backend/app.py` with `@app.get()` or `@app.post()`
2. Use existing Pydantic models or create new ones
3. Call appropriate RAGSystem method
4. Return response model

### Adding Course Content
Place `.txt`, `.pdf`, or `.docx` files in `docs/` folder following the document format above. They're auto-loaded on server startup via the startup event in `app.py`.

### Modifying Search Behavior
- Adjust `MAX_RESULTS` in `config.py` to return more/fewer search results
- Modify search filters in `CourseSearchTool.execute()` in `search_tools.py`
- Change embedding model in `config.py` (requires reindexing - clear `chroma_db/` folder)

### Changing Claude's System Prompt
Edit `SYSTEM_PROMPT` in `backend/ai_generator.py`. The prompt controls:
- When Claude decides to search
- Response format and style
- Available instructions to Claude

## Dependencies

Core dependencies in `pyproject.toml`:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `chromadb` - Vector database
- `sentence-transformers` - Embedding model
- `anthropic` - Claude API client
- `python-dotenv` - Environment variable loading

### Dependency Management with uv
- All dependencies are managed exclusively through `uv`
- `pyproject.toml` contains dependency specifications
- `uv.lock` file locks exact versions for reproducibility - **commit this to git**
- To update dependencies: `uv sync`
- To add new dependencies: `uv add package_name`
- To remove dependencies: `uv remove package_name`
- **Never modify `uv.lock` manually** - it's auto-generated by uv
