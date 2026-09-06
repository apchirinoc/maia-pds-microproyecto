import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { useState } from 'react'
import { TopNav } from '@/components/layout/TopNav'
import { Footer } from '@/components/layout/Footer'
import { TooltipProvider } from '@/components/ui/tooltip'
import { AuthProvider } from '@/hooks/useAuth'
import { I18nProvider } from '@/i18n/I18nProvider'
import { ThemeProvider } from '@/lib/theme/ThemeProvider'
import { AppRoutes } from './router'

export function App() {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 60_000, retry: 1, refetchOnWindowFocus: false },
        },
      }),
  )

  return (
    <ThemeProvider>
      <I18nProvider>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <TooltipProvider delayDuration={200}>
              <BrowserRouter>
                <div className="flex h-screen flex-col overflow-hidden">
                  <TopNav />
                  <main className="min-h-0 flex-1 overflow-y-auto">
                    <AppRoutes />
                  </main>
                  <Footer />
                </div>
              </BrowserRouter>
            </TooltipProvider>
          </AuthProvider>
        </QueryClientProvider>
      </I18nProvider>
    </ThemeProvider>
  )
}
