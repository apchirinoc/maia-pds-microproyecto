import { ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from './button'

export interface PaginationProps {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
  previousLabel: string
  nextLabel: string
  className?: string
}

const SIBLING_COUNT = 1

function getVisiblePages(page: number, totalPages: number): (number | 'ellipsis')[] {
  const totalVisible = SIBLING_COUNT * 2 + 5
  if (totalPages <= totalVisible) {
    return Array.from({ length: totalPages }, (_, index) => index + 1)
  }

  const leftSibling = Math.max(page - SIBLING_COUNT, 2)
  const rightSibling = Math.min(page + SIBLING_COUNT, totalPages - 1)

  const pages: (number | 'ellipsis')[] = [1]
  pages.push(leftSibling > 2 ? 'ellipsis' : 2)
  for (let pageNumber = Math.max(leftSibling, 3); pageNumber <= Math.min(rightSibling, totalPages - 2); pageNumber += 1) {
    pages.push(pageNumber)
  }
  pages.push(rightSibling < totalPages - 1 ? 'ellipsis' : totalPages - 1)
  pages.push(totalPages)

  return Array.from(new Set(pages))
}

export function Pagination({
  page,
  totalPages,
  onPageChange,
  previousLabel,
  nextLabel,
  className,
}: PaginationProps) {
  const pages = getVisiblePages(page, totalPages)

  return (
    <nav
      aria-label="Pagination"
      className={cn('flex items-center justify-end gap-1', className)}
    >
      <Button
        variant="outline"
        size="sm"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
        aria-label={previousLabel}
      >
        <ChevronLeft />
        {previousLabel}
      </Button>
      <div className="flex items-center gap-1 px-1">
        {pages.map((pageNumber, index) =>
          pageNumber === 'ellipsis' ? (
            <span
              key={`ellipsis-${index}`}
              aria-hidden
              className="inline-flex size-8 items-center justify-center text-sm text-muted-foreground"
            >
              …
            </span>
          ) : (
            <button
              key={pageNumber}
              type="button"
              onClick={() => onPageChange(pageNumber)}
              aria-current={pageNumber === page ? 'page' : undefined}
              className={cn(
                'inline-flex size-8 items-center justify-center rounded-md text-sm font-medium transition-colors',
                'outline-none focus-visible:ring-2 focus-visible:ring-ring',
                pageNumber === page
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
              )}
            >
              {pageNumber}
            </button>
          ),
        )}
      </div>
      <Button
        variant="outline"
        size="sm"
        disabled={page >= totalPages}
        onClick={() => onPageChange(page + 1)}
        aria-label={nextLabel}
      >
        {nextLabel}
        <ChevronRight />
      </Button>
    </nav>
  )
}
