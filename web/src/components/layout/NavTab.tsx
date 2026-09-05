import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'

interface NavTabProps {
  to: string
  children: React.ReactNode
  end?: boolean
}

export function NavTab({ to, children, end }: NavTabProps) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          'rounded-md px-3 py-1.5 text-sm font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring',
          isActive
            ? 'bg-secondary text-secondary-foreground'
            : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
        )
      }
    >
      {children}
    </NavLink>
  )
}
