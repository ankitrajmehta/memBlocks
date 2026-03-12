# Technology Stack

**Analysis Date:** 2026-03-12

## Languages

**Primary:**
- **Python 3.11+** - Backend API, CLI, and core library (`memblocks_lib`, `backend`)
- **JavaScript (ESM)** - Frontend application (`frontend`)

**Secondary:**
- **TypeScript** - Type definitions in frontend (`@types/react`, `@types/react-dom`)

## Runtime

**Frontend Environment:**
- Node.js 18+ (development)
- Vite 5.1.4 (build tool/dev server)

**Backend Environment:**
- Python 3.11+ (uvicorn, FastAPI)
- UV package manager (monorepo)

**Package Managers:**
- **npm** 8+ (frontend) - Lockfile: `frontend/package-lock.json`
- **UV** (Python workspace) - Lockfile: `uv.lock`

## Frameworks

**Frontend:**
- **React 18.3.1** - UI framework
- **Vite 5.1.4** - Build tool and dev server
- **React Router 7.13.1** - Client-side routing

**Backend:**
- **FastAPI 0.129.0+** - Web framework
- **Uvicorn 0.41.0+** - ASGI server

**Testing (Frontend):**
- Not detected - No test framework configured

**Testing (Backend):**
- Not detected - No test framework configured

**Styling:**
- **Tailwind CSS 3.4.1** - Utility-first CSS framework
- **PostCSS 8.4.35** - CSS transformation
- **Autoprefixer 10.4.18** - CSS vendor prefixes

**Linting/Formatting:**
- **ESLint 8.57.0** - JavaScript/JSX linting
- **ESLint Plugins:** react, react-hooks, react-refresh

## Key Dependencies

**Core Library (`memblocks_lib`):**
- **Pydantic 2.0+** - Data validation
- **Pydantic-settings 2.0+** - Settings management
- **LangChain 0.1+** - LLM orchestration framework
- **LangChain Core 0.1+** - Core abstractions
- **LangChain-Groq 0.1+** - Groq LLM integration
- **LangChain-OpenAI 0.1+** - OpenAI integration
- **LangChain-Google-GenAI 4.2.1+** - Google Gemini integration

**Vector Store & Database:**
- **Qdrant Client 1.7+** - Vector database client
- **Motor 3.0+** - MongoDB async driver

**Embeddings & Reranking:**
- **FastEmbed 0.7.4+** - Local embeddings
- **Cohere 5.5.1+** - Reranking service

**HTTP & Networking:**
- **httpx 0.25+** - Async HTTP client
- **requests 2.32+** - Synchronous HTTP client

**Observability:**
- **OpenInference Instrumentation 0.1.4+** - LLM tracing
- **Arize-OTel 0.7.0+** - OpenTelemetry + Arize AI

**Frontend:**
- **Axios 1.6.7** - HTTP client
- **@clerk/react 6.0.1** - Authentication UI components

**Backend Authentication:**
- **clerk-backend-api 4.0.0+** - Clerk authentication SDK

## Configuration

**Environment:**
- Environment file: `.env.example` (template)
- Key configurations required:
  - `GROQ_API_KEY` - Groq LLM API
  - `OPENROUTER_API_KEY` - OpenRouter API (fallback LLM)
  - `MONGODB_CONNECTION_STRING` - MongoDB connection
  - `CLERK_PUBLISHABLE_KEY` - Clerk frontend auth
  - `CLERK_SECRET_KEY` - Clerk backend auth
  - `QDRANT_HOST`, `QDRANT_PORT` - Qdrant vector DB
  - `OLLAMA_BASE_URL` - Local LLM endpoint
  - `COHERE_API_KEY` - Cohere reranking
  - `ARIZE_SPACE_ID`, `ARIZE_API_KEY`, `ARIZE_PROJECT_NAME` - Arize monitoring

**Frontend Build:**
- `frontend/vite.config.js` - Vite configuration
  - Dev server port: 3000
  - API proxy: `/api` → `http://localhost:8001`
- `frontend/tailwind.config.js` - Tailwind with custom primary color palette

**Python Workspace:**
- `pyproject.toml` - UV workspace root
- `memblocks_lib/pyproject.toml` - Core library
- `backend/pyproject.toml` - Backend API + CLI

## Platform Requirements

**Development:**
- Node.js 18+
- Python 3.11+
- Docker & Docker Compose (for Qdrant, Ollama)
- MongoDB (optional, can be local)

**Production:**
- FastAPI backend (uvicorn)
- React frontend (static build via Vite)
- MongoDB instance
- Qdrant vector database
- Multiple LLM providers (Groq, OpenRouter, Google Gemini, Ollama)

---

*Stack analysis: 2026-03-12*
