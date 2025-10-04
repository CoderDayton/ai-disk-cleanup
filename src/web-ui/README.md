# AI Disk Cleaner - Modern Web UI

A modern, cross-platform desktop application for intelligent file management powered by AI. Built with Tauri 2.0, React 18, TypeScript, and TailwindCSS v4.

## Features

- 🤖 **AI-Powered Analysis**: Intelligent file recommendations using OpenAI API
- 🎯 **Hybrid Architecture**: Native performance with modern web UI
- 🖥️ **Cross-Platform**: Windows, macOS, and Linux support
- ⚡ **High Performance**: Virtual scrolling for 100k+ files with sub-100ms response times
- 🔒 **Security First**: Local processing with privacy-first architecture
- 🎨 **Modern UI**: Beautiful, accessible interface with dark/light themes
- 📊 **Real-time Updates**: Live progress indicators via WebSocket

## Architecture

This is a **Phase 1 Project Structure Setup** that provides the foundation for the modern web UI. The architecture follows the SDD specifications:

- **Tauri 2.0 Backend**: Rust-based native runtime with security sandboxing
- **React 18 Frontend**: Modern UI with concurrent features and TypeScript
- **FastAPI Bridge**: Integration layer with existing Python CLI backend
- **TailwindCSS v4 + shadcn/ui**: Modern, accessible component library
- **Zustand**: Lightweight state management
- **React Query**: Server state synchronization and caching

## Project Structure

```
src/web-ui/
├── src/
│   ├── components/          # React components
│   │   ├── ui/             # shadcn/ui base components
│   │   ├── forms/          # Form components
│   │   ├── file-management/# File operation components
│   │   ├── ai-analysis/    # AI analysis components
│   │   ├── safety/         # Safety and trust components
│   │   └── layout/         # Layout components
│   ├── hooks/              # Custom React hooks
│   ├── stores/             # Zustand state management
│   ├── services/           # API and external services
│   ├── types/              # TypeScript type definitions
│   ├── utils/              # Utility functions
│   ├── styles/             # Styling configuration
│   └── main.tsx            # Application entry point
├── src-tauri/              # Tauri 2.0 native layer
│   ├── src/
│   │   ├── commands/       # Tauri command handlers
│   │   ├── utils/          # Utility modules
│   │   ├── main.rs         # Tauri application entry
│   │   └── lib.rs          # Rust library exports
│   ├── Cargo.toml          # Rust dependencies
│   └── tauri.conf.json     # Tauri configuration
├── public/                 # Static assets
├── package.json            # Node.js dependencies
├── vite.config.ts          # Vite build configuration
├── tailwind.config.js      # TailwindCSS configuration
└── tsconfig.json           # TypeScript configuration
```

## Getting Started

### Prerequisites

- **Node.js** >= 18.0.0
- **npm** >= 9.0.0
- **Rust** latest stable (for Tauri backend)
- **Tauri CLI**: `npm install -g @tauri-apps/cli`

### Installation

1. **Navigate to the web-ui directory:**
   ```bash
   cd src/web-ui
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

### Development

1. **Start the development server:**
   ```bash
   npm run dev
   ```

2. **Start Tauri development mode:**
   ```bash
   npm run tauri:dev
   ```

3. **Run type checking:**
   ```bash
   npm run type-check
   ```

### Building

1. **Build for web:**
   ```bash
   npm run build
   ```

2. **Build Tauri application:**
   ```bash
   npm run tauri:build
   ```

## Available Scripts

- `npm run dev` - Start Vite development server
- `npm run build` - Build for production
- `npm run tauri:dev` - Start Tauri development mode
- `npm run tauri:build` - Build Tauri application
- `npm run type-check` - Run TypeScript type checking
- `npm run lint` - Run ESLint
- `npm run format` - Format code with Prettier
- `npm run test` - Run tests with Vitest
- `npm run generate:types` - Generate TypeScript types from backend

## Configuration

### Environment Variables

Key environment variables (see `.env.example`):

- `VITE_API_URL` - FastAPI backend URL
- `VITE_WS_URL` - WebSocket URL for real-time updates
- `VITE_APP_NAME` - Application name
- `VITE_APP_VERSION` - Application version
- `TAURI_PRIVATE_KEY_PATH` - Tauri private key path
- `TAURI_PUBLIC_KEY_PATH` - Tauri public key path

### Tauri Configuration

The Tauri configuration is in `src-tauri/tauri.conf.json`:

- Security permissions and capabilities
- Window settings and dimensions
- Build configuration
- Plugin configurations

## Technology Stack

### Frontend
- **React 18** - UI framework with concurrent features
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool and dev server
- **TailwindCSS v4** - Utility-first CSS framework
- **shadcn/ui** - Modern component library
- **Zustand** - Lightweight state management
- **React Query** - Server state management
- **TanStack Router** - Type-safe routing

### Backend (Tauri)
- **Rust** - Systems programming language
- **Tauri 2.0** - Cross-platform desktop framework
- **Tokio** - Async runtime
- **Serde** - Serialization framework
- **Tracing** - Structured logging

### Development Tools
- **ESLint** - Code linting
- **Prettier** - Code formatting
- **Vitest** - Testing framework
- **TypeScript** - Static type checking

## Performance Features

- **Virtual Scrolling**: Efficient rendering of large file lists (100k+ files)
- **Lazy Loading**: Load content only when needed
- **Memory Management**: Efficient caching and cleanup
- **Debounced Operations**: Optimized search and filtering
- **WebSocket Updates**: Real-time progress without polling

## Security Features

- **Tauri Sandboxing**: Isolated web environment
- **Capability System**: Granular permission control
- **Input Validation**: Client and server-side validation
- **Path Safety**: Protection against directory traversal
- **Local Processing**: No file content transmitted externally

## Development Guidelines

### Code Style
- Use TypeScript strict mode
- Follow ESLint rules
- Use Prettier for formatting
- Write meaningful comments
- Use semantic HTML

### Component Architecture
- Functional components with hooks
- TypeScript for all props
- Atomic design principles
- Reusable UI components
- Proper error boundaries

### State Management
- Zustand for global state
- React Query for server state
- Local state for UI components
- Persistent settings with localStorage

## Next Steps

This is **Phase 1** - Project Structure Setup. The foundation is now ready for:

**Phase 2**: Core UI Components and Layout
**Phase 3**: File Management and Analysis Integration
**Phase 4**: AI Analysis Features
**Phase 5**: Safety and Security Features
**Phase 6**: Advanced Features and Polish

## Contributing

1. Follow the established code style and patterns
2. Add TypeScript types for all new components
3. Write tests for new features
4. Update documentation as needed
5. Ensure all linting and type checking passes

## License

This project is part of the AI Disk Cleaner application. See the main project LICENSE file for details.