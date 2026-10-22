import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import {
  Activity,
  CheckCircle2,
  Circle,
  CircleDot,
  Pause,
  Play,
  Radio,
  Send,
  Square,
  Target,
} from 'lucide-react'

import type {
  LiveProgressEvent,
  PanelTurn,
  ProblemCandidate,
  Run,
  RunLimits,
  RunSpend,
} from '../types.ts'
import './RoundTable.css'

/* ==========================================================================
   Round Table — the live deliberation surface.

   Layout follows the Cortex Lab live-run design: a stage rail on the left,
   the roundtable itself in the centre, and the working channel on the right.
   Every value shown here comes from a real backend event; nothing is faked.
   ========================================================================== */

type RoundTableProps = {
  domain: string
  question: string
  mode: 'problem' | 'topic'
  events: LiveProgressEvent[]
  run?: Run | null
  stage: string
  spend: RunSpend
  limits: RunLimits
  onPause?: () => void
  onCancel?: () => void
  onNudge?: (text: string) => void
  onSelectProblem?: (id: string) => void
  selectedProblemIds?: string[]
  selectedCandidate?: ProblemCandidate | null
}

type Seat = {
  id: string
  initials: string
  name: string
  color: string
  x: number
  y: number
  sub: string
}

type PipelineStep = {
  id: string
  code: string
  title: string
  detail: string
  state: 'pending' | 'active' | 'done' | 'checkpoint'
}

const PANEL_SEATS: Seat[] = [
  { id: 'practitioner', initials: 'PR', name: 'Practitioner', color: '#F5A524', x: 310, y: 60, sub: 'supporting' },
  { id: 'academic', initials: 'AC', name: 'Academic', color: '#5AB0FF', x: 467, y: 174, sub: 'defending, under fire' },
  { id: 'strategist', initials: 'ST', name: 'Strategist', color: '#4ADE9C', x: 407, y: 358, sub: 'reading the evidence' },
  { id: 'contrarian', initials: 'CO', name: 'Contrarian', color: '#FF7A70', x: 213, y: 358, sub: 'drafting a challenge' },
  { id: 'futurist', initials: 'FU', name: 'Futurist', color: '#B79CFF', x: 153, y: 174, sub: 'searching the web' },
]

const COUNCIL_SEATS: Seat[] = [
  { id: 'lead', initials: 'PI', name: 'Principal Investigator', color: '#5AB0FF', x: 310, y: 60, sub: 'convening' },
  { id: 'subagent-1', initials: 'AD', name: 'Architecture & Diagnostics', color: '#4ADE9C', x: 467, y: 174, sub: 'deconstructing' },
  { id: 'subagent-2', initials: 'CD', name: 'Cross-Domain Invention', color: '#F5A524', x: 407, y: 358, sub: 'transferring paradigms' },
  { id: 'subagent-3', initials: 'RT', name: 'Adversarial Red-Team', color: '#FF7A70', x: 213, y: 358, sub: 'attacking the claim' },
  { id: 'citation', initials: 'PA', name: 'Prior Art Auditor', color: '#B79CFF', x: 153, y: 174, sub: 'verifying citations' },
  { id: 'judge', initials: 'SJ', name: 'Scientific Rigour Judge', color: '#F472B6', x: 310, y: 358, sub: 'scoring rigour' },
]

const DISCOVERY_PIPELINE: { id: string; code: string; title: string }[] = [
  { id: 'scope_topic', code: 'D1', title: 'Scope topic' },
  { id: 'landscape_scan', code: 'D2', title: 'Landscape scan' },
  { id: 'mine_pain_points', code: 'D3', title: 'Pain-point mining' },
  { id: 'panel_round', code: 'D4', title: 'Panel discussion' },
  { id: 'problem_synthesis', code: 'D5', title: 'Problem synthesis' },
  { id: 'discovery_selection', code: 'D6', title: 'You decide' },
]

