import { useCallback, useEffect, useRef, useState } from 'react'
import { Activity, Atom, BookOpen, Cpu, Lightbulb, Radio, ShieldCheck } from 'lucide-react'

import type {
  ActiveWorkspaceView,
  AgentRole,
  Claim,
  LiveProgressEvent,
  OpenQuestion,
  ReviewStatus,
  Run,
  RunLimits,
  RunSpend,
  Source,
  SourceReview,
  ToastMessage,
} from './types.ts'

import { ToastContainer } from './components/Toast.tsx'
import './App.css'
import { ResearchInput, type RunConfig } from './components/ResearchInput.tsx'
import { AgentMeetingRoom } from './components/AgentMeetingRoom.tsx'
import { ResearchOutcome } from './components/ResearchOutcome.tsx'
import { SourceInspector } from './components/SourceInspector.tsx'
import { RoundTable } from './components/RoundTable.tsx'
import { EvidenceVault } from './components/EvidenceVault.tsx'
import { ObservabilityTrace } from './components/ObservabilityTrace.tsx'

const REVIEW_STORAGE_KEY = 'foresightforge.source-reviews'
const CLAIMS_STORAGE_KEY = 'foresightforge.claims'
const QUESTIONS_STORAGE_KEY = 'foresightforge.open-questions'
const REPLAY_INTERVAL_MS = 1050

type ServerModel = { provider: string; default_model?: string; base_url?: string }

function loadJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

function readRunIdFromPath(): string | null {
  const match = window.location.pathname.match(/^\/investigations\/([^/]+)\/?$/)
  return match ? decodeURIComponent(match[1]) : null
}

