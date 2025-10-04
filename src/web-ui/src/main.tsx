import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider, createRouter, createRootRoute, createRoute, Outlet } from '@tanstack/react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { Toaster } from '@/components/ui/toaster'
import { ErrorBoundary } from 'react-error-boundary'
import '@/styles/globals.css'

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: (failureCount, error) => {
        // Don't retry on 4xx errors
        if (error && typeof error === 'object' && 'status' in error) {
          const status = error.status as number
          if (status >= 400 && status < 500) {
            return false
          }
        }
        return failureCount < 3
      },
    },
  },
})

// Error boundary fallback component
function ErrorFallback({ error, resetErrorBoundary }: { error: Error; resetErrorBoundary: () => void }) {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="max-w-md w-full text-center space-y-6">
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-foreground">Application Error</h1>
          <p className="text-muted-foreground">
            Something went wrong while loading the application.
          </p>
        </div>

        <details className="text-left p-4 bg-muted rounded-lg">
          <summary className="cursor-pointer font-medium text-foreground mb-2">
            Error Details
          </summary>
          <pre className="text-xs text-muted-foreground overflow-auto">
            {error.message}
          </pre>
        </details>

        <div className="space-y-3">
          <button
            onClick={resetErrorBoundary}
            className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            Try Again
          </button>
          <button
            onClick={() => window.location.reload()}
            className="w-full px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/90 transition-colors"
          >
            Reload Application
          </button>
        </div>
      </div>
    </div>
  )
}

// Root layout component
function RootLayout() {
  return (
    <div className="min-h-screen bg-background font-sans antialiased">
      <ErrorBoundary FallbackComponent={ErrorFallback}>
        <Outlet />
        <Toaster />
      </ErrorBoundary>
    </div>
  )
}

// Create root route
const rootRoute = createRootRoute({
  component: RootLayout,
})

// Create main route (placeholder for now)
const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: function Index() {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-6">
          <h1 className="text-4xl font-bold text-foreground">
            AI Disk Cleaner
          </h1>
          <p className="text-lg text-muted-foreground max-w-md mx-auto">
            Modern web interface is being set up. This is the Phase 1 project structure.
          </p>
          <div className="space-y-2 text-sm text-muted-foreground">
            <p>✅ Tauri 2.0 backend configured</p>
            <p>✅ React 18 + TypeScript setup</p>
            <p>✅ TailwindCSS v4 + shadcn/ui configured</p>
            <p>✅ Project structure established</p>
            <p>🔄 Ready for Phase 2 implementation</p>
          </div>
        </div>
      </div>
    )
  },
})

// Create router
const router = createRouter({
  routeTree: rootRoute.addChildren([indexRoute]),
  defaultPreload: 'intent',
})

// Hide splash screen and show app
function hideSplashScreen() {
  const splash = document.getElementById('splash')
  const root = document.getElementById('root')

  if (splash) {
    splash.style.opacity = '0'
    splash.style.transition = 'opacity 0.3s ease-out'

    setTimeout(() => {
      splash.style.display = 'none'
      if (root) {
        root.classList.remove('hidden')
      }
    }, 300)
  } else if (root) {
    root.classList.remove('hidden')
  }
}

// Render the application
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      {process.env.NODE_ENV === 'development' && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  </React.StrictMode>,
)

// Hide splash screen when React is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', hideSplashScreen)
} else {
  hideSplashScreen()
}

// Handle theme changes
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
  const theme = localStorage.getItem('ai-disk-cleaner-theme') || 'system'
  if (theme === 'system') {
    document.documentElement.classList.toggle('dark', e.matches)
  }
})