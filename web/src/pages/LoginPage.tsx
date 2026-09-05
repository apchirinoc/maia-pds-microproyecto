import { AuthSplitPanel } from '@/components/features/auth/AuthSplitPanel'
import { LoginForm } from '@/components/features/auth/LoginForm'

export function LoginPage() {
  return (
    <div className="grid min-h-[calc(100vh-3.5rem)] grid-cols-1 lg:grid-cols-2">
      <AuthSplitPanel />
      <div className="flex items-center justify-center p-6">
        <LoginForm />
      </div>
    </div>
  )
}
