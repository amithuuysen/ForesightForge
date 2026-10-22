import { useMemo, useState } from 'react'
import { BookOpen, CalendarDays, Check, Clock3, ExternalLink, Filter, Search, X } from 'lucide-react'

import type { ReviewStatus, Source, SourceReview } from '../types.ts'
import './RndControls.css'

type EvidenceVaultProps = {
  sources: Source[]
  reviews: Record<string, SourceReview>
  onOpenSource: (sourceId: string, trigger?: HTMLButtonElement) => void
  onUpdateReview: (sourceId: string, status: ReviewStatus | null, note?: string) => void
  onCreateClaimFromSource: (source: Source) => void
  onNotify?: (title: string, detail?: string, type?: 'success' | 'info' | 'warning') => void
}

type StatusFilter = 'all' | 'needs-review' | 'reviewed' | 'disputed' | 'excluded'
type ExtractionFilter = 'all' | 'full-text' | 'snippet-only'
type DateFilter = 'all' | 'dated' | 'undated'
type SortOption = 'retrieved' | 'title' | 'publisher' | 'date'

export const EvidenceVault: React.FC<EvidenceVaultProps> = ({
  sources,
  reviews,
  onOpenSource,
  onUpdateReview,
  onCreateClaimFromSource,
}) => {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [extractionFilter, setExtractionFilter] = useState<ExtractionFilter>('all')
  const [dateFilter, setDateFilter] = useState<DateFilter>('all')
  const [sortBy, setSortBy] = useState<SortOption>('retrieved')
  const [query, setQuery] = useState('')

  const counts = useMemo(() => {
    const reviewed = sources.filter((source) => reviews[source.id]?.status === 'reviewed').length
    const excluded = sources.filter((source) => reviews[source.id]?.status === 'excluded').length
    const disputed = sources.filter((source) => reviews[source.id]?.status === 'disputed').length
    const fullText = sources.filter((source) => Boolean(source.content?.trim())).length
    return {
      reviewed,
      excluded,
      disputed,
      needsReview: sources.length - reviewed - excluded - disputed,
      fullText,
      snippetOnly: sources.length - fullText,
      dated: sources.filter((source) => Boolean(source.published_at)).length,
    }
  }, [sources, reviews])

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase()
    const result = sources.filter((source) => {
      const status = reviews[source.id]?.status
      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'needs-review' && !status) ||
        status === statusFilter
      const fullText = Boolean(source.content?.trim())
      const matchesExtraction =
        extractionFilter === 'all' ||
        (extractionFilter === 'full-text' && fullText) ||
        (extractionFilter === 'snippet-only' && !fullText)
      const matchesDate =
        dateFilter === 'all' ||
        (dateFilter === 'dated' && Boolean(source.published_at)) ||
        (dateFilter === 'undated' && !source.published_at)
      const matchesQuery =
        !needle ||
        [source.title, source.publisher, source.excerpt, source.query].some((value) =>
          value?.toLowerCase().includes(needle)
        )
      return matchesStatus && matchesExtraction && matchesDate && matchesQuery
    })

    return result.sort((first, second) => {
      if (sortBy === 'title') return first.title.localeCompare(second.title)
      if (sortBy === 'publisher') {
        return (first.publisher ?? '').localeCompare(second.publisher ?? '')
      }
      if (sortBy === 'date') {
        return (second.published_at ?? '').localeCompare(first.published_at ?? '')
      }
      return (second.retrieved_at ?? '').localeCompare(first.retrieved_at ?? '')
    })
  }, [sources, reviews, statusFilter, extractionFilter, dateFilter, sortBy, query])

  return (
    <div className="vault-panel">
      <header className="vault-header-row">
        <div>
          <span className="vault-eyebrow">CANDIDATE EVIDENCE</span>
          <h2>Evidence Vault</h2>
          <p>
            Retrieved pages, prior art, and benchmark sources reviewed before they enter a brief. A
            retrieved page is a candidate, not a supported claim.
          </p>
        </div>
        <div className="vault-stats-hud">
          <div className="hud-metric">
            <span className="hud-metric__value">{sources.length}</span>
            <span className="hud-metric__label">TOTAL SOURCES</span>
          </div>
          <div className="hud-metric hud-metric--good">
            <span className="hud-metric__value">{counts.fullText}</span>
            <span className="hud-metric__label">FULL TEXT</span>
          </div>
          <div className="hud-metric hud-metric--warn">
            <span className="hud-metric__value">{counts.snippetOnly}</span>
            <span className="hud-metric__label">SNIPPET ONLY</span>
          </div>
          <div className="hud-metric hud-metric--accent">
            <span className="hud-metric__value">{counts.reviewed}</span>
            <span className="hud-metric__label">REVIEWED</span>
          </div>
        </div>
      </header>

      <div className="vault-toolbar-cyber">
        <div className="vault-filters" role="group" aria-label="Filter sources">
          {(
            [
              ['all', `All ${sources.length}`],
              ['needs-review', `To review ${counts.needsReview}`],
              ['reviewed', `Reviewed ${counts.reviewed}`],
              ['disputed', `Disputed ${counts.disputed}`],
              ['excluded', `Excluded ${counts.excluded}`],
            ] as [StatusFilter, string][]
          ).map(([value, label]) => (
            <button
              key={value}
              className={`vault-filter ${statusFilter === value ? 'active' : ''}`}
              aria-pressed={statusFilter === value}
              onClick={() => setStatusFilter(value)}
            >
              {label}
            </button>
          ))}
        </div>

        <label className="cyber-search-box">
          <Search size={14} />
          <span className="sr-only">Search sources</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search title, publisher, query"
          />
        </label>

        <label className="vault-select-wrap">
          <Filter size={13} />
          <span className="sr-only">Extraction type</span>
          <select
            value={extractionFilter}
            onChange={(event) => setExtractionFilter(event.target.value as ExtractionFilter)}
          >
            <option value="all">All extraction</option>
            <option value="full-text">Full text only</option>
            <option value="snippet-only">Snippet only</option>
          </select>
        </label>

        <label className="vault-select-wrap">
          <CalendarDays size={13} />
          <span className="sr-only">Publication date</span>
          <select
            value={dateFilter}
            onChange={(event) => setDateFilter(event.target.value as DateFilter)}
          >
            <option value="all">Any date</option>
            <option value="dated">Dated</option>
            <option value="undated">Undated</option>
          </select>
        </label>

        <label className="vault-select-wrap">
          <span className="sr-only">Sort sources</span>
          <select value={sortBy} onChange={(event) => setSortBy(event.target.value as SortOption)}>
            <option value="retrieved">Recently retrieved</option>
            <option value="title">Title A–Z</option>
            <option value="publisher">Publisher A–Z</option>
            <option value="date">Publication date</option>
          </select>
        </label>
      </div>

      {filtered.length === 0 ? (
        <div className="vault-empty-state">
          <BookOpen size={22} />
          <strong>
            {sources.length === 0 ? 'No sources retrieved yet' : 'No sources match these filters'}
          </strong>
          <p>
            {sources.length === 0
              ? 'Run an investigation to collect prior art and benchmark evidence.'
              : 'Adjust the review status, extraction type, date filter, or search terms.'}
          </p>
          {sources.length > 0 && (
            <button
              className="text-button"
              onClick={() => {
                setStatusFilter('all')
                setExtractionFilter('all')
                setDateFilter('all')
                setQuery('')
              }}
            >
              Clear filters <X size={13} />
            </button>
          )}
        </div>
      ) : (
        <div className="vault-cards-grid">
          {filtered.map((source) => {
            const review = reviews[source.id]
            const fullText = Boolean(source.content?.trim())
            return (
              <article className={`cyber-source-card ${review?.status ?? 'unreviewed'}`} key={source.id}>
                <div className="cyber-source-card__top">
                  <span className="cyber-source-card__publisher">
                    {source.publisher || 'Publisher unavailable'}
                  </span>
                  <span className={fullText ? 'tag tag--good' : 'tag tag--warn'}>
                    {fullText ? 'FULL TEXT' : 'SNIPPET ONLY'}
                  </span>
                </div>

                <button
                  className="cyber-source-card__title"
                  onClick={(event) => onOpenSource(source.id, event.currentTarget)}
                >
                  {source.title}
                </button>

                <p className="cyber-source-card__excerpt">
                  {source.excerpt || source.search_snippet || 'No readable text was extracted.'}
                </p>

                <div className="cyber-source-card__meta">
                  {source.published_at ? (
                    <span>
                      <CalendarDays size={11} /> {source.published_at}
                    </span>
                  ) : (
                    <span className="muted">Date unavailable</span>
                  )}
                  {source.retrieved_at && (
                    <span>
                      <Clock3 size={11} /> {new Date(source.retrieved_at).toLocaleDateString()}
                    </span>
                  )}
                </div>

                {source.query && <p className="cyber-source-card__query">Found via: {source.query}</p>}

                <div className="cyber-source-card__actions">
                  <a
                    className="tag"
                    href={source.url}
                    target="_blank"
                    rel="noreferrer"
                    aria-label={`Open ${source.title} in a new tab`}
                  >
                    <ExternalLink size={11} /> Source
                  </a>
                  <button
                    className="tag"
                    onClick={() => onCreateClaimFromSource(source)}
                    disabled={!fullText}
                    title={
                      fullText
                        ? 'Create a claim from this source'
                        : 'Full page text is required to create a claim'
                    }
                  >
                    <Check size={11} /> Claim
                  </button>
                  <button
                    className={`tag ${review?.status === 'reviewed' ? 'tag--good' : ''}`}
                    onClick={() =>
                      onUpdateReview(
                        source.id,
                        review?.status === 'reviewed' ? null : 'reviewed'
                      )
                    }
                  >
                    <Check size={11} /> {review?.status === 'reviewed' ? 'Reviewed' : 'Review'}
                  </button>
                  <button
                    className={`tag ${review?.status === 'excluded' ? 'tag--warn' : ''}`}
                    onClick={() =>
                      onUpdateReview(
                        source.id,
                        review?.status === 'excluded' ? null : 'excluded'
                      )
                    }
                  >
                    <X size={11} /> Exclude
                  </button>
                </div>

                {review?.status === 'reviewed' && (
                  <span className="cyber-source-card__badge">Reviewed</span>
                )}
                {review?.status === 'excluded' && (
                  <span className="cyber-source-card__badge cyber-source-card__badge--warn">
                    Excluded
                  </span>
                )}
              </article>
            )
          })}
        </div>
      )}

      {filtered.length > 0 && (
        <div className="vault-footer">
          <span>
            Showing {filtered.length} of {sources.length} sources · {counts.dated} dated ·{' '}
            {counts.dated === 0 ? 'publication dates unknown' : 'publication dates known'}
          </span>
          <span>Review decisions are stored in this browser.</span>
        </div>
      )}
    </div>
  )
}
