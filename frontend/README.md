# Chat UI - React Implementation

This is a modern React + Vite reimplementation of the original vanilla JavaScript Chat UI application.

## Features

- **Modern React Architecture**: Built with React 19, using hooks and context for state management
- **Real-time Communication**: WebSocket connection for real-time chat functionality
- **Responsive Design**: Tailwind CSS for modern, responsive styling
- **Tool Management**: Interactive tool selection and management
- **RAG Integration**: Data source selection and RAG-only mode
- **Agent Mode**: Multi-step reasoning with progress tracking
- **Canvas Support**: Dynamic canvas content rendering
- **Markdown Support**: Full markdown rendering with syntax highlighting
- **LocalStorage**: Persistent tool selections

## Architecture

### Context Providers
- **WSContext**: Manages WebSocket connection and message handling
- **ChatContext**: Manages application state, chat messages, and configurations

### Components
- **App**: Main application container
- **Header**: Top navigation with model selection and controls
- **ChatArea**: Main chat interface with message display and input
- **Message**: Individual message component with markdown rendering
- **WelcomeScreen**: Initial welcome screen
- **ToolsPanel**: Tool selection and management
- **RagPanel**: Data source selection
- **CanvasPanel**: Canvas content display
- **AgentModal**: Agent mode configuration

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Technologies Used

- **React 19**: Modern React with hooks
- **Vite**: Fast build tool and dev server
- **Tailwind CSS**: Utility-first CSS framework
- **Lucide React**: Modern icon library
- **Marked**: Markdown parser
- **DOMPurify**: HTML sanitization
- **WebSocket API**: Real-time communication

## API Compatibility

This React implementation maintains full API compatibility with the original backend:

- `/api/config` - Configuration endpoint
- `/ws` - WebSocket endpoint for real-time communication
- All message types and payloads remain identical