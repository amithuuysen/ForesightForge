import React, { useEffect, useRef, useState } from 'react'
import {
  AlertCircle,
  CalendarDays,
  Check,
  CircleX,
  Clock3,
  Copy,
  ExternalLink,
  MessageSquare,
  Quote,
  ShieldAlert,
  Sparkles,
  X,
} from 'lucide-react'
import type { ReviewStatus, Source, SourceReview } from '../types.ts'

type SourceInspectorProps = {
  source: Source
  review?: SourceReview
  onClose: () => void
  onUpdateReview: (sourceId: string, status: ReviewStatus | null, note?: string) => void
  onCreateClaimFromSource: (source: Source, passage?: string) => void
  onNotify: (title: string, detail?: string) => void
}

export const SourceInspector: React.FC<SourceInspectorProps> = ({
  source,
  review,
  onClose,
  onUpdateReview,
  onCreateClaimFromSource,
  onNotify,
}) => {
  const dialogRef = useRef<HTMLElement>(null)
  const [selectedText, setSelectedText] = useState('')
  const [noteText, setNoteText] = useState(review?.note ?? '')
  const [isEditingNote, setIsEditingNote] = useState(Boolean(review?.note))
  const isFullText = Boolean(source.content?.trim())
  const textContent = source.content?.trim() || source.search_snippet || source.excerpt || 'No readable text was returned for this page.'

  const [prevNote, setPrevNote] = useState(review?.note)
  if (review?.note !== prevNote) {
    setPrevNote(review?.note)
    setNoteText(review?.note ?? '')
  }

  useEffect(() => {
    dialogRef.current?.focus()
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
      if (event.key === 'Tab') {
        const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(
          'button, a[href], input, textarea, [tabindex]:not([tabindex="-1"])'
        )
        if (!focusable?.length) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first.focus()
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  function handleMouseUp() {
    const selection = window.getSelection()?.toString().trim()
    if (selection && selection.length > 10) {
      setSelectedText(selection)
    } else {
      setSelectedText('')
    }
  }

  function copyCitation() {
    const pub = source.publisher ? ` — ${source.publisher}` : ''
    const date = source.published_at ? ` (${source.published_at})` : ' (n.d.)'
    const ret = source.retrieved_at ? `. Retrieved ${new Date(source.retrieved_at).toLocaleDateString()}` : ''
    const citation = `[${source.title}](${source.url})${pub}${date}${ret}.`
    void navigator.clipboard.writeText(citation)
    onNotify('Citation copied', 'Markdown citation copied to clipboard')
  }

  function copyPassage(textToCopy: string) {
    void navigator.clipboard.writeText(textToCopy)
    onNotify('Passage copied', 'Excerpt copied to clipboard')
  }

  function saveNote() {
    onUpdateReview(source.id, review?.status ?? 'reviewed', noteText.trim())
    onNotify('Analyst note saved', 'Assessment recorded for this source')
  }

  return (
    <div
      className="source-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <section
        className="source-inspector"
        role="dialog"
        aria-modal="true"
        aria-labelledby="inspector-title"
        tabIndex={-1}
        ref={dialogRef}
      >
        <div className="inspector-topline">
          <div className="inspector-topline-left">
            <span className="eyebrow">SOURCE INSPECTOR</span>
            <span className={`review-badge-inline ${review?.status ?? 'needs-review'}`}>
              {review?.status === 'reviewed' ? 'REVIEWED' : review?.status === 'disputed' ? 'DISPUTED' : review?.status === 'excluded' ? 'EXCLUDED' : 'NEEDS REVIEW'}
            </span>
          </div>
          <button className="icon-button" aria-label="Close source details" onClick={onClose}>
            <X size={19} />
          </button>
        </div>

        <div className="inspector-scroll" onMouseUp={handleMouseUp}>
          <div className="inspector-tags-row">
            <span className={isFullText ? 'extraction-tag extracted' : 'extraction-tag snippet'}>
              {isFullText ? 'PAGE TEXT EXTRACTED (TRAFILATURA)' : 'SEARCH SNIPPET ONLY (FALLBACK)'}
            </span>
            {source.published_at ? (
              <span className="meta-tag date">
                <CalendarDays size={12} /> Published {source.published_at}
              </span>
            ) : (
              <span className="meta-tag unknown-date">
                <CalendarDays size={12} /> Unknown publication date
              </span>
            )}
          </div>

          <h2 id="inspector-title">{source.title}</h2>

          <div className="inspector-meta">
            <span><strong>Publisher:</strong> {source.publisher || 'Unavailable'}</span>
            <span className="crumb-dot" />
            <span>
              <Clock3 size={12} /> Retrieved {source.retrieved_at ? new Date(source.retrieved_at).toLocaleString() : 'date unavailable'}
            </span>
          </div>

          <div className="inspector-links-row">
            <a className="original-link" href={source.url} target="_blank" rel="noreferrer">
              Open original source <ExternalLink size={13} />
            </a>
            <button className="action-pill-button" onClick={copyCitation} title="Copy markdown citation">
              <Copy size={13} /> Copy citation
            </button>
            <button
              className="action-pill-button primary"
              onClick={() => onCreateClaimFromSource(source, selectedText || undefined)}
              title="Formulate a claim using this source"
            >
              <Sparkles size={13} /> Turn into claim
            </button>
          </div>

          {source.query && (
            <div className="inspector-query">
              <span className="section-label">ORIGINATING SEARCH QUERY</span>
              <p>“{source.query}”</p>
            </div>
          )}

          {selectedText && (
            <div className="floating-selection-banner">
              <Quote size={14} />
              <div className="selection-copy">
                <span>Selected {selectedText.length} characters</span>
                <p>“{selectedText.length > 90 ? `${selectedText.slice(0, 90)}…` : selectedText}”</p>
              </div>
              <div className="selection-actions">
                <button
                  className="selection-btn quote"
                  onClick={() => onCreateClaimFromSource(source, selectedText)}
                >
                  <Sparkles size={12} /> Quote in claim
                </button>
                <button
                  className="selection-btn copy"
                  onClick={() => copyPassage(selectedText)}
                >
                  <Copy size={12} /> Copy quote
                </button>
              </div>
            </div>
          )}

          <div className="inspector-content">
            <div className="inspector-content-header">
              <span className="section-label">
                {isFullText ? 'RETRIEVED ARTICLE CONTENT' : 'SEARCH RESULT SNIPPET'}
              </span>
              <span className="char-count">{textContent.length.toLocaleString()} characters</span>
            </div>
            <div className="inspector-text-surface">
              <p>{textContent}</p>
            </div>
          </div>

          <div className="inspector-analyst-notes">
            <div className="notes-header">
              <span className="section-label">
                <MessageSquare size={13} /> ANALYST ASSESSMENT & NOTES
              </span>
              {!isEditingNote && (
                <button className="text-button" onClick={() => setIsEditingNote(true)}>
                  {noteText ? 'Edit note' : '+ Add note'}
                </button>
              )}
            </div>
            {isEditingNote ? (
              <div className="notes-edit-block">
                <textarea
                  rows={3}
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                  placeholder="Record your assessment: key takeaway, methodological limitations, contradictory data, or why this source is kept/excluded…"
                />
                <div className="notes-actions">
                  <button className="primary-button small" onClick={saveNote}>
                    Save note
                  </button>
                  <button className="text-button" onClick={() => setIsEditingNote(false)}>
                    Cancel
                  </button>
                </div>
              </div>
            ) : noteText ? (
              <div className="note-display">
                <p>{noteText}</p>
                {review?.updatedAt && (
                  <small>Recorded {new Date(review.updatedAt).toLocaleTimeString()}</small>
                )}
              </div>
            ) : (
              <p className="empty-note-hint">
                No analyst notes recorded yet. Add notes to explain why this source supports or contradicts your brief.
              </p>
            )}
          </div>

          <div className="inspector-warning">
            <AlertCircle size={15} />
            <p>
              <strong>Candidate evidence:</strong> Retrieved text is not a verified conclusion. Inspect the publisher’s context, verify date accuracy, and ensure claims cite specific passages before incorporating into a decision brief.
            </p>
          </div>
        </div>

        <div className="inspector-actions">
          <div className="inspector-review-controls">
            <span className="controls-label">STATUS DECISION:</span>
            <button
              className={`review-action-btn reviewed ${review?.status === 'reviewed' ? 'active' : ''}`}
              onClick={() => onUpdateReview(source.id, 'reviewed', noteText)}
            >
              <Check size={14} /> Mark Reviewed
            </button>
            <button
              className={`review-action-btn disputed ${review?.status === 'disputed' ? 'active' : ''}`}
              onClick={() => onUpdateReview(source.id, 'disputed', noteText)}
              title="Flag contradictory or questionable evidence"
            >
              <ShieldAlert size={14} /> Flag Disputed
            </button>
            <button
              className={`review-action-btn excluded ${review?.status === 'excluded' ? 'active' : ''}`}
              onClick={() => onUpdateReview(source.id, 'excluded', noteText)}
            >
              <CircleX size={14} /> Exclude
            </button>
            {review && (
              <button
                className="review-action-btn reset"
                onClick={() => onUpdateReview(source.id, null)}
                title="Reset back to needs review"
              >
                Reset
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}
