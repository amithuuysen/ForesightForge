import React, { useEffect, useState, type FormEvent } from 'react'
import {
  Send,
  FileText,
  Radio,
  Layers,
  Sparkles,
  Lightbulb,
  Cpu,
} from 'lucide-react'
import type { Run, Source } from '../types.ts'
import './AgentMeetingRoom.css'

type AgentMeetingRoomProps = {
  run: Run
  sources: Source[]
  onOpenSource?: (sourceId: string) => void
  onAddPerspective?: (text: string) => void
  onNotify?: (title: string, detail?: string, type?: 'success' | 'info' | 'warning') => void
}

type FellowConfig = {
  id: string
  name: string
  role: string
  color: string
  initials: string
  department: string
}

const FELLOWS: FellowConfig[] = [
  {
    id: 'lead',
    name: 'Principal Investigator',
    role: 'R&D Lead & Architectural Synthesis',
    department: 'Systems Architecture',
    color: '#3B82F6',
    initials: 'PI',
  },
  {
    id: 'subagent-1',
    name: 'Architecture & Diagnostics',
    role: 'System Flaws & Bottlenecks',
    department: 'Root-Cause Engineering',
    color: '#10B981',
    initials: 'AD',
  },
  {
    id: 'subagent-2',
    name: 'Cross-Domain Invention Fellow',
    role: 'Invention & Paradigm Transfer',
    department: 'Interdisciplinary Innovation',
    color: '#F59E0B',
    initials: 'CD',
  },
  {
    id: 'subagent-3',
    name: 'Adversarial Red-Team',
    role: 'Stress-Testing & Failure Modes',
    department: 'Reliability & Limits',
    color: '#EF4444',
    initials: 'RT',
  },
  {
    id: 'citation',
    name: 'Prior Art & Patent Auditor',
    role: 'Primary Sources & Evidence',
    department: 'Literature & Verification',
    color: '#8B5CF6',
    initials: 'PA',
  },
  {
    id: 'judge',
    name: 'Scientific Rigour Judge',
    role: 'Engineering Feasibility & Rubric',
    department: 'Governance & Standards',
    color: '#EC4899',
    initials: 'SJ',
  },
]