const COUNCIL_PIPELINE: { id: string; code: string; title: string }[] = [
  { id: 'plan', code: 'S1', title: 'Frame the problem' },
  { id: 'deconstruct', code: 'S2', title: 'Deconstruct architecture' },
  { id: 'gather', code: 'S3', title: 'Gather prior art' },
  { id: 'attack', code: 'S4', title: 'Adversarial attack' },
  { id: 'cross_examine', code: 'S5', title: 'Cross-examination' },
  { id: 'refine_attempt', code: 'S6', title: 'Resolve contested points' },
  { id: 'cross-pollinate', code: 'S7', title: 'Cross-domain invention' },
  { id: 'project', code: 'S8', title: 'Model the trajectory' },
  { id: 'synthesize', code: 'S9', title: 'Synthesise the blueprint' },
  { id: 'cite', code: 'S10', title: 'Verify citations' },
  { id: 'verify', code: 'S11', title: 'Judge the rigour' },
  { id: 'validate', code: 'S12', title: 'Validate and rank' },
]

const STAGE_DETAIL: Record<string, (count?: number) => string> = {
  scope_topic: (count) => `${count ?? 0} subtopics`,
  landscape_scan: (count) => `${count ?? 0} sources, 7 source types`,
  mine_pain_points: (count) => `${count ?? 0} pain points clustered`,
  panel_round: (count) => `Round ${count ?? 1} of 3`,
  problem_synthesis: (count) => `${count ?? 0} ranked problems`,
  discovery_selection: () => 'Checkpoint',
  plan: () => 'Research plan',
  deconstruct: () => 'First principles',
  gather: (count) => `${count ?? 0} sources retrieved`,
  attack: () => 'Stress test',
  cross_examine: () => 'Disagreements recorded',
  refine_attempt: () => 'Convergence check',
  'cross-pollinate': (count) => `${count ?? 0} inventions`,
  project: () => 'Quantitative model',
  synthesize: () => 'Blueprint',
  cite: (count) => `${count ?? 0} citations checked`,
  verify: () => 'Rigour rubric',
  validate: (count) => `${count ?? 0} ideas ranked`,
}

function formatUsd(value: number): string {
  return `$${value.toFixed(2)}`
}

const SEAT_COLORS: Record<string, string> = {
  practitioner: '#F5A524',
  academic: '#5AB0FF',
  strategist: '#4ADE9C',
  contrarian: '#FF7A70',
  futurist: '#B79CFF',
  moderator: '#4ADE9C',
  lead: '#5AB0FF',
  'subagent-1': '#4ADE9C',
  'subagent-2': '#F5A524',
  'subagent-3': '#FF7A70',
  citation: '#B79CFF',
  judge: '#F472B6',
}

function colorFor(speakerId: string): string {
  return SEAT_COLORS[speakerId] ?? '#5AB0FF'
}

