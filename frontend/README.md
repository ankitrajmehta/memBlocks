# memBlocks Frontend

Modern React frontend for **memBlocks** - an intelligent, modular memory management system for LLMs.

## 🚀 Features

- **Split-Screen Interface**: Chat panel on the left, control panel on the right
- **User Management**: Create and select users
- **Memory Block Management**: Create and manage memory blocks (cartridge-like memory contexts)
- **Real-time Chat**: Interactive chat interface with message history
- **Memory Viewer**: View core memory stored in blocks
- **Recursive Summary**: Display hierarchical memory summaries
- **Responsive Design**: Works on desktop and mobile devices
- **Modern Tech Stack**: React 18, Vite, Tailwind CSS, Axios

## 📋 Prerequisites

- **Node.js** 16+ (or npm/pnpm/yarn)
- **Backend API** running at `http://localhost:80001`
  - Make sure the memBlocks backend is running (see main project README)
  - Required services: MongoDB, Qdrant, Ollama

## 🛠️ Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
# or
pnpm install
# or
yarn install
```

## 🏃 Running the Application

### Development Mode

```bash
npm run dev
```

The application will start at `http://localhost:3000`

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## 🏗️ Project Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── client.js           # API client for backend communication
│   ├── components/
│   │   ├── ChatPanel.jsx       # Left panel - chat interface
│   │   ├── OptionsPanel.jsx    # Right panel - controls container
│   │   ├── UserSelector.jsx    # User selection/creation
│   │   ├── BlockSelector.jsx   # Block selection/creation
│   │   ├── MemoryViewer.jsx    # Core memory display modal
│   │   └── SummaryViewer.jsx   # Recursive summary modal
│   ├── styles/
│   │   └── App.css             # Global styles
│   ├── App.jsx                 # Main application component
│   └── main.jsx                # React entry point
├── public/                     # Static assets
├── index.html                  # HTML template
├── vite.config.js              # Vite configuration
├── tailwind.config.js          # Tailwind CSS configuration
├── postcss.config.js           # PostCSS configuration
└── package.json                # Dependencies and scripts
```

## 📡 API Integration

The frontend communicates with the backend via REST API:

- **Base URL**: `http://localhost:80001/api`
- **Proxy**: Vite dev server proxies `/api` requests to backend

### Available API Endpoints

**Users:**
- `POST /api/users` - Create user
- `GET /api/users` - List users
- `GET /api/users/{userId}` - Get user details

**Blocks:**
- `POST /api/blocks` - Create memory block
- `GET /api/blocks?user_id={userId}` - List user's blocks
- `GET /api/blocks/{blockId}` - Get block details
- `DELETE /api/blocks/{blockId}` - Delete block

**Chat:**
- `POST /api/chat/start` - Start chat session
- `POST /api/chat/message` - Send message
- `GET /api/chat/history/{sessionId}` - Get chat history

**Memory:**
- `GET /api/memory/{blockId}/core` - Get core memory
- `GET /api/memory/{blockId}/summary` - Get recursive summary
- `GET /api/memory/{blockId}/semantic` - Get semantic memories
- `POST /api/memory/search` - Search memories

## 🎨 UI Components

### ChatPanel
- Displays conversation history
- Message input with send button
- Auto-scrolls to latest message
- Shows current session info
- Disabled when no active session

### OptionsPanel
Contains:
- **UserSelector**: Dropdown + create new user form
- **BlockSelector**: Dropdown + create new block form
- **Action Buttons**: Start session, view memory, view summary
- **Status Display**: Shows current user, block, and session state

### MemoryViewer (Modal)
- Displays core memory for selected block
- Formatted display of memory contents
- Shows metadata if available

### SummaryViewer (Modal)
- Displays recursive summary
- Shows summary level and timestamp
- Formatted text display

## 🔧 Configuration

### Backend URL

To change the backend URL, edit `src/api/client.js`:

```javascript
const API_BASE_URL = 'http://your-backend-url:80001/api';
```

Or update the Vite proxy in `vite.config.js`:

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://your-backend-url:80001',
      changeOrigin: true,
    }
  }
}
```

### Port Configuration

Change dev server port in `vite.config.js`:

```javascript
server: {
  port: 3000, // Change to desired port
}
```

## 🎯 Usage Workflow

1. **Select/Create User**: Choose an existing user or create a new one
2. **Select/Create Block**: Choose a memory block or create a new one
3. **Start Session**: Click "Start Chat Session" to begin
4. **Chat**: Send messages and receive AI responses
5. **View Memory**: Click "View Core Memory" to see stored facts
6. **View Summary**: Click "View Recursive Summary" to see conversation summaries

## 🐛 Troubleshooting

### "Network error - please check backend is running"
- Ensure backend API is running at `http://localhost:80001`
- Check if MongoDB, Qdrant, and Ollama services are running
- Run `docker-compose up -d` in project root

### CORS Issues
- Backend should have CORS configured for `http://localhost:3000`
- Check backend `main.py` for CORS middleware settings

### Chat messages not appearing
- Check browser console for API errors
- Verify session was started successfully
- Check backend logs for errors

## 🚀 Technology Stack

- **React 18** - UI library
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **Axios** - HTTP client
- **Modern JavaScript** - ES6+ features

## 📦 Build Output

```bash
npm run build
```

Production build is output to `dist/` directory:
- Optimized and minified JavaScript
- CSS extracted and minified
- Assets copied and hashed

## 🤝 Contributing

This frontend is part of the memBlocks project. See main project README for contribution guidelines.

## 📄 License

Part of the memBlocks project.

---

**Need Help?** Check the main project documentation or backend API docs.
