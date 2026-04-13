import { Search, SlidersHorizontal, ArrowUpDown } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuCheckboxItem,
} from '@/components/ui/dropdown-menu'
import type { SortOption, FilterState, Tag } from '@/types'

const SORT_LABELS: Record<SortOption, string> = {
  'date-desc': 'Newest first',
  'date-asc': 'Oldest first',
  'alpha-asc': 'A → Z',
  'alpha-desc': 'Z → A',
}

interface BookmarkToolbarProps {
  search: string
  onSearchChange: (v: string) => void
  sort: SortOption
  onSortChange: (v: SortOption) => void
  filter: FilterState
  onFilterChange: (v: FilterState) => void
  availableTags?: Tag[]
  totalCount?: number
}

export default function BookmarkToolbar({
  search,
  onSearchChange,
  sort,
  onSortChange,
  filter,
  onFilterChange,
  availableTags = [],
  totalCount,
}: BookmarkToolbarProps) {
  const activeFilterCount = filter.tagIds.length + (filter.folderId ? 1 : 0)

  function toggleTag(tagId: string) {
    const newTagIds = filter.tagIds.includes(tagId)
      ? filter.tagIds.filter((t) => t !== tagId)
      : [...filter.tagIds, tagId]
    onFilterChange({ ...filter, tagIds: newTagIds })
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Search + controls row */}
      <div className="flex items-center gap-2">
        {/* Search input */}
        <div className="relative flex-1">
          <Search
            size={14}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
          />
          <Input
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search bookmarks…"
            className="h-9 border-border-subtle bg-bg-subtle pl-9 text-sm text-text-primary placeholder:text-text-muted focus-visible:border-brand/40"
          />
        </div>

        {/* Sort */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="h-9 gap-1.5 border-border-subtle bg-bg-subtle text-text-secondary hover:text-text-primary"
            >
              <ArrowUpDown size={13} />
              <span className="hidden sm:inline">{SORT_LABELS[sort]}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-44">
            <DropdownMenuLabel className="text-xs text-text-muted">Sort by</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuRadioGroup
              value={sort}
              onValueChange={(v) => onSortChange(v as SortOption)}
            >
              {(Object.keys(SORT_LABELS) as SortOption[]).map((key) => (
                <DropdownMenuRadioItem key={key} value={key} className="text-sm">
                  {SORT_LABELS[key]}
                </DropdownMenuRadioItem>
              ))}
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Filter */}
        {availableTags.length > 0 && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="relative h-9 gap-1.5 border-border-subtle bg-bg-subtle text-text-secondary hover:text-text-primary"
              >
                <SlidersHorizontal size={13} />
                <span className="hidden sm:inline">Filter</span>
                {activeFilterCount > 0 && (
                  <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-brand text-[9px] font-bold text-white">
                    {activeFilterCount}
                  </span>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuLabel className="text-xs text-text-muted">Filter by tag</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {availableTags.map((tag) => (
                <DropdownMenuCheckboxItem
                  key={tag.id}
                  checked={filter.tagIds.includes(tag.id)}
                  onCheckedChange={() => toggleTag(tag.id)}
                  className="text-sm"
                >
                  #{tag.name}
                  <span className="ml-auto text-xs text-text-muted">{tag.bookmarkCount}</span>
                </DropdownMenuCheckboxItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>

      {/* Active filters chips + count */}
      {(filter.tagIds.length > 0 || totalCount !== undefined) && (
        <div className="flex items-center gap-2">
          {filter.tagIds.length > 0 &&
            filter.tagIds.map((id) => {
              const tag = availableTags.find((t) => t.id === id)
              if (!tag) return null
              return (
                <button
                  key={id}
                  onClick={() => toggleTag(id)}
                  className="flex items-center gap-1 rounded-full bg-brand-light px-2.5 py-1 text-xs font-medium text-brand-mid transition-colors hover:bg-brand/20"
                >
                  #{tag.name}
                  <span className="text-brand-mid/60">×</span>
                </button>
              )
            })}

          {totalCount !== undefined && (
            <span className="ml-auto text-xs text-text-muted">
              {totalCount.toLocaleString()} bookmark{totalCount !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      )}
    </div>
  )
}
