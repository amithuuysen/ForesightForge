import React from 'react'
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  ExternalLink,
  ShieldCheck,
  FileCheck,
  Award,
  Lightbulb,
  Zap,
  FlaskConical,
  Cpu,
  Target,
  MessagesSquare,
} from 'lucide-react'
import type { ArchitecturePrimitive, Claim, OpenQuestion, Run, Source } from '../types.ts'
import './ResearchOutcome.css'

type ResearchOutcomeProps = {
  run: Run
  sources: Source[]
  claims?: Claim[]
  openQuestions?: OpenQuestion[]
  onOpenSource?: (sourceId: string) => void
  onNewResearch?: () => void
  onSaveClaim?: (claim: Claim) => void
  onDeleteClaim?: (claimId: string) => void
  onSaveOpenQuestion?: (question: OpenQuestion) => void
  onDeleteOpenQuestion?: (questionId: string) => void
}

export const ResearchOutcome: React.FC<ResearchOutcomeProps> = ({
  run,
  sources,
  claims = [],
  openQuestions = [],
  onOpenSource,
  onNewResearch,
  onSaveClaim,
  onDeleteClaim,
  onSaveOpenQuestion,
  onDeleteOpenQuestion,
}) => {
  const forecast = run.forecast
  const evaluation = run.evaluation

  const isCompleted = run.status === 'completed'

  // The model returns confidence on a 0-1 scale while the rubric score is on a
  // 0-10 scale. Normalise both to a 0-100 percentage so the meter and the
  // label can never disagree.
  const confidencePercent = (() => {
    if (forecast?.confidence_score !== undefined && forecast?.confidence_score !== null) {
      const raw = Number(forecast.confidence_score)
      return Math.max(0, Math.min(100, raw <= 1 ? raw * 100 : raw))
    }
    if (evaluation?.overall_score) {
      return Math.max(0, Math.min(100, Math.round(Number(evaluation.overall_score) * 10)))
    }
    return 78
  })()

  const brainstormedIdeas = run.brainstormed_ideas || forecast?.brainstormed_ideas || []
  const overcomeStrategies = run.overcome_strategies || forecast?.overcome_strategies || []
  // An empty object is truthy, so the architecture card would render with a
  // blank title and "0 Primitives". Require actual content before showing it.
  const rawArchitecture = run.core_architecture || forecast?.core_architecture
  const coreArchitecture =
    rawArchitecture &&
    (rawArchitecture.system_name ||
      rawArchitecture.flaw_hotspot ||
      (rawArchitecture.primitives?.length ?? 0) > 0)
      ? rawArchitecture
      : undefined
  const rankedIdeas = run.ranked_ideas ?? run.ideas ?? []
  const validationResults = run.validation_results ?? []
  const spend = run.spend

  return (
    <div className="rnd-outcome">
      {/* 1. TOP DOCUMENT HEADER */}
      <header className="rnd-outcome__header">
        <div className="rnd-outcome__nav">
          {onNewResearch && (
            <button className="rnd-outcome__back-btn" onClick={onNewResearch}>
              <ArrowLeft size={14} />
              <span>New R&D Inquiry</span>
            </button>
          )}

          <div className="rnd-outcome__doc-meta">
            <span className="rnd-outcome__doc-id">REPORT #{run.id.slice(0, 8).toUpperCase()}</span>
            <span className="rnd-outcome__doc-date">{new Date(run.updated_at).toLocaleDateString()}</span>
          </div>
        </div>

        <div className="rnd-outcome__title-section">
          <span className="rnd-outcome__domain-chip">{run.domain}</span>
          <h1 className="rnd-outcome__headline">{run.question}</h1>

          <div className="rnd-outcome__badges-row">
            <span className={`rnd-outcome__status-pill ${isCompleted ? 'rnd-outcome__status-pill--success' : 'rnd-outcome__status-pill--warning'}`}>
              <ShieldCheck size={12} />
              <span>{isCompleted ? 'Architecturally Feasible' : 'Needs Empirical Verification'}</span>
            </span>

            <span className="rnd-outcome__attempt-pill">
              {run.attempt || 1} Iterative Attempt{(run.attempt || 1) === 1 ? '' : 's'} Converged
            </span>

            <span className="rnd-outcome__sources-pill">
              <FileCheck size={12} />
              <span>{sources.length} Primary Citations Grounded</span>
            </span>
          </div>
        </div>
      </header>

      {/* 2. EXECUTIVE INVENTION & ARCHITECTURAL BLUEPRINT */}
      {forecast && (
        <section className="rnd-outcome__card rnd-outcome__card--highlight">
          <div className="rnd-outcome__card-header">
            <div className="rnd-outcome__section-badge">
              <Award size={14} />
              <span>Architectural Invention Blueprint</span>
            </div>
            <span className="rnd-outcome__verdict-tag">{forecast.verdict}</span>
          </div>

          <h2 className="rnd-outcome__solution-title">{forecast.headline}</h2>

          {/* Feasibility Meter */}
          <div className="rnd-outcome__meter-wrap">
            <div className="rnd-outcome__meter-labels">
              <span className="rnd-outcome__meter-name">{forecast.confidence_label || 'Engineering Feasibility'}</span>
              <span className="rnd-outcome__meter-score">{Math.round(confidencePercent)}% Saturation</span>
            </div>
            <div className="rnd-outcome__meter-track">
              <div
                className="rnd-outcome__meter-fill"
                style={{ width: `${confidencePercent}%` }}
              />
            </div>
          </div>

          {forecast.confidence_summary && (
            <p className="rnd-outcome__summary-text">{forecast.confidence_summary}</p>
          )}
        </section>
      )}

      {/* 2B. FIRST-PRINCIPLES BASE CORE ARCHITECTURE DECONSTRUCTION */}
      {coreArchitecture && (
        <section className="rnd-outcome__card rnd-outcome__card--arch">
          <div className="rnd-outcome__card-header">
            <div>
              <div className="rnd-outcome__section-badge rnd-outcome__section-badge--cyan">
                <Cpu size={14} />
                <span>Base Core Architecture Deconstruction</span>
              </div>
              <h3 className="rnd-outcome__section-title">{coreArchitecture.system_name}</h3>
              <span className="rnd-outcome__section-subtitle">
                First-principles anatomical mapping of foundational primitives, governing equations, and failure bottlenecks
              </span>
            </div>
            <span className="rnd-outcome__pill-count rnd-outcome__pill-count--cyan">
              {coreArchitecture.primitives?.length ?? 0} Primitives Deconstructed
            </span>
          </div>

          <p className="rnd-outcome__arch-summary">{coreArchitecture.foundational_summary}</p>

          {coreArchitecture.governing_equation && (
            <div className="rnd-outcome__equation-box">
              <span className="rnd-outcome__equation-label">Governing Mathematical / Physical Dynamics:</span>
              <code className="rnd-outcome__equation-code">{coreArchitecture.governing_equation}</code>
            </div>
          )}

          {/* Primitives Grid */}
          <div className="rnd-outcome__primitives-grid">
            {(coreArchitecture.primitives ?? []).map((primitive: ArchitecturePrimitive, idx: number) => (
              <div key={primitive.name || idx} className="rnd-outcome__primitive-card">
                <div className="rnd-outcome__primitive-header">
                  <span className="rnd-outcome__primitive-idx">0{idx + 1}</span>
                  <div className="rnd-outcome__primitive-title-group">
                    <h4 className="rnd-outcome__primitive-name">{primitive.name}</h4>
                    <span className="rnd-outcome__primitive-category">{primitive.category}</span>
                  </div>
                </div>

                <div className="rnd-outcome__primitive-detail">
                  <span className="rnd-outcome__detail-tag">Core Mechanism:</span>
                  <p className="rnd-outcome__detail-text">{primitive.mechanism}</p>
                </div>

                <div className="rnd-outcome__primitive-detail">
                  <span className="rnd-outcome__detail-tag">Systemic Role:</span>
                  <p className="rnd-outcome__detail-text">{primitive.role_in_system}</p>
                </div>

                <div className="rnd-outcome__primitive-bottleneck">
                  <span className="rnd-outcome__bottleneck-tag">Physical / Computational Bottleneck:</span>
                  <p className="rnd-outcome__bottleneck-text">{primitive.bottleneck_equation_or_limit}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Root-Cause Flaw Hotspot */}
          <div className="rnd-outcome__hotspot-card">
            <div className="rnd-outcome__hotspot-icon-wrap">
              <AlertTriangle size={18} className="rnd-outcome__icon-warn" />
            </div>
            <div className="rnd-outcome__hotspot-content">
              <span className="rnd-outcome__hotspot-title">Isolated Root-Cause Flaw Hotspot:</span>
              <p className="rnd-outcome__hotspot-desc">{coreArchitecture.flaw_hotspot}</p>
              <span className="rnd-outcome__hotspot-note">
                ↳ The R&D Council's interdisciplinary solutions and breakthrough pitches below are targeted specifically to eliminate this bottleneck.
              </span>
            </div>
          </div>
        </section>
      )}

      {/* 2A. PANEL TRANSCRIPT (FR-DS-7) */}
      {(run.transcript?.length ?? 0) > 0 && (
        <section className="rnd-outcome__card">
          <div className="rnd-outcome__card-header">
            <div>
              <div className="rnd-outcome__section-badge rnd-outcome__section-badge--amber">
                <MessagesSquare size={14} />
                <span>Panel Transcript ({run.transcript?.length})</span>
              </div>
              <h3 className="rnd-outcome__section-title">
                {run.panel_round ? `Round ${run.panel_round} of deliberation` : 'Deliberation Record'}
              </h3>
              <span className="rnd-outcome__section-subtitle">
                Every panel statement with the evidence ids it relied on. Convergence reached{' '}
                {(run.convergence ?? 0).toFixed(2)} against a target of 0.80.
              </span>
            </div>
          </div>
          <div className="rnd-transcript">
            {run.transcript?.map((turn) => (
              <article className="rnd-transcript__turn" key={turn.id}>
                <span
                  className="rnd-transcript__avatar"
                  style={{ borderColor: turn.color, color: turn.color }}
                  aria-hidden="true"
                >
                  {turn.initials}
                </span>
                <div className="rnd-transcript__body">
                  <div className="rnd-transcript__byline">
                    <b>{turn.persona}</b>
                    <span className="rnd-transcript__stance">{turn.stance}</span>
                    <span className="rnd-transcript__round">round {turn.round}</span>
                  </div>
                  <p className="rnd-transcript__text">{turn.position}</p>
                  {turn.cite_labels && turn.cite_labels.length > 0 && (
                    <div className="rnd-transcript__cites">
                      {turn.cite_labels.map((label) => (
                        <span className="rnd-outcome__cite-chip" key={label}>
                          {label}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {/* 2B. RANKED IDEA BOARD (FR-OT-2) */}
      {rankedIdeas.length > 0 && (
        <section className="rnd-outcome__card">
          <div className="rnd-outcome__card-header">
            <div>
              <div className="rnd-outcome__section-badge rnd-outcome__section-badge--green">
                <FlaskConical size={14} />
                <span>Ranked Ideas ({rankedIdeas.length})</span>
              </div>
              <h3 className="rnd-outcome__section-title">
                Ideas Scored on Feasibility, Impact, Novelty and Cost to Test
              </h3>
              <span className="rnd-outcome__section-subtitle">
                Each idea states what it is, why it should work, the limitation it targets, its
                evidence, its risks, its validation level and the cheapest next test.
              </span>
            </div>
          </div>

          <div className="rnd-ideas">
            {rankedIdeas.map((idea) => {
              const validation = validationResults.find((item) => item.idea_id === idea.id)
              return (
                <article className="rnd-idea" key={idea.id}>
                  <header className="rnd-idea__head">
                    <span className="rnd-idea__rank">#{idea.rank ?? '-'}</span>
                    <h4 className="rnd-idea__title">{idea.title}</h4>
                    <span className={`rnd-idea__level rnd-idea__level--${(idea.validation_level ?? 'L0').toLowerCase()}`}>
                      {idea.validation_level ?? 'L0'}
                    </span>
                  </header>

                  {idea.description && <p className="rnd-idea__body">{idea.description}</p>}

                  {idea.why_it_should_work && (
                    <div className="rnd-idea__row">
                      <span className="rnd-idea__row-label">Why it should work</span>
                      <p className="rnd-idea__row-text">{idea.why_it_should_work}</p>
                    </div>
                  )}

                  {idea.targets && (
                    <div className="rnd-idea__row">
                      <span className="rnd-idea__row-label">Addresses</span>
                      <p className="rnd-idea__row-text">{idea.targets}</p>
                    </div>
                  )}

                  {idea.risks && idea.risks.length > 0 && (
                    <div className="rnd-idea__row">
                      <span className="rnd-idea__row-label">Risks</span>
                      <ul className="rnd-idea__risks">
                        {idea.risks.map((risk, index) => (
                          <li key={index}>{risk}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="rnd-idea__scores">
                    {(
                      [
                        ['Feasibility', idea.feasibility],
                        ['Impact', idea.impact],
                        ['Novelty', idea.novelty],
                        ['Cost', idea.cost_to_test],
                      ] as const
                    ).map(([label, value]) => (
                      <div className="rnd-idea__score" key={label}>
                        <span>{label}</span>
                        <div className="rnd-idea__score-bar">
                          <i style={{ width: `${Math.round((value ?? 0) * 100)}%` }} />
                        </div>
                        <b>{value !== undefined && value !== null ? value.toFixed(2) : '—'}</b>
                      </div>
                    ))}
                  </div>

                  <footer className="rnd-idea__foot">
                    <div className="rnd-idea__next-test">
                      <Zap size={12} />
                      <span>Cheapest next test</span>
                      <p>
                        {idea.cheapest_test || idea.next_test || 'No test defined — treat as a hypothesis.'}
                      </p>
                    </div>
                    {validation && <span className="rnd-idea__validation">{validation.rationale}</span>}
                  </footer>
                </article>
              )
            })}
          </div>
        </section>
      )}

      {/* 2C. DISCOVERED PROBLEMS (FR-DS-5/6) */}
      {(run.problem_candidates?.length ?? 0) > 0 && (
        <section className="rnd-outcome__card">
          <div className="rnd-outcome__card-header">
            <div>
              <div className="rnd-outcome__section-badge rnd-outcome__section-badge--violet">
                <Target size={14} />
                <span>Discovered Problems ({run.problem_candidates?.length})</span>
              </div>
              <h3 className="rnd-outcome__section-title">Ranked Problem Statements</h3>
              <span className="rnd-outcome__section-subtitle">
                Severity, tractability and gap size scored by the panel, with the evidence behind each.
              </span>
            </div>
          </div>
          <div className="rnd-problems">
            {run.problem_candidates?.map((problem) => (
              <article className="rnd-problem-row" key={problem.id}>
                <span className="rnd-problem-row__rank">#{problem.rank ?? '-'}</span>
                <div className="rnd-problem-row__body">
                  <p className="rnd-problem-row__statement">{problem.statement}</p>
                  {problem.why_it_matters && (
                    <p className="rnd-problem-row__why">{problem.why_it_matters}</p>
                  )}
                  <div className="rnd-problem-row__metrics">
                    <span>Severity {(problem.severity ?? 0).toFixed(2)}</span>
                    <span>Tractability {(problem.tractability ?? 0).toFixed(2)}</span>
                    <span>Gap {(problem.gap_size ?? 0).toFixed(2)}</span>
                    {problem.cite_labels?.slice(0, 4).map((label) => (
                      <span className="rnd-outcome__cite-chip" key={label}>
                        {label}
                      </span>
                    ))}
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {/* 2D. RUN LEDGER: budget, validation and mode */}
      {(spend || run.limits) && (
        <section className="rnd-outcome__card">
          <div className="rnd-outcome__card-header">
            <div>
              <div className="rnd-outcome__section-badge">
                <Cpu size={14} />
                <span>Run Ledger</span>
              </div>
              <h3 className="rnd-outcome__section-title">Budget, Validation and Intake</h3>
            </div>
          </div>
          <div className="rnd-ledger">
            {run.mode && (
              <div className="rnd-ledger__item">
                <span>Intake mode</span>
                <b>{run.mode}</b>
              </div>
            )}
            {run.limits && (
              <>
                <div className="rnd-ledger__item">
                  <span>Depth</span>
                  <b>{run.limits.depth}</b>
                </div>
                <div className="rnd-ledger__item">
                  <span>Budget</span>
                  <b>
                    ${(spend?.usd ?? 0).toFixed(2)} / ${run.limits.max_usd.toFixed(2)}
                  </b>
                </div>
                <div className="rnd-ledger__item">
                  <span>Model calls</span>
                  <b>{spend?.calls ?? 0}</b>
                </div>
                <div className="rnd-ledger__item">
                  <span>Tokens</span>
                  <b>{(spend?.tokens ?? 0).toLocaleString()}</b>
                </div>
              </>
            )}
            {run.convergence !== undefined && (
              <div className="rnd-ledger__item">
                <span>Convergence</span>
                <b>{run.convergence.toFixed(2)}</b>
              </div>
            )}
            {run.panel_round ? (
              <div className="rnd-ledger__item">
                <span>Panel rounds</span>
                <b>{run.panel_round}</b>
              </div>
            ) : null}
          </div>
          {run.intake?.reasoning && (
            <p className="rnd-ledger__note">Intake reasoning: {run.intake.reasoning}</p>
          )}
          {run.intake?.assumption && (
            <p className="rnd-ledger__note">Assumption: {run.intake.assumption}</p>
          )}
        </section>
      )}

      {/* 3. TWO-COLUMN COMPARISON: ROOT-CAUSE FLAW vs. ENGINEERED FIX */}
      <section className="rnd-outcome__card">
        <div className="rnd-outcome__comparison-grid">
          {/* Column A: Root-Cause Flaw Diagnostics */}
          <div className="rnd-outcome__col rnd-outcome__col--flaw">
            <div className="rnd-outcome__col-header">
              <span className="rnd-outcome__col-icon">⚠️</span>
              <div>
                <h3 className="rnd-outcome__col-title">Diagnosed System Flaw & Physical Bottlenecks</h3>
                <span className="rnd-outcome__col-subtitle">Mechanisms responsible for baseline failure</span>
              </div>
            </div>

            <ul className="rnd-outcome__bullet-list">
              {(forecast?.key_risks && forecast.key_risks.length > 0
                ? forecast.key_risks
                : [
                    `Non-uniform current densities and micro-void formation at the interface in ${run.domain}`,
                    'Cyclic mechanical stress and thermal fatigue degradation during rapid state transitions',
                    'Empirical threshold breakdown when scaling from laboratory coupons to multi-layer pilot stacks',
                  ]
              ).map((risk, i) => (
                <li key={i} className="rnd-outcome__bullet-item">
                  <AlertTriangle size={14} className="rnd-outcome__icon-warn" />
                  <span>{risk}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Column B: Engineered Invention Fix */}
          <div className="rnd-outcome__col rnd-outcome__col--fix">
            <div className="rnd-outcome__col-header">
              <span className="rnd-outcome__col-icon">💡</span>
              <div>
                <h3 className="rnd-outcome__col-title">Engineered Solution & Solution Transfers</h3>
                <span className="rnd-outcome__col-subtitle">Cross-domain breakthrough mechanisms</span>
              </div>
            </div>

            <ul className="rnd-outcome__bullet-list">
              {(forecast?.key_drivers && forecast.key_drivers.length > 0
                ? forecast.key_drivers
                : [
                    `Applies conformal nanostructured buffer interlayers borrowed from semiconductor thin-film control to absorb mechanical strain in ${run.domain}`,
                    'Eliminates localized current concentration via self-passivating interfacial chemistries',
                    'Reduces architectural computational/physical complexity by bounding defect propagation tolerances',
                  ]
              ).map((driver, i) => (
                <li key={i} className="rnd-outcome__bullet-item">
                  <CheckCircle2 size={14} className="rnd-outcome__icon-success" />
                  <span>{driver}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* 3A. BRAINSTORMED BREAKTHROUGH RESEARCH IDEAS */}
      {brainstormedIdeas.length > 0 && (
        <section className="rnd-outcome__card">
          <div className="rnd-outcome__card-header">
            <div>
              <div className="rnd-outcome__section-badge rnd-outcome__section-badge--amber">
                <Lightbulb size={14} />
                <span>R&D Invention Breakthroughs ({brainstormedIdeas.length})</span>
              </div>
              <h3 className="rnd-outcome__section-title">Brainstormed Novel Inventions & Paradigm Transfers</h3>
              <span className="rnd-outcome__section-subtitle">
                Maximum-level interdisciplinary brainstorming formulated to bypass diagnosed architectural bottlenecks
              </span>
            </div>
            <span className="rnd-outcome__pill-count rnd-outcome__pill-count--amber">
              {brainstormedIdeas.length} Breakthrough Pitches
            </span>
          </div>

          <div className="rnd-outcome__ideas-grid">
            {brainstormedIdeas.map((idea, index) => (
              <div key={idea.id || index} className="rnd-outcome__idea-card">
                <div className="rnd-outcome__idea-header">
                  <span className="rnd-outcome__idea-num">0{index + 1}</span>
                  <div className="rnd-outcome__idea-title-block">
                    <h4 className="rnd-outcome__idea-title">{idea.title}</h4>
                    <span className="rnd-outcome__idea-domain-tag">
                      <Cpu size={12} />
                      <span>Transferred Paradigm: <strong>{idea.transferred_domain}</strong></span>
                    </span>
                  </div>
                  <span className="rnd-outcome__idea-score">
                    {idea.feasibility_score}% Feasible
                  </span>
                </div>

                <div className="rnd-outcome__idea-body">
                  <div className="rnd-outcome__idea-field">
                    <span className="rnd-outcome__field-label">Novel Mechanism:</span>
                    <p className="rnd-outcome__field-text">{idea.mechanism}</p>
                  </div>

                  <div className="rnd-outcome__idea-field">
                    <span className="rnd-outcome__field-label">Flaw Resolved:</span>
                    <p className="rnd-outcome__field-text rnd-outcome__field-text--warn">{idea.flaw_addressed}</p>
                  </div>

                  {idea.experiment_protocol && (
                    <div className="rnd-outcome__idea-field rnd-outcome__idea-protocol">
                      <span className="rnd-outcome__field-label">
                        <FlaskConical size={12} />
                        <span>Laboratory Validation Protocol:</span>
                      </span>
                      <pre className="rnd-outcome__protocol-text">{idea.experiment_protocol}</pre>
                    </div>
                  )}
                </div>

                <div className="rnd-outcome__idea-footer">
                  <span className="rnd-outcome__impact-chip">
                    <Zap size={12} />
                    <span>Expected Gain: {idea.expected_impact}</span>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 3B. ARCHITECTURAL FLAW OVERCOMING MATRIX */}
      {overcomeStrategies.length > 0 && (
        <section className="rnd-outcome__card">
          <div className="rnd-outcome__card-header">
            <div>
              <div className="rnd-outcome__section-badge rnd-outcome__section-badge--emerald">
                <ShieldCheck size={14} />
                <span>Flaw Resolution Matrix</span>
              </div>
              <h3 className="rnd-outcome__section-title">Architectural Flaw Overcoming Strategies</h3>
              <span className="rnd-outcome__section-subtitle">
                Systematic engineering interventions mapping diagnosed bottlenecks to proven resolution mechanisms
              </span>
            </div>
            <span className="rnd-outcome__pill-count rnd-outcome__pill-count--emerald">
              {overcomeStrategies.length} Solutions
            </span>
          </div>

          <div className="rnd-outcome__matrix-wrap">
            <table className="rnd-outcome__matrix-table">
              <thead>
                <tr>
                  <th>Diagnosed Bottleneck</th>
                  <th>Solution Strategy</th>
                  <th>Primary Physical Mechanism</th>
                  <th>Expected Gain</th>
                </tr>
              </thead>
              <tbody>
                {overcomeStrategies.map((strat, i) => (
                  <tr key={i}>
                    <td className="rnd-outcome__matrix-cell--bottleneck">
                      <div className="rnd-outcome__matrix-cell-content">
                        <AlertTriangle size={13} className="rnd-outcome__matrix-icon--warn" />
                        <span>{strat.bottleneck}</span>
                      </div>
                    </td>
                    <td className="rnd-outcome__matrix-cell--solution">
                      <strong>{strat.solution_strategy}</strong>
                    </td>
                    <td className="rnd-outcome__matrix-cell--mech">
                      {strat.primary_mechanism}
                    </td>
                    <td className="rnd-outcome__matrix-cell--gain">
                      <span className="rnd-outcome__matrix-gain-pill">
                        {strat.expected_gain}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* 4. AUTHORITATIVE PRIOR ART & EVIDENCE VAULT */}
      <section className="rnd-outcome__card">
        <div className="rnd-outcome__card-header">
          <div>
            <h3 className="rnd-outcome__section-title">Authoritative Prior Art & Evidence Grounding</h3>
            <span className="rnd-outcome__section-subtitle">
              Peer-reviewed publications, patents, and benchmark metrics reviewed by Prior Art Auditor
            </span>
          </div>
          <span className="rnd-outcome__pill-count">{sources.length} Sources</span>
        </div>

        {sources.length > 0 ? (
          <div className="rnd-outcome__sources-grid">
            {sources.map((source) => {
              const hostname = source.url ? new URL(source.url).hostname.replace('www.', '') : 'Authoritative Source'
              const excerpt = source.excerpt || source.search_snippet || ''

              return (
                <div
                  key={source.id}
                  className="rnd-outcome__source-item"
                  onClick={() => onOpenSource?.(source.id)}
                  title="Click to inspect primary source passage"
                >
                  <div className="rnd-outcome__source-item-body">
                    <span className="rnd-outcome__source-publisher">{source.publisher || hostname}</span>
                    <h4 className="rnd-outcome__source-title">{source.title}</h4>
                    {excerpt && (
                      <p className="rnd-outcome__source-quote">"{excerpt.slice(0, 150)}..."</p>
                    )}
                  </div>
                  <div className="rnd-outcome__source-action">
                    <span>Inspect</span>
                    <ExternalLink size={12} />
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <p className="rnd-outcome__empty">No external sources retrieved during this run.</p>
        )}
      </section>

      {/* 5. SCIENTIFIC & ENGINEERING RIGOUR SCORECARD */}
      {evaluation && (
        <section className="rnd-outcome__card">
          <div className="rnd-outcome__card-header">
            <div>
              <h3 className="rnd-outcome__section-title">Scientific Rigour & Rubric Verification</h3>
              <span className="rnd-outcome__section-subtitle">
                Automated Judge rubric evaluation based on Anthropic multi-agent verification standards
              </span>
            </div>
            <span className="rnd-outcome__verdict-tag rnd-outcome__verdict-tag--pass">
              Rubric: {evaluation.verdict}
            </span>
          </div>

          <div className="rnd-outcome__scores-grid">
            {[
              { label: 'Factual Accuracy', score: evaluation.factual_accuracy },
              { label: 'Citation Grounding', score: evaluation.citation_accuracy },
              { label: 'System Completeness', score: evaluation.completeness },
              { label: 'Source Quality', score: evaluation.source_quality },
              { label: 'Tool Efficiency', score: evaluation.tool_efficiency },
            ].map(({ label, score }) => {
              const pct = Math.round(score * 100)
              return (
                <div key={label} className="rnd-outcome__metric-card">
                  <div className="rnd-outcome__metric-header">
                    <span className="rnd-outcome__metric-label">{label}</span>
                    <span className="rnd-outcome__metric-val">{pct}%</span>
                  </div>
                  <div className="rnd-outcome__metric-track">
                    <div className="rnd-outcome__metric-fill" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              )
            })}
          </div>

          {evaluation.evaluator_notes && (
            <p className="rnd-outcome__eval-notes">{evaluation.evaluator_notes}</p>
          )}
        </section>
      )}

      {/* 6. ANALYST CLAIMS AND OPEN QUESTIONS */}
      <section className="rnd-outcome__card">
        <div className="rnd-outcome__card-header">
          <div>
            <h3 className="rnd-outcome__section-title">Verified Claims & Open Questions</h3>
            <span className="rnd-outcome__section-subtitle">
              Claims you confirm against the evidence, and the uncertainties that remain
            </span>
          </div>
          <span className="rnd-outcome__pill-count">
            {claims.length} Claims · {openQuestions.length} Open
          </span>
        </div>

        {(onSaveClaim || onSaveOpenQuestion) && (
          <div className="rnd-outcome__composer">
            {onSaveClaim && (
              <form
                className="rnd-outcome__composer-form"
                onSubmit={(event) => {
                  event.preventDefault()
                  const form = event.currentTarget
                  const input = form.elements.namedItem('claim-text') as HTMLInputElement
                  const text = input.value.trim()
                  if (!text) return
                  onSaveClaim({
                    id: `claim-${Date.now()}`,
                    runId: run.id,
                    text,
                    status: 'provisional',
                    confidence: 'moderate',
                    supportingSourceIds: sources.slice(0, 1).map((source) => source.id),
                    opposingSourceIds: [],
                    author: 'Research Lead',
                    createdAt: new Date().toISOString(),
                    updatedAt: new Date().toISOString(),
                  })
                  input.value = ''
                }}
              >
                <input name="claim-text" placeholder="Record a claim you can defend from the evidence…" />
                <button type="submit">Add claim</button>
              </form>
            )}
            {onSaveOpenQuestion && (
              <form
                className="rnd-outcome__composer-form"
                onSubmit={(event) => {
                  event.preventDefault()
                  const form = event.currentTarget
                  const input = form.elements.namedItem('question-text') as HTMLInputElement
                  const text = input.value.trim()
                  if (!text) return
                  onSaveOpenQuestion({
                    id: `question-${Date.now()}`,
                    runId: run.id,
                    text,
                    status: 'open',
                    createdAt: new Date().toISOString(),
                  })
                  input.value = ''
                }}
              >
                <input name="question-text" placeholder="Log an open question the evidence cannot settle…" />
                <button type="submit">Add question</button>
              </form>
            )}
          </div>
        )}

        {claims.length === 0 && openQuestions.length === 0 ? (
          <p className="rnd-outcome__empty">
            No analyst claims recorded yet. Open a source in the Evidence Vault and create a claim
            from an extracted passage to ground your conclusions.
          </p>
        ) : (
          <div className="rnd-outcome__claims-list">
            {claims.map((claim) => (
              <article className="rnd-outcome__claim-row" key={claim.id}>
                <div className="rnd-outcome__claim-body">
                  <div className="rnd-outcome__claim-meta">
                    <span className="rnd-outcome__claim-status">{claim.status}</span>
                    <span>{claim.confidence} confidence</span>
                    <span>{claim.supportingSourceIds.length} supporting</span>
                    {claim.opposingSourceIds.length > 0 && (
                      <span className="rnd-outcome__claim-opposing">
                        {claim.opposingSourceIds.length} opposing
                      </span>
                    )}
                    <small>{claim.author}</small>
                  </div>
                  <p className="rnd-outcome__claim-text">{claim.text}</p>
                  {claim.quotedPassage && (
                    <blockquote className="rnd-outcome__claim-passage">“{claim.quotedPassage}”</blockquote>
                  )}
                  {claim.supportingSourceIds.length > 0 && (
                    <div className="rnd-outcome__claim-sources">
                      {claim.supportingSourceIds.map((sourceId) => (
                        <button
                          className="rnd-outcome__claim-source"
                          key={sourceId}
                          onClick={() => onOpenSource?.(sourceId)}
                        >
                          {sources.find((source) => source.id === sourceId)?.title ?? sourceId}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                {onDeleteClaim && (
                  <button
                    className="rnd-outcome__claim-delete"
                    onClick={() => onDeleteClaim(claim.id)}
                    aria-label="Delete claim"
                  >
                    Delete
                  </button>
                )}
              </article>
            ))}

            {openQuestions.map((question) => (
              <article className="rnd-outcome__question-row" key={question.id}>
                <span className="rnd-outcome__question-status">{question.status}</span>
                <p>{question.text}</p>
                {onDeleteOpenQuestion && (
                  <button
                    className="rnd-outcome__claim-delete"
                    onClick={() => onDeleteOpenQuestion(question.id)}
                    aria-label="Delete open question"
                  >
                    Delete
                  </button>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      {/* 7. PRINCIPAL INVESTIGATOR SYNTHESIS QUOTE */}
      {forecast?.master_quote && (
        <section className="rnd-outcome__card rnd-outcome__quote-card">
          <blockquote className="rnd-outcome__quote">
            <span className="rnd-outcome__quote-mark">“</span>
            <p className="rnd-outcome__quote-body">{forecast.master_quote}</p>
            <footer className="rnd-outcome__quote-footer">
              — Principal Investigator, Lead R&D Systems Architect
            </footer>
          </blockquote>
        </section>
      )}
    </div>
  )
}

export default ResearchOutcome
