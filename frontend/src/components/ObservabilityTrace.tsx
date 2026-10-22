import { useEffect, useMemo, useRef } from 'react'
import { Activity, ArrowLeft, BookOpen, ExternalLink, Pause, Play, RotateCcw, Search, ShieldCheck } from 'lucide-react'

import type { Run, Source } from '../types.ts'
import './RndControls.css'

type ObservabilityTraceProps = {
  run: Run
  sources: Source[]
  replayIndex: number
  replayPlaying: boolean
  onStartReplay: () => void
  onPauseReplay: () => void
  onResetReplay: () => void
  onOpenSource: (sourceId: string) => void
  onClose: () => void
}

type Beat = {
  id: string
  actor: string
  role: string
  title: string
  detail: string
  meta: string
  kind: 'question' | 'search' | 'source' | 'system' | 'gate'
  sourceId?: string
}

const STAGE_ORDER = [
  'plan',
  'deconstruct',
  'gather',
  'attack',
  'cross_examine',
  'refine_attempt',
  'cross-pollinate',
  'project',
  'synthesize',
  'cite',
  'verify',
]

const STAGE_LABELS: Record<string, string> = {
  plan: 'Planning',
  deconstruct: 'Deconstruction',
  gather: 'Evidence',
  attack: 'Stress Test',
  cross_examine: 'Cross-Examination',
  refine_attempt: 'Refinement',
  'cross-pollinate': 'Invention',
  project: 'Trajectory',
  synthesize: 'Synthesis',
  cite: 'Citations',
  verify: 'Judging',
}