export const AgentMeetingRoom: React.FC<AgentMeetingRoomProps> = ({
  run,
  sources,
  onOpenSource,
  onAddPerspective,
  onNotify,
}) => {
  const [secondsElapsed, setSecondsElapsed] = useState(0)
  const [userPerspective, setUserPerspective] = useState('')
  const [selectedIdeaIdx, setSelectedIdeaIdx] = useState(0)

  const brainstormedIdeas = run.brainstormed_ideas || run.forecast?.brainstormed_ideas || []
  const activeIdea = brainstormedIdeas.length > 0 ? brainstormedIdeas[Math.min(selectedIdeaIdx, brainstormedIdeas.length - 1)] : null

  useEffect(() => {
    const timer = setInterval(() => {
      setSecondsElapsed((prev) => prev + 1)
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  const formatTimer = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60)
    const secs = totalSeconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const currentStage = run.active_speaker?.stage || run.current_stage || 'plan'

  const getActiveFellowId = (): string => {
    switch (currentStage) {
      case 'plan':
      case 'project':
      case 'synthesize':
        return 'lead'
      case 'deconstruct':
        return 'subagent-1'
      case 'gather':
        return 'subagent-1'
      case 'attack':
        return 'subagent-3'
      case 'cross_examine':
        return 'subagent-3'
      case 'refine_attempt':
        return 'subagent-3'
      case 'cross-pollinate':
        return 'subagent-2'
      case 'cite':
        return 'citation'
      case 'verify':
        return 'judge'
      default:
        return 'lead'
    }
  }

  const activeFellowId = run.active_speaker?.id || getActiveFellowId()
  const activeFellow = FELLOWS.find((f) => f.id === activeFellowId) || FELLOWS[0]
  const otherFellows = FELLOWS.filter((f) => f.id !== activeFellowId)

  const getFellowStatus = (fellowId: string): 'speaking' | 'analyzing' | 'done' | 'waiting' => {
    if (fellowId === activeFellowId) return 'speaking'
    const order = ['lead', 'subagent-1', 'subagent-2', 'subagent-3', 'citation', 'judge']
    const activeIdx = order.indexOf(activeFellowId)
    const fellowIdx = order.indexOf(fellowId)
    if (fellowIdx < activeIdx) return 'done'
    if (fellowIdx === activeIdx) return 'speaking'
    if (fellowIdx === activeIdx + 1) return 'analyzing'
    return 'waiting'
  }

  // Live thinking / speech derivation
  const getActiveSpeech = (): string => {
    if (run.active_speaker?.speech) {
      return run.active_speaker.speech
    }

    if (run.audit && run.audit.length > 0) {
      const recent = run.audit[run.audit.length - 1]
      if (recent.detail) return recent.detail
    }

    if (run.subagent_executions && run.subagent_executions.length > 0) {
      const matched = run.subagent_executions.find((e) => e.subagent_id === activeFellowId)
      if (matched?.key_findings && matched.key_findings.length > 0) {
        return matched.key_findings[0]
      }
      if (matched?.thinking_trace && matched.thinking_trace.length > 0) {
        const step = matched.thinking_trace[matched.thinking_trace.length - 1]
        return step.scratchpad || step.decision
      }
    }

    return `Deliberating on ${run.domain} system bottlenecks and cross-domain solution transfers...`
  }

  const formatStageLabel = (stage: string) => {
    switch (stage) {
      case 'plan':
        return 'Diagnosing Flaws & Objectives'
      case 'deconstruct':
        return 'Base Core Architecture Deconstruction'
      case 'gather':
        return 'Extracting Prior Art & Baselines'
      case 'attack':
        return 'Adversarial Stress-Testing'
      case 'cross_examine':
        return 'Council Cross-Examination'
      case 'refine_attempt':
        return `Refining Attempt ${run.attempt || 2}`
      case 'cross-pollinate':
        return 'Cross-Pollinating Inventions'
      case 'project':
        return 'Modeling Scaling Trajectories'
      case 'synthesize':
        return 'Synthesizing Architecture Blueprint'
      case 'cite':
        return 'Verifying Primary Citations'
      case 'verify':
        return 'Evaluating Scientific Rigour'
      default:
        return stage.toUpperCase()
    }
  }

  const handleSendPerspective = (e: FormEvent) => {
    e.preventDefault()
    if (!userPerspective.trim()) return
    if (onAddPerspective) {
      // The action callback owns the confirmation. Notifying here as well
      // would raise a second, near-identical toast.
      onAddPerspective(userPerspective.trim())
    } else {
      onNotify?.('R&D Guidance Recorded', 'Perspective passed to Principal Investigator.', 'info')
    }
    setUserPerspective('')
  }

  const recentAudits = (run.audit || []).slice(-2)

  return (
    <div className="meeting-chamber">
      {/* 1. TOP MEETING BAR */}
      <header className="meeting-chamber__topbar">
        <div className="meeting-chamber__left">
          <div className="meeting-chamber__rec-badge">
            <span className="meeting-chamber__rec-dot" />
            <span>REC</span>
          </div>
          <span className="meeting-chamber__meeting-title">R&D Council Deliberation</span>
          <div className="meeting-chamber__stage-chip">
            <Radio size={12} className="meeting-chamber__stage-icon" />
            <span>{formatStageLabel(currentStage)}</span>
          </div>
        </div>

        <div className="meeting-chamber__center" title={run.question}>
          <span className="meeting-chamber__goal-label">Objective:</span>
          <span className="meeting-chamber__goal-text">{run.question}</span>
        </div>

        <div className="meeting-chamber__right">
          <div className="meeting-chamber__timer-pill">
            <span>⏱</span>
            <span>{formatTimer(secondsElapsed)}</span>
          </div>
          <span className="meeting-chamber__round-pill">
            Attempt {run.attempt || 1} / {run.max_attempts || 2}
          </span>
          <span className="meeting-chamber__fellows-pill">
            6 Fellows Active
          </span>
        </div>
      </header>

      {/* 2. MAIN MEETING FLOOR: SPOTLIGHT & COUNCIL GALLERY */}
      <main className="meeting-chamber__floor">
        {/* Spotlight Stage (Active Fellow Enlarged) */}
        <section className="meeting-chamber__spotlight" style={{ borderColor: activeFellow.color }}>
          <div className="meeting-chamber__spotlight-header">
            <div className="meeting-chamber__spotlight-fellow">
              <div
                className="meeting-chamber__avatar meeting-chamber__avatar--large"
                style={{ borderColor: activeFellow.color, color: activeFellow.color }}
              >
                {activeFellow.initials}
              </div>
              <div className="meeting-chamber__spotlight-identity">
                <span className="meeting-chamber__spotlight-name">{activeFellow.name}</span>
                <span className="meeting-chamber__spotlight-role">{activeFellow.role}</span>
              </div>
            </div>

            <div className="meeting-chamber__speaking-badge" style={{ borderColor: `${activeFellow.color}40` }}>
              <span className="meeting-chamber__speaking-dot" style={{ background: activeFellow.color }} />
              <span className="meeting-chamber__speaking-label">Presenting</span>
              <div className="meeting-chamber__equalizer">
                <span className="meeting-chamber__eq-bar" style={{ background: activeFellow.color }} />
                <span className="meeting-chamber__eq-bar" style={{ background: activeFellow.color }} />
                <span className="meeting-chamber__eq-bar" style={{ background: activeFellow.color }} />
              </div>
            </div>
          </div>

          <div className="meeting-chamber__speech-card">
            <span className="meeting-chamber__speech-quote-icon">“</span>
            <p className="meeting-chamber__speech-text">{getActiveSpeech()}</p>
          </div>

          {/* First-Principles Core Architecture Decomposition Panel */}
          {run.core_architecture && (
            <div className="meeting-chamber__arch-deck">
              <div className="meeting-chamber__arch-header">
                <div className="meeting-chamber__arch-title">
                  <Cpu size={13} className="meeting-chamber__arch-icon" />
                  <span>Base Architecture: <strong>{run.core_architecture.system_name}</strong></span>
                </div>
                <span className="meeting-chamber__arch-count">{run.core_architecture.primitives?.length ?? 0} Primitives Deconstructed</span>
              </div>

              <div className="meeting-chamber__arch-primitives">
                {(run.core_architecture.primitives ?? []).map((primitive) => (
                  <div key={primitive.name} className="meeting-chamber__primitive-pill" title={primitive.mechanism}>
                    <span className="meeting-chamber__primitive-name">{primitive.name}</span>
                    <span className="meeting-chamber__primitive-cat">{primitive.category}</span>
                  </div>
                ))}
              </div>

              <div className="meeting-chamber__arch-hotspot">
                <span className="meeting-chamber__hotspot-tag">Diagnosed Flaw Hotspot:</span>
                <span className="meeting-chamber__hotspot-text">{run.core_architecture.flaw_hotspot}</span>
              </div>
            </div>
          )}

          {/* Live R&D Invention Pitches (rendered when brainstormed ideas exist) */}
          {brainstormedIdeas.length > 0 && activeIdea && (
            <div className="meeting-chamber__brainstorm-deck">
              <div className="meeting-chamber__brainstorm-header">
                <div className="meeting-chamber__brainstorm-title">
                  <Lightbulb size={13} className="meeting-chamber__brainstorm-icon" />
                  <span>Breakthrough Inventions Brainstormed ({brainstormedIdeas.length})</span>
                </div>
                <div className="meeting-chamber__brainstorm-tabs">
                  {brainstormedIdeas.map((idea, idx) => (
                    <button
                      key={idea.id}
                      type="button"
                      className={`meeting-chamber__brainstorm-tab ${idx === selectedIdeaIdx ? 'meeting-chamber__brainstorm-tab--active' : ''}`}
                      onClick={() => setSelectedIdeaIdx(idx)}
                    >
                      Idea #{idx + 1}
                    </button>
                  ))}
                </div>
              </div>

              <div className="meeting-chamber__brainstorm-card">
                <div className="meeting-chamber__brainstorm-card-top">
                  <span className="meeting-chamber__brainstorm-name">{activeIdea.title}</span>
                  <span className="meeting-chamber__brainstorm-score">{activeIdea.feasibility_score}% Feasible</span>
                </div>
                <div className="meeting-chamber__brainstorm-transfer">
                  <Cpu size={12} />
                  <span>Paradigm Transferred from: <strong>{activeIdea.transferred_domain}</strong></span>
                </div>
                <p className="meeting-chamber__brainstorm-mech">{activeIdea.mechanism}</p>
                <div className="meeting-chamber__brainstorm-impact">
                  <span className="meeting-chamber__impact-label">Expected Impact:</span>
                  <span className="meeting-chamber__impact-val">{activeIdea.expected_impact}</span>
                </div>
              </div>
            </div>
          )}

          <div className="meeting-chamber__spotlight-footer">
            <div className="meeting-chamber__spotlight-meta">
              <span className="meeting-chamber__department-tag">{activeFellow.department}</span>
              {sources.length > 0 && (
                <span className="meeting-chamber__source-metric">
                  <FileText size={12} />
                  {sources.length} authoritative source{sources.length === 1 ? '' : 's'} ingested
                </span>
              )}
            </div>

            <span className="meeting-chamber__active-hint">
              Active turn in multi-agent research graph
            </span>
          </div>
        </section>

        {/* Council Gallery (Other Fellows in video-style tiles) */}
        <aside className="meeting-chamber__gallery">
          <div className="meeting-chamber__gallery-heading">
            <Layers size={13} />
            <span>Council Participants</span>
          </div>

          <div className="meeting-chamber__gallery-list">
            {otherFellows.map((fellow) => {
              const status = getFellowStatus(fellow.id)
              const statusLabel =
                status === 'done' ? 'Completed Turn' : status === 'analyzing' ? 'Analyzing Data' : 'Listening'

              return (
                <div
                  key={fellow.id}
                  className={`meeting-chamber__tile meeting-chamber__tile--${status}`}
                  onClick={() => onNotify?.(fellow.name, `${fellow.role} · ${fellow.department}`, 'info')}
                >
                  <div
                    className="meeting-chamber__avatar meeting-chamber__avatar--small"
                    style={{ borderColor: fellow.color, color: fellow.color }}
                  >
                    {fellow.initials}
                  </div>

                  <div className="meeting-chamber__tile-info">
                    <span className="meeting-chamber__tile-name">{fellow.name}</span>
                    <span className="meeting-chamber__tile-role">{fellow.role}</span>
                  </div>

                  <div className={`meeting-chamber__status-chip meeting-chamber__status-chip--${status}`}>
                    {status === 'done' && <span className="meeting-chamber__status-check">✓</span>}
                    {status === 'analyzing' && <span className="meeting-chamber__status-pulse" />}
                    <span>{statusLabel}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </aside>
      </main>

      {/* 3. BOTTOM MEETING CONTROLS & CAPTIONS */}
      <footer className="meeting-chamber__bottombar">
        {/* Real-Time Closed Captions / Deliberation Ticker */}
        <div className="meeting-chamber__ticker">
          <span className="meeting-chamber__ticker-label">Live Deliberation:</span>
          <div className="meeting-chamber__ticker-stream">
            {recentAudits.map((a, idx) => (
              <span key={idx} className="meeting-chamber__ticker-item">
                <span className="meeting-chamber__ticker-time">[{a.stage}]</span> {a.detail}
              </span>
            ))}
          </div>
        </div>

        {/* Interactive Perspective / Guidance Bar */}
        <form className="meeting-chamber__input-bar" onSubmit={handleSendPerspective}>
          <input
            type="text"
            className="meeting-chamber__input"
            placeholder="Intervene or add technical guidance to the R&D council..."
            value={userPerspective}
            onChange={(e) => setUserPerspective(e.target.value)}
          />
          <button type="submit" className="meeting-chamber__send-btn" title="Submit guidance">
            <Send size={14} />
          </button>
        </form>

        {/* Ingested Sources Drawer Pill */}
        {sources.length > 0 && (
          <button
            className="meeting-chamber__sources-pill"
            onClick={() => onOpenSource && onOpenSource(sources[0].id)}
            title="Inspect ingested evidence vault"
          >
            <Sparkles size={13} color="#38BDF8" />
            <span>{sources.length} Sources Ingested</span>
          </button>
        )}
      </footer>
    </div>
  )
}

export default AgentMeetingRoom
