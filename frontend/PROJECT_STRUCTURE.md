# Frontend Project Structure

## Overview
This is a React + TypeScript + Vite application for a LiveKit-powered AI voice assistant with banking integration.

## Directory Structure

```
frontend/
├── src/
│   ├── components/              # Shared/General components
│   │   ├── AudioVisualizer.tsx
│   │   ├── Chatlist.tsx
│   │   ├── Flashcard.tsx
│   │   ├── Header.tsx
│   │   ├── Visualizer.tsx
│   │   └── VoiceAssistant.tsx
│   │
│   ├── components2_bank/        # Banking-specific components
│   │   ├── banking/
│   │   │   ├── AgentCardUI.tsx
│   │   │   ├── BankingDashboardUI.tsx
│   │   │   └── VoiceAgentStyles.css
│   │   ├── AudioVisualizer.tsx
│   │   ├── Chatlist.tsx
│   │   ├── Flashcard.tsx
│   │   ├── Header.tsx
│   │   ├── Visualizer.tsx
│   │   └── VoiceAssistant.tsx
│   │
│   ├── hooks/                   # Custom React hooks
│   │   └── useChatTranscriptions.ts
│   │
│   ├── pages/                   # Page components (Routes)
│   │   ├── BankingPage.tsx
│   │   └── HomePage.tsx
│   │
│   ├── types/                   # TypeScript type definitions
│   │   └── agent.ts
│   │
│   ├── App.tsx                  # Main application component
│   ├── main.tsx                 # Application entry point
│   ├── index.css                # Global styles
│   └── sample.css               # Sample/additional styles
│
├── dist/                        # Production build output
├── node_modules/                # Dependencies
│
├── .dockerignore                # Docker ignore patterns
├── .env                         # Environment variables (local)
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore patterns
├── Dockerfile                   # Docker configuration
├── README.md                    # Project documentation
├── eslint.config.js             # ESLint configuration
├── index.html                   # HTML entry point
├── nginx.conf                   # Nginx configuration for deployment
├── package.json                 # NPM dependencies and scripts
├── package-lock.json            # NPM lock file
├── tsconfig.app.json            # TypeScript config for app
├── tsconfig.json                # TypeScript base config
├── tsconfig.node.json           # TypeScript config for Node
└── vite.config.ts               # Vite bundler configuration
```

## Key Directories

### `/src/components/`
General-purpose reusable components used across the application:
- **AudioVisualizer.tsx** - Visual representation of audio input
- **Chatlist.tsx** - Chat message list component
- **Flashcard.tsx** - Flashcard UI component
- **Header.tsx** - Application header
- **Visualizer.tsx** - General visualization component
- **VoiceAssistant.tsx** - Voice assistant interface

### `/src/components2_bank/`
Banking-specific component implementations (separate from general components):
- Contains duplicates of general components customized for banking context
- **banking/** subdirectory contains core banking UI components:
  - **AgentCardUI.tsx** - Voice agent card interface
  - **BankingDashboardUI.tsx** - Main banking dashboard
  - **VoiceAgentStyles.css** - Banking agent styles

> [!NOTE]
> This directory contains duplicate components from `/src/components/`. Consider consolidating these into a single shared component library with variant props.

### `/src/hooks/`
Custom React hooks for shared logic:
- **useChatTranscriptions.ts** - Hook for managing LiveKit chat transcriptions

### `/src/pages/`
Top-level page components mapped to routes:
- **HomePage.tsx** - Landing page with general voice assistant
- **BankingPage.tsx** - Banking dashboard page (`/bank` route)

### `/src/types/`
TypeScript type definitions and interfaces:
- **agent.ts** - Agent-related type definitions

## Configuration Files

| File | Purpose |
|------|---------|
| `vite.config.ts` | Vite build tool configuration |
| `tsconfig.*.json` | TypeScript compiler settings |
| `eslint.config.js` | Code linting rules |
| `package.json` | Project metadata, dependencies, scripts |
| `Dockerfile` | Container build instructions |
| `nginx.conf` | Production web server config |
| `.env` | Environment variables (not committed) |
| `.env.example` | Template for environment variables |

## Application Architecture

### Routing
- **/** - Home page with general voice assistant
- **/bank** - Banking dashboard with voice agent overlay

### Component Pattern
The application uses a route-based architecture where:
1. Pages are mounted based on routes
2. Voice assistants appear as overlays above persistent dashboards
3. Components are organized by feature domain (general vs. banking)

## Recommended Improvements

> [!TIP]
> Consider these structural improvements:

1. **Consolidate duplicate components** - Merge `components/` and `components2_bank/` into a unified component library
2. **Add feature-based organization** - Group related components, hooks, and types by feature
3. **Create a utils/ directory** - For shared utility functions
4. **Add services/ directory** - For API calls and external service integrations
5. **Add constants/ directory** - For application-wide constants and configurations
6. **Rename components2_bank** - Use a more descriptive name like `features/` or merge with `components/`

## Technology Stack

- **Framework:** React 18 with TypeScript
- **Build Tool:** Vite
- **Real-time Communication:** LiveKit
- **Styling:** CSS with modern features
- **Deployment:** Docker + Nginx
