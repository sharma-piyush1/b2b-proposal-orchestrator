# Enterprise B2B Proposal Orchestrator

A stateful, multi-agent AI system designed to automate the extraction, research, and generation of enterprise B2B technical proposals from raw RFP (Request for Proposal) text. 

## 🏗️ Architecture

This project is built on a decoupled architecture featuring a modern web frontend and a containerized, agentic backend.

- **Frontend:** Next.js (App Router), Tailwind CSS, React Three Fiber (WebGL AI Avatar).
- **Backend:** FastAPI, LangGraph, Python.
- **LLM & Tooling:** Groq (Llama 3.3 70B), Tavily Search API.
- **State Management:** PostgreSQL (Supabase) via LangGraph Checkpointers.

## ✨ Key Features

- **Multi-Agent Pipeline:** Utilizes specialized LangGraph nodes (`Extractor`, `Researcher`, `Pricing`, `Critic`, `Writer`) to process complex RFPs.
- **Real-Time Market Research:** Agents autonomously query the web via Tavily to ground financial models in current market data.
- **Human-in-the-Loop (HITL):** Graph execution pauses securely for human validation of calculated pricing before drafting the final document.
- **Stateful Memory:** PostgreSQL connection pooling ensures thread-safe memory, allowing workflows to pause and resume without data loss.
- **Reactive UI:** Features a WebGL representation of the AI agent that responds dynamically to system state and text-to-speech outputs.

## 🚀 Quick Start (Local Development)

### Backend (Docker)
1. Navigate to the backend directory.
2. Create a `.env` file with your keys:
   ```text
   GROQ_API_KEY=your_key
   TAVILY_API_KEY=your_key
   DATABASE_URI=your_supabase_connection_string
3. Build and run the container:
```bash
docker build -t b2b-agent-backend .
docker run -p 8000:8000 --env-file .env b2b-agent-backend
```

## Frontend (Next.js)

1. Navigate to the frontend directory (b2b-proposal-ui).
2. Install dependencies: npm install
3. Create a .env.local file:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```
4. Start the dev server:
```bash
npm run dev
```
5. Open http://localhost:3000 in your browser.
