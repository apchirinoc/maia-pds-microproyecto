import { Monitor, Moon, Sun } from 'lucide-react'
import { useI18n } from '@/i18n/I18nProvider'
import { useTheme } from '@/lib/theme/ThemeProvider'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'

export function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme()
  const { t } = useI18n()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label={t('theme.system')}>
          {resolvedTheme === 'dark' ? <Moon /> : <Sun />}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onSelect={() => setTheme('light')} data-state={theme === 'light' ? 'active' : undefined}>
          <Sun className="size-4" /> {t('theme.light')}
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => setTheme('dark')} data-state={theme === 'dark' ? 'active' : undefined}>
          <Moon className="size-4" /> {t('theme.dark')}
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => setTheme('system')} data-state={theme === 'system' ? 'active' : undefined}>
          <Monitor className="size-4" /> {t('theme.system')}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