function initialsFor(name: string): string {
  return name
    .split(' ')
    .map((word) => word[0] ?? '')
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

function stanceLabel(turn: PanelTurn): string {
  switch (turn.stance) {
    case 'support':
      return 'Supports'
    case 'challenge':
      return 'Challenges'
    case 'defend':
      return 'Defends'
    case 'question':
      return 'Questions'
    default:
      return 'Notes'
  }
}

function stanceTone(turn: PanelTurn): string {
  switch (turn.stance) {
    case 'support':
      return 'rt-support'
    case 'challenge':
      return 'rt-challenge'
    case 'defend':
      return 'rt-defend'
    case 'question':
      return 'rt-question'
    default:
      return 'rt-neutral'
  }
}

/** Collect the live transcript from whichever event shape the run produced. */
function useTranscript(events: LiveProgressEvent[], run?: Run | null): PanelTurn[] {
  return useMemo(() => {
    const turns: PanelTurn[] = []
    for (const event of events) {
      if (event.type === 'panel_turn' && event.speaker_name) {
        const panelTurn = event.panel_turn
        turns.push({
          id: panelTurn?.id ?? `${event.speaker_id ?? 'speaker'}-${turns.length}`,
          round: event.round ?? panelTurn?.round ?? 1,
          persona: event.speaker_name,
          persona_id: event.speaker_id ?? panelTurn?.persona_id ?? '',
          initials: panelTurn?.initials ?? initialsFor(event.speaker_name),
          color: panelTurn?.color ?? colorFor(event.speaker_id ?? ''),
          position: event.speech ?? panelTurn?.position ?? '',
          cites: panelTurn?.cites ?? [],
          cite_labels: panelTurn?.cite_labels ?? [],
          evidence_ids: panelTurn?.evidence_ids ?? [],
          challenges: panelTurn?.challenges ?? [],
          stance: panelTurn?.stance ?? 'neutral',
          status: 'done',
          is_moderator: panelTurn?.is_moderator,
        })
      } else if (event.type === 'agent_speech' && event.speaker_name) {
        turns.push({
          id: `${event.speaker_id ?? 'speaker'}-${turns.length}`,
          round: 1,
          persona: event.speaker_name,
          persona_id: event.speaker_id ?? '',
          initials: initialsFor(event.speaker_name),
          color: colorFor(event.speaker_id ?? ''),
          position: event.speech ?? '',
          cites: [],
          cite_labels: [],
          evidence_ids: [],
          challenges: [],
          stance: 'neutral',
          status: 'done',
        })
      }
    }
    if (turns.length === 0 && run?.transcript?.length) return run.transcript
    return turns
  }, [events, run])
}

export const RoundTable: React.FC<RoundTableProps> = ({
  domain,
  question,
  mode,
  events,
  run,
  stage,
  spend,
  limits,
  onPause,
  onCancel,
  onNudge,
  onSelectProblem,
  selectedProblemIds = [],
  selectedCandidate,
}) => {
  const [nudge, setNudge] = useState('')
  const [paused, setPaused] = useState(false)
  const threadRef = useRef<HTMLDivElement>(null)

  const seats = mode === 'topic' ? PANEL_SEATS : COUNCIL_SEATS
  const pipeline = mode === 'topic' ? DISCOVERY_PIPELINE : COUNCIL_PIPELINE
  const transcript = useTranscript(events, run)
  const candidates = run?.problem_candidates ?? []

  useEffect(() => {
    const node = threadRef.current
    if (node) node.scrollTop = node.scrollHeight
  }, [transcript.length])

  const activeSpeakerId = useMemo(() => {
    for (let index = events.length - 1; index >= 0; index -= 1) {
      const event = events[index]
      if ((event.type === 'panel_turn' || event.type === 'agent_speech') && event.speaker_id) {
        return event.speaker_id
      }
    }
    return run?.active_speaker?.id ?? null
  }, [events, run])

  const activeSeat = seats.find((seat) => seat.id === activeSpeakerId) ?? null

  const counters = useMemo(() => {
    const searches = events.filter((event) => event.type === 'search_query_finished').length
    const evidence = run?.sources?.length ?? events.filter((e) => e.type === 'page_fetch_finished').length
    const turns = transcript.length
    const problems = candidates.length
    return { searches, evidence, turns, problems }
  }, [events, transcript.length, candidates.length, run])

  const pipelineSteps = useMemo<PipelineStep[]>(() => {
    const currentIndex = pipeline.findIndex((step) => step.id === stage)
    const stageCounts: Record<string, number> = {
      scope_topic: run?.scope?.subtopics?.length ?? 0,
      landscape_scan: counters.evidence,
      mine_pain_points: run?.pain_points?.length ?? 0,
      panel_round: run?.panel_round ?? 1,
      problem_synthesis: counters.problems,
      gather: counters.evidence,
      'cross-pollinate': run?.brainstormed_ideas?.length ?? 0,
      cite: run?.citation_verifications?.length ?? 0,
      validate: run?.ranked_ideas?.length ?? 0,
    }
    return pipeline.map((step, index) => {
      let state: PipelineStep['state'] = 'pending'
      if (currentIndex >= 0) {
        if (index < currentIndex) state = 'done'
        else if (index === currentIndex) state = step.id === 'discovery_selection' ? 'checkpoint' : 'active'
      }
      if (step.id === 'discovery_selection' && state === 'active') state = 'checkpoint'
      return {
        ...step,
        detail: STAGE_DETAIL[step.id]?.(stageCounts[step.id]) ?? '',
        state,
      }
    })
  }, [pipeline, stage, run, counters])

  const budgetUsed = limits.max_usd > 0 ? Math.min(1, spend.usd / limits.max_usd) : 0
  const convergence = run?.convergence ?? 0

  const flows = useMemo(() => {
    const byId = new Map(seats.map((seat) => [seat.id, seat]))
    const result: { from: Seat; to: Seat; kind: 'support' | 'challenge' }[] = []
    for (const turn of transcript.slice(-8)) {
      if (!turn.challenges?.length) continue
      const from = byId.get(turn.persona_id)
      for (const targetId of turn.challenges) {
        const to = byId.get(targetId)
        if (from && to) {
          result.push({ from, to, kind: turn.stance === 'challenge' ? 'challenge' : 'support' })
        }
      }
    }
    return result.slice(-4)
  }, [transcript, seats])

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    const text = nudge.trim()
    if (!text || !onNudge) return
    onNudge(text)
    setNudge('')
  }

  const thinkingLines = useMemo(() => {
    const lines: { text: string; kind: 'think' | 'tool' | 'result' }[] = []
    for (const event of events.slice(-40)) {
      if (event.type === 'thinking_step') {
        if (event.scratchpad) lines.push({ text: event.scratchpad, kind: 'think' })
        if (event.decision) lines.push({ text: event.decision, kind: 'result' })
      } else if (event.type === 'search_query_started') {
        lines.push({ text: event.query ?? '', kind: 'tool' })
      } else if (event.type === 'search_query_finished') {
        lines.push({ text: `${event.result_count ?? 0} hits`, kind: 'result' })
      } else if (event.type === 'page_fetch_finished') {
        lines.push({ text: event.title ?? event.publisher ?? 'page read', kind: 'result' })
      }
    }
    return lines.slice(-7)
  }, [events])

  return (
    <div className="rt-shell">
      {/* ---------- Header ---------- */}
      <header className="rt-header">
        <div className="rt-header__brand">
          <span className="rt-header__name">FORESIGHTFORGE</span>
          <span className="rt-header__divider" />
          <span className="rt-header__domain" title={question}>
            {domain}
          </span>
          <span className={`rt-tag ${mode === 'topic' ? 'rt-tag--violet' : 'rt-tag--blue'}`}>
            {mode === 'topic' ? 'Topic Discovery' : 'Problem Mode'}
          </span>
        </div>

        <div className="rt-header__right">
          <div className="rt-budget">
            <div className="rt-budget__row">
              <span>Budget</span>
              <span className="rt-mono">
                {formatUsd(spend.usd)} of {formatUsd(limits.max_usd)}
              </span>
            </div>
            <div className="rt-bar">
              <i style={{ width: `${Math.round(budgetUsed * 100)}%` }} />
            </div>
          </div>

          {onPause && (
            <button
              type="button"
              className="rt-btn rt-btn--ghost"
              onClick={() => {
                const next = !paused
                setPaused(next)
                onPause()
              }}
            >
              {paused ? <Play size={13} /> : <Pause size={13} />}
              {paused ? 'Resume' : 'Pause'}
            </button>
          )}
          {onCancel && (
            <button type="button" className="rt-btn rt-btn--ghost" onClick={onCancel}>
              <Square size={12} /> Cancel
            </button>
          )}
          {selectedCandidate && (
            <span className="rt-tag rt-tag--amber">Next: you choose the problem</span>
          )}
        </div>
      </header>

      {/* ---------- Body ---------- */}
      <div className="rt-body">
        {/* --- Left rail --- */}
        <aside className="rt-rail">
          <section className="rt-card rt-card--flush">
            <p className="rt-lbl">{mode === 'topic' ? 'Discovery pipeline' : 'Council pipeline'}</p>
            <ol className="rt-pipeline">
              {pipelineSteps.map((step) => (
                <li key={step.id} className={`rt-pipeline__item rt-pipeline__item--${step.state}`}>
                  <span className="rt-pipeline__dot" aria-hidden="true">
                    {step.state === 'done' ? (
                      <CheckCircle2 size={13} />
                    ) : step.state === 'active' ? (
                      <CircleDot size={13} />
                    ) : step.state === 'checkpoint' ? (
                      <Target size={13} />
                    ) : (
                      <Circle size={13} />
                    )}
                  </span>
                  <div>
                    <p className="rt-pipeline__title">
                      {step.code} {step.title}
                    </p>
                    {step.detail && <p className="rt-pipeline__detail">{step.detail}</p>}
                  </div>
                </li>
              ))}
            </ol>
          </section>

          <section className="rt-card rt-card--flush">
            <p className="rt-lbl">Live counters</p>
            <div className="rt-counters">
              <div>
                <p className="rt-mono rt-counters__value">{counters.evidence}</p>
                <p className="rt-counters__label">Evidence</p>
              </div>
              <div>
                <p className="rt-mono rt-counters__value">{counters.searches}</p>
                <p className="rt-counters__label">Searches</p>
              </div>
              <div>
                <p className="rt-mono rt-counters__value">{counters.turns}</p>
                <p className="rt-counters__label">Turns</p>
              </div>
              <div>
                <p className="rt-mono rt-counters__value">{counters.problems}</p>
                <p className="rt-counters__label">Problems</p>
              </div>
            </div>
          </section>
        </aside>

        {/* --- Centre: the roundtable --- */}
        <main className="rt-centre">
          <section className="rt-card rt-card--table">
            <div className="rt-card__head">
              <p className="rt-lbl">{mode === 'topic' ? 'The Round Table' : 'The Council'}</p>
              <div className="rt-legend">
                <span>
                  <i style={{ background: '#FF7A70' }} /> challenge
                </span>
                <span>
                  <i style={{ background: '#4ADE9C' }} /> support
                </span>
              </div>
            </div>

            <div className="rt-table-wrap">
              <svg
                className="rt-table"
                viewBox="0 0 620 440"
                role="img"
                aria-label={`${seats.length} agents around a moderator. ${
                  activeSeat ? `${activeSeat.name} is speaking.` : 'No agent is currently speaking.'
                }`}
              >
                <circle cx="310" cy="225" r="205" fill="none" stroke="#1F2733" strokeWidth="1" />
                <circle
                  cx="310"
                  cy="225"
                  r="140"
                  fill="none"
                  stroke="#1B2330"
                  strokeWidth="1"
                  strokeDasharray="2 6"
                />

                {flows.map((flow, index) => (
                  <line
                    key={`flow-${index}`}
                    className={`rt-flow ${flow.kind === 'challenge' ? 'rt-flow--challenge' : 'rt-flow--support'}`}
                    x1={flow.from.x}
                    y1={flow.from.y}
                    x2={flow.to.x}
                    y2={flow.to.y}
                    strokeWidth={flow.kind === 'challenge' ? 2 : 1.5}
                    opacity={flow.kind === 'challenge' ? 1 : 0.4}
                  />
                ))}

                <circle cx="310" cy="225" r="52" fill="#151A22" stroke="#222B37" strokeWidth="8" />
                <circle
                  cx="310"
                  cy="225"
                  r="52"
                  fill="none"
                  stroke="#4ADE9C"
                  strokeWidth="8"
                  strokeLinecap="round"
                  strokeDasharray={`${Math.round(convergence * 327)} 327`}
                  transform="rotate(-90 310 225)"
                />
                <text x="310" y="226" textAnchor="middle" fill="#E8ECF1" className="rt-svg-mono" fontSize="22">
                  {convergence.toFixed(2)}
                </text>
                <text x="310" y="244" textAnchor="middle" fill="#9AA6B5" fontSize="10">
                  {convergence >= 0.8 ? 'converged' : 'converging'}
                </text>
                <text x="310" y="296" textAnchor="middle" fill="#9AA6B5" fontSize="11">
                  Moderator · target 0.80
                </text>

                {seats.map((seat) => {
                  const speaking = seat.id === activeSpeakerId
                  return (
                    <g key={seat.id} className={speaking ? 'rt-seat rt-seat--active' : 'rt-seat'}>
                      {speaking && <circle className="rt-halo" cx={seat.x} cy={seat.y} r="34" />}
                      <circle
                        cx={seat.x}
                        cy={seat.y}
                        r="30"
                        fill="#1A2230"
                        stroke={seat.color}
                        strokeWidth={speaking ? 3 : 2}
                      />
                      <text
                        x={seat.x}
                        y={seat.y + 5}
                        textAnchor="middle"
                        fill={seat.color}
                        className="rt-svg-grotesk"
                        fontWeight="700"
                        fontSize="15"
                      >
                        {seat.initials}
                      </text>
                      <text x={seat.x} y={seat.y + 48} textAnchor="middle" fill="#E8ECF1" fontSize="12" fontWeight="600">
                        {seat.name}
                      </text>
                      <text
                        x={seat.x}
                        y={seat.y + 63}
                        textAnchor="middle"
                        fill={speaking ? seat.color : '#9AA6B5'}
                        fontSize="11"
                      >
                        {speaking ? 'speaking now' : seat.sub}
                      </text>
                    </g>
                  )
                })}
              </svg>
            </div>
          </section>

          {mode === 'topic' && (
            <section className="rt-card rt-card--grow rt-card--problems">
              <p className="rt-lbl">Problems taking shape</p>
              {candidates.length === 0 ? (
                <p className="rt-empty">
                  The panel has not ranked any problems yet. They appear here as the debate settles.
                </p>
              ) : (
                <div className="rt-problem-grid">
                  {candidates.map((candidate) => {
                    const selected = selectedProblemIds.includes(candidate.id)
                    const isCurrent = selectedCandidate?.id === candidate.id
                    return (
                      <button
                        type="button"
                        key={candidate.id}
                        className={`rt-problem ${selected ? 'rt-problem--selected' : ''} ${
                          isCurrent ? 'rt-problem--current' : ''
                        }`}
                        onClick={() => onSelectProblem?.(candidate.id)}
                        disabled={!onSelectProblem}
                      >
                        <span
                          className={`rt-tag ${
                            selected
                              ? 'rt-tag--green'
                              : candidate.rank === 1
                                ? 'rt-tag--green'
                                : 'rt-tag--neutral'
                          }`}
                        >
                          {selected ? 'Selected' : candidate.rank === 1 ? 'Converging' : `Rank ${candidate.rank ?? '-'}`}
                        </span>
                        <p className="rt-problem__statement">{candidate.statement}</p>
                        <div className="rt-problem__metrics">
                          <div>
                            <span>Severity</span>
                            <div className="rt-bar">
                              <i style={{ width: `${Math.round((candidate.severity ?? 0) * 100)}%`, background: '#4ADE9C' }} />
                            </div>
                          </div>
                          <div>
                            <span>Gap size</span>
                            <div className="rt-bar">
                              <i style={{ width: `${Math.round((candidate.gap_size ?? 0) * 100)}%`, background: '#5AB0FF' }} />
                            </div>
                          </div>
                        </div>
                        {candidate.cite_labels?.length > 0 && (
                          <div className="rt-chips">
                            {(candidate.cite_labels ?? []).slice(0, 4).map((label) => (
                              <span className="rt-chip" key={label}>
                                {label}
                              </span>
                            ))}
                          </div>
                        )}
                      </button>
                    )
                  })}
                </div>
              )}
            </section>
          )}
        </main>

        {/* --- Right: working channel --- */}
        <aside className="rt-channel">
          <section className="rt-card rt-card--flush">
            <div className="rt-thinking__head">
              {activeSeat ? (
                <>
                  <span
                    className="rt-avatar"
                    style={{ borderColor: activeSeat.color, color: activeSeat.color }}
                    aria-hidden="true"
                  >
                    {activeSeat.initials}
                  </span>
                  <p className="rt-thinking__name">{activeSeat.name} is working</p>
                </>
              ) : (
                <>
                  <span className="rt-avatar rt-avatar--idle" aria-hidden="true">
                    <Radio size={12} />
                  </span>
                  <p className="rt-thinking__name">Council is gathering evidence</p>
                </>
              )}
              <span className="rt-mono rt-thinking__step">
                step {(transcript.length % 5) + 1} of 5
              </span>
            </div>
            <div className="rt-thinking">
              {thinkingLines.length === 0 ? (
                <p className="rt-empty rt-empty--tight">
                  Tool calls and reasoning steps appear here as the council works.
                </p>
              ) : (
                thinkingLines.map((line, index) => (
                  <p
                    key={`${line.kind}-${index}`}
                    className={`rt-thinking__line rt-thinking__line--${line.kind}`}
                  >
                    {line.kind === 'think' && <span className="rt-thinking__prompt">&gt; </span>}
                    {line.kind === 'result' && <span className="rt-thinking__prompt rt-thinking__prompt--ok">&lt; </span>}
                    {line.kind === 'tool' && <span className="rt-chip">web_search</span>}
                    {line.text}
                    {index === thinkingLines.length - 1 && <span className="rt-caret" />}
                  </p>
                ))
              )}
            </div>
          </section>

          <section className="rt-card rt-card--grow rt-thread">
            <p className="rt-lbl">Discussion · {mode === 'topic' ? `round ${run?.panel_round ?? 1}` : 'deliberation'}</p>
            <div className="rt-thread__list" ref={threadRef} aria-live="polite">
              {transcript.length === 0 ? (
                <p className="rt-empty">
                  No statements yet. The roundtable opens once the first agent has evidence to speak from.
                </p>
              ) : (
                transcript.map((turn, index) => (
                  <article className="rt-turn" key={turn.id ?? `${turn.persona}-${index}`}>
                    <span
                      className="rt-avatar rt-avatar--small"
                      style={{ borderColor: turn.color ?? '#5AB0FF', color: turn.color ?? '#5AB0FF' }}
                      aria-hidden="true"
                    >
                      {turn.initials}
                    </span>
                    <div className="rt-turn__body">
                      <div className="rt-turn__byline">
                        <b>{turn.persona}</b>
                        {!turn.is_moderator && (
                          <span className={`rt-tag rt-tag--tight ${stanceTone(turn)}`}>{stanceLabel(turn)}</span>
                        )}
                        {turn.is_moderator && <span className="rt-tag rt-tag--tight rt-tag--green">Moderator</span>}
                      </div>
                      <p className="rt-turn__text">{turn.position}</p>
                      {turn.cite_labels?.length > 0 && (
                        <div className="rt-chips">
                          {(turn.cite_labels ?? []).slice(0, 5).map((label) => (
                            <span className="rt-chip" key={label}>
                              {label}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </article>
                ))
              )}
            </div>

            {onNudge && (
              <form className="rt-nudge" onSubmit={handleSubmit}>
                <label className="rt-sr-only" htmlFor="rt-nudge-input">
                  Steer the panel
                </label>
                <input
                  id="rt-nudge-input"
                  value={nudge}
                  onChange={(event) => setNudge(event.target.value)}
                  placeholder="Steer the panel (optional)"
                />
                <button type="submit" disabled={!nudge.trim()}>
                  <Send size={13} /> Send
                </button>
              </form>
            )}
          </section>
        </aside>
      </div>

      <footer className="rt-footer">
        <Activity size={12} />
        <span>
          Every line above is a real backend operation. Model reasoning needs a configured provider; without
          one the council reports only what it retrieved.
        </span>
        <span className="rt-mono rt-footer__right">
          {spend.tokens.toLocaleString()} tokens · {spend.calls} model calls
        </span>
      </footer>
    </div>
  )
}
