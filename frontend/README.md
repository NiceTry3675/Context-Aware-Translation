# Context-Aware Translation - Frontend

## Overview

A modern web application for AI-powered literary translation of novels from English to Korean. Built with Next.js 15, TypeScript, and Material-UI, this frontend provides an intuitive interface for uploading documents, managing translations, and engaging with the community.

## Tech Stack

- **Framework**: Next.js 15.3.5 with App Router
- **Language**: TypeScript 5 (strict mode)
- **UI Libraries**: 
  - Material-UI v7 for components
  - Tailwind CSS v4 for utility styling
- **Authentication**: Clerk (Korean localization)
- **Analytics**: Vercel Analytics
- **Development**: Turbopack for faster builds

## Features

### 🔐 Authentication
- Clerk integration with Korean localization
- Protected routes via middleware
- User session management
- Role-based access control

### 📄 Translation Management
- **File Upload**: Support for TXT, DOCX, EPUB, PDF, and Markdown
- **Real-time Progress**: Live status updates with progress bars
- **Style Analysis**: AI-powered extraction of narrative style and character dialogue patterns
- **Glossary Management**: Automatic term extraction and translation consistency
- **Multiple AI Models**: Support for Google Gemini and OpenRouter models
- **Advanced Settings**:
  - Segment size configuration (up to 15,000 characters)
  - Validation toggle with sample rate control
  - Quick validation mode for faster checks
  - Post-edit processing for automatic corrections

### 🔍 Translation Validation & Post-Editing
- **Validation Reports**: Comprehensive analysis of translation quality
  - Critical issues detection
  - Missing/added content identification
  - Name consistency checking
  - Pass/fail status per segment
- **Post-Edit Logs**: Detailed tracking of automated corrections
  - Before/after comparisons
  - Issue resolution metrics
  - Change tracking

### 📊 Job Management
- Local storage persistence of job IDs
- Automatic status polling (3-second intervals)
- Batch job operations
- Download completed translations
- Delete unwanted jobs

### 👥 Community Features
- Discussion boards with categories
- Post creation and commenting
- User display names
- Admin announcements
- Content moderation

### 🎨 UI Components

#### Core Components
- `TranslationSidebar`: Detailed job view with validation/post-edit tabs
- `ValidationReportViewer`: Interactive validation results display
- `PostEditLogViewer`: Post-edit changes visualization
- `JobsTable`: Translation job management interface
- `ModelSelector`: AI model selection with provider switching

#### Layout Sections
- `HeroSection`: Landing page hero
- `FeatureSection`: Feature showcase
- `Footer`: Site footer with links
- `AnnouncementHandler`: System-wide announcements

## Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── (auth)/          # Authentication pages (sign-in/sign-up)
│   │   ├── community/       # Community features
│   │   ├── components/      # Reusable components
│   │   │   ├── jobs/       # Job-related components
│   │   │   ├── sections/   # Layout sections
│   │   │   └── translation/# Translation-specific components
│   │   ├── hooks/           # Custom React hooks
│   │   ├── types/           # TypeScript type definitions
│   │   ├── utils/           # Utility functions and API helpers
│   │   │   └── constants/  # Application constants
│   │   ├── layout.tsx       # Root layout with providers
│   │   └── page.tsx         # Main translation interface
│   └── theme.ts             # MUI theme configuration
├── public/                  # Static assets
├── middleware.ts            # Clerk authentication middleware
└── package.json            # Dependencies and scripts
```

## Getting Started

### Prerequisites
- Node.js 18+ 
- npm or yarn
- Backend API running on port 8000

### Installation

```bash
# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local
```

### Environment Variables

Create `.env.local` with:

```env
# Clerk Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_key
CLERK_SECRET_KEY=your_clerk_secret

# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# Optional: Vercel Analytics
VERCEL_ANALYTICS_ID=your_analytics_id
```

### Development

```bash
# Start development server with Turbopack
npm run dev

# The application will be available at http://localhost:3000
```

### Production Build

```bash
# Build for production
npm run build

# Start production server
npm run start
```

### Code Quality

```bash
# Run ESLint
npm run lint

# Type checking
npx tsc --noEmit
```

## Custom Hooks

### `useTranslationJobs`
Manages translation job state with localStorage persistence and automatic polling.

```typescript
const { jobs, addJob, deleteJob, refreshJobs, error } = useTranslationJobs({
  apiUrl: API_URL,
  pollInterval: 3000
});
```

### `useApiKey`
Handles API key and provider management with localStorage.

```typescript
const { apiKey, setApiKey, apiProvider, setApiProvider, selectedModel, setSelectedModel } = useApiKey();
```

## API Integration

The frontend communicates with the backend through REST APIs:

### Translation Endpoints
- `POST /uploadfile/` - Upload file and start translation
- `GET /api/v1/jobs/{id}` - Get job status
- `GET /api/v1/jobs/{id}/validation-report` - Get validation report
- `GET /api/v1/jobs/{id}/post-edit-log` - Get post-edit log
- `PUT /api/v1/jobs/{id}/validation` - Trigger validation
- `PUT /api/v1/jobs/{id}/post-edit` - Trigger post-editing

### Community Endpoints
- `GET/POST /posts/` - Manage community posts
- `GET/POST /comments/` - Handle comments
- `GET /categories/` - Retrieve post categories
- `POST /announcements/` - Admin announcements

## Styling

The application uses a hybrid styling approach:
- **Material-UI**: Component-level theming and styled components
- **Tailwind CSS v4**: Utility classes for rapid development
- **Custom Theme**: Defined in `src/theme.ts` for consistent branding

## Authentication Flow

1. User visits the application
2. Clerk middleware checks authentication status
3. Public routes (homepage) are accessible without auth
4. Protected routes redirect to sign-in
5. Authenticated users can access full features
6. User data synced with backend via webhooks

## State Management

The application uses React's built-in state management:
- **Local State**: Component-specific state with `useState`
- **LocalStorage**: Persistent storage for job IDs and API keys
- **Context**: Theme and authentication via providers
- **Custom Hooks**: Encapsulated business logic

## Performance Optimizations

- **Turbopack**: Fast development builds
- **Code Splitting**: Automatic with Next.js App Router
- **Lazy Loading**: Components loaded on demand
- **Polling Optimization**: Only active for processing jobs
- **Memoization**: Strategic use in expensive computations

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Deployment

The application is optimized for Vercel deployment:

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy to Vercel
vercel

# Or connect GitHub repo for automatic deployments
```

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Ensure backend is running on port 8000
   - Check NEXT_PUBLIC_API_URL in `.env.local`

2. **Authentication Errors**
   - Verify Clerk keys are correctly set
   - Check middleware configuration

3. **Translation Not Starting**
   - Confirm API key is provided
   - Check file format is supported
   - Verify backend connection

4. **TypeScript Errors**
   - Run `npx tsc --noEmit` to check types
   - Ensure all dependencies are installed

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

This project is part of the Context-Aware Translation system. See the main project README for license information.