export default function App() {
  const [runs, setRuns] = useState<Run[]>([])
  const [selectedRun, setSelectedRun] = useState<Run | null>(null)
  const [activeView, setActiveView] = useState<ActiveWorkspaceView>('meeting')
  const [apiStatus, setApiStatus] = useState<'checking' | 'connected' | 'offline'>('checking')
  const [serverModel, setServerModel] = useState<ServerModel | null>(null)

  const [isCollecting, setIsCollecting] = useState(false)
  const [collectionDomain, setCollectionDomain] = useState('')
  const [collectionQuestion, setCollectionQuestion] = useState('')
  const [collectionEvents, setCollectionEvents] = useState<LiveProgressEvent[]>([])
  const [collectionMode, setCollectionMode] = useState<'problem' | 'topic'>('problem')
  const [collectionSpend, setCollectionSpend] = useState<RunSpend>({
    usd: 0,
    tokens: 0,
    calls: 0,
  })
  const [collectionLimits, setCollectionLimits] = useState<RunLimits>({
    depth: 'standard',
    max_usd: 5,
    max_debate_rounds: 2,
    max_panel_rounds: 3,
    max_wall_seconds: 3600,
    max_queries: 3,
    max_sources: 6,
  })
  const [collectionStage, setCollectionStage] = useState('intake')
  const [collectionRun, setCollectionRun] = useState<Run | null>(null)
  const [selectedProblemIds, setSelectedProblemIds] = useState<string[]>([])

  const [sourceReviews, setSourceReviews] = useState<Record<string, SourceReview>>(() => {
    const stored = loadJson<Record<string, SourceReview | string>>(REVIEW_STORAGE_KEY, {})
    const normalized: Record<string, SourceReview> = {}
    for (const [key, value] of Object.entries(stored)) {
      if (typeof value === 'string') {
        normalized[key] = { status: value as ReviewStatus, updatedAt: new Date().toISOString() }
      } else if (value && typeof value === 'object') {
        normalized[key] = value as SourceReview
      }
    }
    return normalized
  })
  const [claimsMap, setClaimsMap] = useState<Record<string, Claim[]>>(() =>
    loadJson<Record<string, Claim[]>>(CLAIMS_STORAGE_KEY, {})
  )
  const [questionsMap, setQuestionsMap] = useState<Record<string, OpenQuestion[]>>(() =>
    loadJson<Record<string, OpenQuestion[]>>(QUESTIONS_STORAGE_KEY, {})
  )

  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null)
  const [toasts, setToasts] = useState<ToastMessage[]>([])
  // The root path is the intake surface; an investigation path opens a run.
  const [startingNewRun, setStartingNewRun] = useState(() => readRunIdFromPath() === null)

  const [traceRunId, setTraceRunId] = useState<string | null>(() => readRunIdFromPath())
  const [replayIndex, setReplayIndex] = useState(-1)
  const [replayPlaying, setReplayPlaying] = useState(false)

  const sourceTriggerRef = useRef<HTMLButtonElement | null>(null)
  const replayTimerRef = useRef<number | null>(null)

  const showToast = useCallback(
    (title: string, detail?: string, type: 'success' | 'info' | 'warning' = 'success') => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
      setToasts((current) => [...current, { id, title, detail, type }])
      window.setTimeout(() => {
        setToasts((current) => current.filter((toast) => toast.id !== id))
      }, 4000)
    },
    []
  )

  const dismissToast = useCallback((id: string) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const refresh = useCallback(async () => {
    try {
      const [healthResponse, runsResponse] = await Promise.all([fetch('/api/health'), fetch('/api/runs')])
      if (!healthResponse.ok || !runsResponse.ok) throw new Error('API offline')
      const health = await healthResponse.json()
      const records: Run[] = await runsResponse.json()
      setApiStatus(health.graph === 'connected' ? 'connected' : 'offline')
      if (health.model) setServerModel(health.model as ServerModel)
      setRuns(records)
      setSelectedRun((current) =>
        current ? records.find((run) => run.id === current.id) ?? current : records[0] ?? null
      )
    } catch {
      setApiStatus('offline')
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    async function loadInitial() {
      try {
        const [healthResponse, runsResponse] = await Promise.all([fetch('/api/health'), fetch('/api/runs')])
        if (!healthResponse.ok || !runsResponse.ok) throw new Error('API offline')
        const health = await healthResponse.json()
        const records: Run[] = await runsResponse.json()
        if (cancelled) return
        setApiStatus(health.graph === 'connected' ? 'connected' : 'offline')
        if (health.model) setServerModel(health.model as ServerModel)
        setRuns(records)
        if (records.length > 0) setSelectedRun((current) => current ?? records[0])
      } catch {
        if (!cancelled) setApiStatus('offline')
      }
    }
    void loadInitial()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    localStorage.setItem(REVIEW_STORAGE_KEY, JSON.stringify(sourceReviews))
  }, [sourceReviews])

  useEffect(() => {
    localStorage.setItem(CLAIMS_STORAGE_KEY, JSON.stringify(claimsMap))
  }, [claimsMap])

  useEffect(() => {
    localStorage.setItem(QUESTIONS_STORAGE_KEY, JSON.stringify(questionsMap))
  }, [questionsMap])

  const traceRun = traceRunId
    ? runs.find((run) => run.id === traceRunId) ?? (selectedRun?.id === traceRunId ? selectedRun : null)
    : null
  // The intake form is the landing surface. It shows whenever no run is
  // explicitly open, so a saved run never hides the way to start a new one.
  const activeRun = startingNewRun ? null : (traceRun ?? selectedRun ?? runs[0] ?? null)
  const activeSources = activeRun?.sources ?? []
  const activeRunId = activeRun?.id ?? 'default'
  const currentRunClaims = claimsMap[activeRunId] ?? []
  const currentRunQuestions = questionsMap[activeRunId] ?? []
  const selectedSource = activeSources.find((source) => source.id === selectedSourceId) ?? null

  const openSource = useCallback((sourceId: string, trigger?: HTMLButtonElement) => {
    if (trigger) sourceTriggerRef.current = trigger
    setSelectedSourceId(sourceId)
  }, [])

  const closeSource = useCallback(() => {
    setSelectedSourceId(null)
    requestAnimationFrame(() => sourceTriggerRef.current?.focus())
  }, [])

  const updateSourceReview = useCallback(
    (sourceId: string, status: ReviewStatus | null, note?: string) => {
      setSourceReviews((current) => {
        const next = { ...current }
        if (status) {
          next[sourceId] = {
            status,
            note: note !== undefined ? note : current[sourceId]?.note,
            updatedAt: new Date().toISOString(),
          }
        } else {
          delete next[sourceId]
        }
        return next
      })
      showToast('Evidence Status Updated', `Source marked as ${status?.toUpperCase() ?? 'unreviewed'}`)
    },
    [showToast]
  )

  const handleSaveClaim = useCallback((claim: Claim) => {
    setClaimsMap((current) => {
      const existing = current[claim.runId] ?? []
      const index = existing.findIndex((item) => item.id === claim.id)
      const next =
        index >= 0
          ? existing.map((item) => (item.id === claim.id ? claim : item))
          : [...existing, claim]
      return { ...current, [claim.runId]: next }
    })
  }, [])

  const handleDeleteClaim = useCallback(
    (claimId: string) => {
      setClaimsMap((current) => {
        const existing = current[activeRunId] ?? []
        return { ...current, [activeRunId]: existing.filter((claim) => claim.id !== claimId) }
      })
      showToast('Claim Deleted', 'Removed from synthesized decision brief', 'info')
    },
    [activeRunId, showToast]
  )

  const handleSaveOpenQuestion = useCallback((question: OpenQuestion) => {
    setQuestionsMap((current) => {
      const existing = current[question.runId] ?? []
      return { ...current, [question.runId]: [...existing, question] }
    })
  }, [])

  const handleDeleteOpenQuestion = useCallback(
    (questionId: string) => {
      setQuestionsMap((current) => {
        const existing = current[activeRunId] ?? []
        return { ...current, [activeRunId]: existing.filter((question) => question.id !== questionId) }
      })
    },
    [activeRunId]
  )

  const handleCreateClaimFromSource = useCallback(
    (source: Source, passage?: string) => {
      const claim: Claim = {
        id: `claim-${Date.now()}`,
        runId: activeRunId,
        text: passage
          ? `Based on ${source.publisher || 'source'}: ${passage.slice(0, 140)}`
          : `Finding from ${source.title}`,
        status: 'supported',
        confidence: 'high',
        supportingSourceIds: [source.id],
        opposingSourceIds: [],
        quotedPassage: passage,
        author: 'Research Lead',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      }
      handleSaveClaim(claim)
      setSelectedSourceId(null)
      showToast('Claim Created', 'Evidence passage attached to the brief')
    },
    [activeRunId, handleSaveClaim, showToast]
  )

  const openInvestigation = useCallback((run: Run, view: ActiveWorkspaceView = 'outcome') => {
    window.history.pushState(
      { investigationId: run.id },
      '',
      `${window.location.origin}/investigations/${encodeURIComponent(run.id)}`
    )
    setStartingNewRun(false)
    setSelectedRun(run)
    setTraceRunId(run.id)
    setActiveView(view)
    setReplayIndex(-1)
    setReplayPlaying(false)
    window.scrollTo({ top: 0 })
  }, [])

  const closeInvestigation = useCallback(() => {
    window.history.pushState({}, '', `${window.location.origin}/`)
    setTraceRunId(null)
    setReplayIndex(-1)
    setReplayPlaying(false)
    window.scrollTo({ top: 0 })
  }, [])

  const startNewRun = useCallback(() => {
    window.history.pushState({}, '', `${window.location.origin}/`)
    setStartingNewRun(true)
    setTraceRunId(null)
    setSelectedRun(null)
    setActiveView('meeting')
    setReplayIndex(-1)
    setReplayPlaying(false)
    window.scrollTo({ top: 0 })
  }, [])

  const handleDispatchGoal = useCallback(
    async (domain: string, question: string, runConfig?: RunConfig) => {
      setIsCollecting(true)
      setStartingNewRun(false)
      setCollectionDomain(domain)
      setCollectionQuestion(question)
      setCollectionEvents([])
      setCollectionMode(runConfig?.mode === 'topic' ? 'topic' : 'problem')
      setCollectionStage('intake')
      setCollectionRun(null)
      setSelectedProblemIds([])
      setActiveView('meeting')
      window.scrollTo({ top: 0 })

      try {
        const response = await fetch('/api/runs/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            domain,
            question,
            model_provider: runConfig?.model_provider,
            model_name: runConfig?.model_name,
            api_key: runConfig?.api_key,
            mode: runConfig?.mode ?? 'auto',
            depth: runConfig?.depth ?? 'standard',
            max_usd: runConfig?.max_usd ?? 5,
          }),
        })

        if (!response.ok) {
          const payload = await response.json()
          throw new Error(payload.detail ?? 'Could not start the R&D investigation')
        }
        if (!response.body) throw new Error('Live streaming is unsupported in this browser')

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        let completedRun: Run | null = null

        const processFrame = (frame: string) => {
          const data = frame
            .split(/\r?\n/)
            .filter((line) => line.startsWith('data:'))
            .map((line) => line.slice(5).trim())
            .join('\n')
          if (!data) return
          const update = JSON.parse(data) as LiveProgressEvent
          setCollectionEvents((current) => [...current, update])

          if (update.stage) setCollectionStage(update.stage)
          if (update.spend) setCollectionSpend(update.spend)
          if (update.limits) {
            setCollectionLimits((current) => ({ ...current, ...update.limits }))
          }
          if (update.mode === 'topic') setCollectionMode('topic')
          if (update.candidates?.length) {
            setCollectionRun((current) => ({
              ...(current ?? ({ id: 'pending' } as Run)),
              problem_candidates: update.candidates,
            }))
          }
          if (update.type === 'run_completed' && update.run) {
            completedRun = update.run
            setCollectionRun(update.run)
          }
          if (update.type === 'run_failed') {
            throw new Error(update.detail ?? 'The council run failed')
          }
        }

        while (true) {
          const { value, done } = await reader.read()
          buffer += decoder.decode(value, { stream: !done })
          const frames = buffer.split(/\r?\n\r?\n/)
          buffer = frames.pop() ?? ''
          for (const frame of frames) processFrame(frame)
          if (done) break
        }
        if (buffer.trim()) processFrame(buffer)
        if (!completedRun) throw new Error('The server closed the progress stream before saving this run')

        const savedRun = completedRun as Run
        setRuns((current) => [savedRun, ...current.filter((run) => run.id !== savedRun.id)])
        setSelectedRun(savedRun)
        setTraceRunId(savedRun.id)
        window.history.pushState(
          { investigationId: savedRun.id },
          '',
          `${window.location.origin}/investigations/${encodeURIComponent(savedRun.id)}`
        )
        setActiveView('outcome')
        showToast(
          savedRun.status === 'awaiting_input'
            ? 'Problems Discovered — Your Call'
            : 'Council Delivered Outcome',
          `${savedRun.sources?.length ?? 0} sources retrieved · ${
            savedRun.core_architecture ? 'architecture deconstructed' : 'evidence collected'
          }`
        )
      } catch (error) {
        showToast(
          'Council Execution Alert',
          error instanceof Error ? error.message : 'The investigation was interrupted',
          'warning'
        )
      } finally {
        setIsCollecting(false)
      }
    },
    [showToast]
  )

  const handleSelectAgentWork = useCallback((role: AgentRole) => {
    if (role === 'research' || role === 'data') setActiveView('vault')
    else if (role === 'review' || role === 'synthesis') setActiveView('outcome')
    else setActiveView('observability')
  }, [])

  const handleAddPerspective = useCallback(
    (text: string) => {
      showToast('R&D Guidance Recorded', text.slice(0, 120), 'info')
    },
    [showToast]
  )

  const startReplay = useCallback(() => {
    setReplayIndex(0)
    setReplayPlaying(true)
  }, [])

  useEffect(() => {
    if (!replayPlaying) return
    const total = Math.max(1, activeRun?.audit?.length ?? 1)
    replayTimerRef.current = window.setInterval(() => {
      setReplayIndex((current) => {
        if (current + 1 >= total - 1) {
          setReplayPlaying(false)
          return Math.max(0, total - 1)
        }
        return current + 1
      })
    }, REPLAY_INTERVAL_MS)
    return () => {
      if (replayTimerRef.current !== null) window.clearInterval(replayTimerRef.current)
      replayTimerRef.current = null
    }
  }, [replayPlaying, activeRun?.audit?.length])

  useEffect(() => {
    const handlePopState = () => {
      const nextId = readRunIdFromPath()
      setTraceRunId(nextId)
      setStartingNewRun(nextId === null)
      setReplayIndex(-1)
      setReplayPlaying(false)
    }
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  return (
    <div className={`cyber-app-shell ${isCollecting ? 'cyber-app-shell--immersive' : ''}`}>
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      <header className="cyber-top-hud">
        <div className="hud-brand-zone">
          <a
            href="#meeting"
            className="hud-brand"
            onClick={(event) => {
              event.preventDefault()
              setActiveView('meeting')
            }}
          >
            <span className="brand-glow-orb">
              <Atom size={19} className="radar-glow-svg" />
            </span>
            <div className="brand-titles">
              <span className="brand-name">
                FORESIGHT<span className="brand-highlight">FORGE</span>
              </span>
              <span className="brand-badge-version">R&D COUNCIL</span>
            </div>
          </a>
        </div>

        <nav className="hud-view-nav" aria-label="Agent Workspaces">
          <button
            className={`hud-nav-tab ${activeView === 'meeting' ? 'active' : ''}`}
            onClick={() => setActiveView('meeting')}
          >
            <Radio size={15} />
            <span>Council Chamber</span>
            <span className="live-dot" style={{ width: 6, height: 6 }} />
          </button>
          <button
            className={`hud-nav-tab ${activeView === 'orchestrator' ? 'active' : ''}`}
            onClick={() => setActiveView('orchestrator')}
          >
            <Cpu size={15} />
            <span>Agent Matrix</span>
          </button>
          <button
            className={`hud-nav-tab ${activeView === 'outcome' ? 'active' : ''}`}
            onClick={() => setActiveView('outcome')}
          >
            <Lightbulb size={15} />
            <span>R&D Brief</span>
            <span className="tab-count-pill">{currentRunClaims.length}</span>
          </button>
          <button
            className={`hud-nav-tab ${activeView === 'vault' ? 'active' : ''}`}
            onClick={() => setActiveView('vault')}
          >
            <BookOpen size={15} />
            <span>Evidence Vault</span>
            <span className="tab-count-pill">{activeSources.length}</span>
          </button>
          <button
            className={`hud-nav-tab ${activeView === 'observability' ? 'active' : ''}`}
            onClick={() => setActiveView('observability')}
          >
            <Activity size={15} />
            <span>Observability</span>
          </button>
        </nav>

        <div className="hud-actions-zone">
          <button className="hud-new-run" onClick={startNewRun} title="Start a new investigation">
            <Atom size={14} />
            <span>New Run</span>
          </button>

          <div className="mission-dropdown-wrap">
            <span className="mission-label">MISSION:</span>
            <select
              className="cyber-mission-select"
              value={activeRun?.id ?? ''}
              onChange={(event) => {
                const target = runs.find((run) => run.id === event.target.value)
                if (target) openInvestigation(target, activeView)
              }}
            >
              {runs.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.domain} ({run.sources?.length ?? 0} sources)
                </option>
              ))}
            </select>
          </div>

          <div className={`hud-connection-status ${apiStatus}`}>
            <span className="status-blip" />
            <span className="status-label">
              {apiStatus === 'connected'
                ? 'COUNCIL ONLINE'
                : apiStatus === 'checking'
                  ? 'SYNCING'
                  : 'OFFLINE'}
            </span>
            <button className="icon-refresh" onClick={() => void refresh()} title="Sync system state">
              <ShieldCheck size={13} />
            </button>
          </div>
        </div>
      </header>

      <main className={`cyber-main-content ${isCollecting ? 'cyber-main-content--immersive' : ''}`}>
        {isCollecting ? (
          <RoundTable
            domain={collectionDomain}
            question={collectionQuestion}
            mode={collectionMode}
            events={collectionEvents}
            run={collectionRun}
            stage={collectionStage}
            spend={collectionSpend}
            limits={collectionLimits}
            selectedProblemIds={selectedProblemIds}
            onSelectProblem={(id) =>
              setSelectedProblemIds((current) =>
                current.includes(id) ? current.filter((item) => item !== id) : [...current, id]
              )
            }
            onNudge={(text) => showToast('Guidance Queued', text.slice(0, 140), 'info')}
            onPause={() => showToast('Pause Requested', 'The council will stop at the next stage', 'info')}
            onCancel={() => showToast('Cancel Requested', 'The council will stop after the current step', 'warning')}
          />
        ) : (
          <>
            {activeView === 'meeting' && activeRun && (
              <AgentMeetingRoom
                run={activeRun}
                sources={activeSources}
                onOpenSource={(id) => openSource(id)}
                onAddPerspective={handleAddPerspective}
                onNotify={showToast}
              />
            )}

            {activeView === 'orchestrator' && activeRun && (
              <>
                <AgentMeetingRoom
                  run={activeRun}
                  sources={activeSources}
                  onOpenSource={(id) => openSource(id)}
                  onAddPerspective={handleAddPerspective}
                  onNotify={showToast}
                />
                <div className="orchestrator-role-rail">
                  {(
                    [
                      ['orchestrator', 'Principal Investigator', 'Orchestration'],
                      ['research', 'Research Fellows', 'Evidence'],
                      ['data', 'Data Agent', 'Extraction'],
                      ['review', 'Prior Art Auditor', 'Citations'],
                      ['synthesis', 'Lead Researcher', 'Blueprint'],
                    ] as [AgentRole, string, string][]
                  ).map(([role, label, destination]) => (
                    <button
                      className="orchestrator-role-chip"
                      key={role}
                      onClick={() => handleSelectAgentWork(role)}
                    >
                      <strong>{label}</strong>
                      <small>{destination}</small>
                    </button>
                  ))}
                </div>
              </>
            )}

            {activeView === 'outcome' && activeRun && (
              <ResearchOutcome
                run={activeRun}
                sources={activeSources}
                claims={currentRunClaims}
                openQuestions={currentRunQuestions}
                onOpenSource={(id) => openSource(id)}
                onNewResearch={() => {
                  setActiveView('meeting')
                  startNewRun()
                }}
                onSaveClaim={handleSaveClaim}
                onDeleteClaim={handleDeleteClaim}
                onSaveOpenQuestion={handleSaveOpenQuestion}
                onDeleteOpenQuestion={handleDeleteOpenQuestion}
              />
            )}

            {activeView === 'vault' && (
              <EvidenceVault
                sources={activeSources}
                reviews={sourceReviews}
                onOpenSource={(id, trigger) => openSource(id, trigger)}
                onUpdateReview={updateSourceReview}
                onCreateClaimFromSource={(source) => handleCreateClaimFromSource(source)}
                onNotify={showToast}
              />
            )}

            {activeView === 'observability' && activeRun && (
              <ObservabilityTrace
                run={activeRun}
                sources={activeSources}
                replayIndex={replayIndex}
                replayPlaying={replayPlaying}
                onStartReplay={startReplay}
                onPauseReplay={() => setReplayPlaying(false)}
                onResetReplay={() => {
                  setReplayIndex(-1)
                  setReplayPlaying(false)
                }}
                onOpenSource={(id) => openSource(id)}
                onClose={closeInvestigation}
              />
            )}

            {!activeRun && (
              <ResearchInput
                serverModel={serverModel ?? undefined}
                onSubmit={handleDispatchGoal}
                pastRuns={runs.map((run) => ({
                  id: run.id,
                  domain: run.domain,
                  question: run.question,
                  status: run.status,
                  updated_at: run.updated_at,
                }))}
                onSelectRun={(runId) => {
                  const target = runs.find((run) => run.id === runId)
                  if (target) openInvestigation(target, 'outcome')
                }}
                isSubmitting={isCollecting}
              />
            )}
          </>
        )}
      </main>

      {selectedSource && (
        <SourceInspector
          source={selectedSource}
          review={sourceReviews[selectedSource.id]}
          onClose={closeSource}
          onUpdateReview={updateSourceReview}
          onCreateClaimFromSource={handleCreateClaimFromSource}
          onNotify={showToast}
        />
      )}
    </div>
  )
}
