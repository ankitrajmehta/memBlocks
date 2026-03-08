# MemBlocks Frontend

The MemBlocks frontend is a modern, responsive Single Page Application (SPA) built with **React** and **Vite**. It provides a sleek, dark-themed user interface for interacting with the MemBlocks backend and visualizing real-time memory analytics.

## Tech Stack
- **Framework**: React 18 + Vite
- **Styling**: TailwindCSS
- **Routing**: React Router DOM v6
- **Authentication**: Clerk `@clerk/react`

## Architecture Overview

The frontend code is structured inside `frontend/src/`:

1. **`api/client.js`**: The central Axios HTTP client configured to intercept requests and inject the Clerk JWT `Authorization` header automatically. Handles all communication with the FastAPI backend (CRUD on blocks, sending messages, fetching transparency stats, etc.).
2. **`components/`**: Reusable UI components.
    - **`ChatInterface.jsx`**: Manages the conversation UI. Automatically loads the active session from LocalStorage, tracks message states, pushing live semantic/core memory analytics up to the workspace, and handles safe session-switching and forced manual memory flushing (`/flush`) to ensure zero-context loss on new chats.
    - **`AnalyticsPanel.jsx`**: The dynamic right sidebar that listens for live prop updates from the parent component. Displays real-time estimated Token Usage, live Core Memory extractions (Persona and Human profiles), Rolling Summaries, and Pipeline Transparency Stats fetched straight from the backend.
    - **`BlockManager.jsx`**: The left sidebar containing the UI for listing, creating, selecting, and deleting Memory Blocks.
3. **`pages/`**: Primary route views.
    - **`Landing.jsx`**: The branded public entry point with background imagery and the Clerk Auth modal overlay.
    - **`Workspace.jsx`**: The authenticated application view that glues together the Block Manager, Chat Interface, and Analytics Panel.
4. **`App.jsx`**: The root routing logic that verifies the active user session and conditionally renders either the Landing or Workspace components.

## Core Concepts

### Persistent Sessions
The UI maps a specific `sessionId` to a `blockId` inside the browser's `localStorage`. This ensures that when a user refreshes the page, their exact context, chat history, rolling summary, and analytics are seamlessly re-fetched and restored without generating orphaned "abandoned" sessions in the database.

### State Drilling for Live Analytics
To ensure the UI is reactive, the `ChatInterface` captures the enriched response payload containing real-time processing stats (like the `memory_window_size` and freshly extracted `core_memory`) directly from the `/message` endpoint, emitting it up to `Workspace.jsx`, which passes it down to `AnalyticsPanel.jsx` to render instantly.

## Setup and Installation

### Prerequisites
- Node.js (v18+)
- A `VITE_CLERK_PUBLISHABLE_KEY` in `frontend/.env`
- Ensure the backend FastAPI server is running.

### Running the App locally

1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server (default port 5173):
   ```bash
   npm run dev
   ```
4. Access the application in your browser at: `http://localhost:5173`
