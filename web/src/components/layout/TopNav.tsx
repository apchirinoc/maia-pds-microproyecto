import { Link } from 'react-router-dom'
import { Activity } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { useI18n } from '@/i18n/I18nProvider'
import { Button } from '@/components/ui/button'
import { ApiStatusIndicator } from './ApiStatusIndicator'
import { LanguageSwitcher } from './LanguageSwitcher'
import { ThemeToggle } from './ThemeToggle'
import { NavTab } from './NavTab'
import { AdminUserMenu } from './AdminUserMenu'

export function TopNav() {
  const { t } = useI18n()
  const { isAuthenticated } = useAuth()

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/75">
      <div className="mx-auto flex min-h-14 max-w-7xl flex-wrap items-center gap-2 px-4 py-2 sm:px-6 lg:gap-4">
        <Link to="/" className="flex items-center gap-2 font-semibold">
          <Activity className="size-5 text-primary" aria-hidden />
          <span>{t('common.appName')}</span>
        </Link>

        <nav className="order-last flex w-full flex-wrap items-center gap-1 lg:order-none lg:w-auto" aria-label="Primary">
          <NavTab to="/" end>
            {t('nav.panel')}
          </NavTab>
          <NavTab to="/analyze">{t('nav.analyze')}</NavTab>
          {isAuthenticated && (
            <>
              <NavTab to="/admin/models">{t('nav.models')}</NavTab>
              <NavTab to="/admin/history">{t('nav.history')}</NavTab>
            </>
          )}
        </nav>

        <div className="ml-auto flex max-w-full flex-wrap items-center justify-end gap-2">
          <LanguageSwitcher />
          <ApiStatusIndicator />
          <ThemeToggle />
          {isAuthenticated ? (
            <AdminUserMenu />
          ) : (
            <Button asChild size="sm">
              <Link to="/login">{t('nav.signIn')}</Link>
            </Button>
          )}
        </div>
      </div>
    </header>
  )
}
