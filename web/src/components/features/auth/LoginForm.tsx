import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { useI18n } from '@/i18n/I18nProvider'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export function LoginForm() {
  const { t } = useI18n()
  const { login, isAuthenticating, error } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      await login(username, password)
      navigate('/admin/models')
    } catch {
      // handled by useAuth error state
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full max-w-sm flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold">{t('auth.title')}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t('auth.subtitle')}</p>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="username">{t('auth.username')}</Label>
        <Input
          id="username"
          name="username"
          autoComplete="username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          placeholder={t('auth.username').toLowerCase()}
          required
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="password">{t('auth.password')}</Label>
        <Input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="••••••••"
          invalid={Boolean(error)}
          required
        />
      </div>

      {error && <p className="text-sm text-destructive">{t('auth.invalidCredentials')}</p>}

      <Button type="submit" disabled={isAuthenticating} className="mt-1">
        {isAuthenticating ? t('common.loading') : t('auth.submit')}
      </Button>

      <a href="#" className="text-center text-sm text-primary outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring">
        {t('auth.forgotPassword')}
      </a>

      <p className="mt-4 text-center text-xs text-muted-foreground">{t('auth.footer')}</p>
    </form>
  )
}