export const ObservabilityTrace: React.FC<ObservabilityTraceProps> = ({
  run,
  sources,
  replayIndex,
  replayPlaying,
  onStartReplay,
  onPauseReplay,
  onResetReplay,
  onOpenSource,
  onClose,
}) => {
  const listRef = useRef<HTMLOListElement>(null)

  const beats = useMemo<Beat[]>(() => {
    const items: Beat[] = [
      {
        id: 'question',
        actor: 'Principal Investigator',
        role: 'Investigation Goal',
        title: 'Objective Dispatched',
        detail: run.question,
        meta: run.created_at ? new Date(run.created_at).toLocaleString() : 'Recorded input',
        kind: 'question',
      },
    ]

    const queries = [...new Set(sources.map((source) => source.query).filter(Boolean))]
    queries.forEach((query, index) => {
      const found = sources.filter((source) => source.query === query)
      items.push({
        id: `query-${index}`,
        actor: 'Search System',
        role: 'Public Web Search',
        title: `Search Path ${String(index + 1).padStart(2, '0')}`,
        detail: String(query),
        meta: `${found.length} page(s) retrieved`,
        kind: 'search',
      })
    })

    sources
      .slice()
      .sort((a, b) => (a.retrieved_at ?? '').localeCompare(b.retrieved_at ?? ''))
      .forEach((source, index) => {
        items.push({
          id: `source-${source.id}`,
          actor: source.content?.trim() ? 'Data Agent' : 'Search Index',
          role: source.content?.trim() ? 'Text Extracted' : 'Snippet Fallback',
          title: source.title,
          detail: source.excerpt || source.search_snippet || 'No readable text extracted.',
          meta: source.retrieved_at
            ? new Date(source.retrieved_at).toLocaleString()
            : `Source #${index + 1}`,
          kind: 'source',
          sourceId: source.id,
        })
      })

    ;(run.audit ?? [])
      .filter((event) => event.event !== 'awaiting_model_agent')
      .forEach((event, index) => {
        items.push({
          id: `audit-${index}-${event.stage}`,
          actor: event.stage === 'verify' ? 'Verification Gate' : 'Orchestrator',
          role: event.event.replaceAll('_', ' '),
          title: `${event.stage.replaceAll('-', ' ')} stage`,
          detail: event.detail,
          meta: 'Workflow record',
          kind: event.stage === 'verify' ? 'gate' : 'system',
        })
      })

    return items
  }, [run.question, run.created_at, run.audit, sources])

  useEffect(() => {
    if (replayIndex < 0) return
    const node = listRef.current?.children[replayIndex] as HTMLElement | undefined
    node?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [replayIndex])

  const stageStatus = useMemo(() => {
    const recorded = new Set((run.audit ?? []).map((event) => event.stage))
    return STAGE_ORDER.map((stage) => ({
      stage,
      label: STAGE_LABELS[stage] ?? stage,
      state: recorded.has(stage) ? 'recorded' : 'idle',
    }))
  }, [run.audit])

  const visibleCount = replayIndex < 0 ? beats.length : Math.min(beats.length, replayIndex + 1)

  return (
    <div className="trace-panel">
      <header className="trace-panel__topbar">
        <button className="trace-back" onClick={onClose}>
          <ArrowLeft size={14} /> All investigations
        </button>
        <div className="trace-panel__identity">
          <span className="trace-panel__id">RUN {run.id.slice(0, 8).toUpperCase()}</span>
          <h2>{run.domain}</h2>
          <p>“{run.question}”</p>
        </div>
        <div className="trace-panel__controls">
          <span className="trace-panel__counter">
            {replayIndex < 0 ? 'READY' : `${String(replayIndex + 1).padStart(2, '0')} / ${String(beats.length).padStart(2, '0')}`}
          </span>
          {replayPlaying ? (
            <button className="trace-btn" onClick={onPauseReplay}>
              <Pause size={14} /> Pause
            </button>
          ) : (
            <button className="trace-btn" onClick={onStartReplay} disabled={beats.length === 0}>
              <Play size={14} /> {replayIndex >= beats.length - 1 ? 'Replay again' : 'Replay path'}
            </button>
          )}
          {replayIndex >= 0 && (
            <button className="trace-btn trace-btn--ghost" onClick={onResetReplay} aria-label="Reset replay">
              <RotateCcw size={14} />
            </button>
          )}
        </div>
      </header>

      <div className="trace-stage-strip">
        {stageStatus.map((item) => (
          <div className={`trace-stage ${item.state}`} key={item.stage}>
            <span className="trace-stage__dot" />
            <span className="trace-stage__label">{item.label}</span>
            <span className="trace-stage__state">{item.state === 'recorded' ? 'RECORDED' : 'NO EVENT'}</span>
          </div>
        ))}
      </div>

      <ol className="trace-beats" ref={listRef}>
        {beats.map((beat, index) => {
          const visible = index < visibleCount
          const current = index === replayIndex
          return (
            <li
              className={`trace-beat ${beat.kind} ${visible ? 'visible' : 'hidden'} ${
                current ? 'current' : ''
              }`}
              key={beat.id}
            >
              <span className="trace-beat__node" aria-hidden="true">
                {beat.kind === 'source' ? (
                  <BookOpen size={13} />
                ) : beat.kind === 'search' ? (
                  <Search size={13} />
                ) : beat.kind === 'gate' ? (
                  <ShieldCheck size={13} />
                ) : (
                  <Activity size={13} />
                )}
              </span>
              <div className="trace-beat__body">
                <div className="trace-beat__byline">
                  <strong>{beat.actor}</strong>
                  <span>{beat.role}</span>
                  <small>{beat.meta}</small>
                </div>
                <h3>{beat.title}</h3>
                <p>{beat.detail}</p>
                {beat.sourceId && (
                  <button
                    className="trace-beat__inspect"
                    onClick={() => onOpenSource(beat.sourceId as string)}
                  >
                    Inspect source <ExternalLink size={12} />
                  </button>
                )}
              </div>
            </li>
          )
        })}
      </ol>

      <footer className="trace-panel__footer">
        <ShieldCheck size={13} />
        <span>
          Replay follows stored records only. It never invents agent dialogue, and stages with no
          model agent remain marked as having no event.
        </span>
      </footer>
    </div>
  )
}
