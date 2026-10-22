import React, { useState, type FormEvent, useEffect } from 'react'
import {
  Sparkles,
  Loader2,
  Atom,
  Clock,
  ArrowRight,
  ChevronRight,
  Cpu,
  ChevronDown,
  ChevronUp,
  Key,
} from 'lucide-react'
import './ResearchInput.css'

export type PastRunSummary = {
  id: string
  domain: string
  question: string
  status: string
  updated_at: string
}

export type ModelConfig = {
  model_provider?: string
  model_name?: string
  api_key?: string
}

export type IntakeMode = 'auto' | 'problem' | 'topic'
export type RunDepth = 'quick' | 'standard' | 'deep'

export type RunConfig = ModelConfig & {
  mode?: IntakeMode
  depth?: RunDepth
  max_usd?: number
}

type ResearchInputProps = {
  onSubmit: (domain: string, question: string, modelConfig?: RunConfig) => void
  pastRuns?: PastRunSummary[]
  onSelectRun?: (runId: string) => void
  isSubmitting?: boolean
  /** The provider the server is configured with, so the UI can preselect it. */
  serverModel?: { provider: string; default_model?: string; base_url?: string }
}

const PROVIDERS = [
  { id: 'nvidia', name: 'NVIDIA NIM (Default)', defaultModel: 'meta/llama-3.3-70b-instruct', icon: '⚡', hint: 'integrate.api.nvidia.com' },
  { id: 'groq', name: 'Groq Cloud', defaultModel: 'llama-3.3-70b-versatile', icon: '🚀', hint: 'api.groq.com' },
  { id: 'anthropic', name: 'Anthropic Claude', defaultModel: 'claude-3-5-sonnet-20241022', icon: '🟣', hint: 'api.anthropic.com' },
  { id: 'gemini', name: 'Google Gemini', defaultModel: 'gemini-2.0-flash', icon: '✨', hint: 'generativelanguage.googleapis.com' },
  { id: 'openai', name: 'OpenAI', defaultModel: 'gpt-4o-mini', icon: '🟢', hint: 'api.openai.com' },
  { id: 'ollama', name: 'Ollama (Local)', defaultModel: 'llama3.1', icon: '🦙', hint: 'localhost:11434' },
  { id: 'custom', name: 'Custom Endpoint', defaultModel: '', icon: '⚙️', hint: 'OpenAI-compatible URL' },
]
function formatRelativeTime(isoString: string): string {
  try {
    const date = new Date(isoString)
    const diffMs = Math.max(0, Date.now() - date.getTime())
    const diffMins = Math.floor(diffMs / 60000)
    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    return date.toLocaleDateString()
  } catch {
    return ''
  }
}

export const ResearchInput: React.FC<ResearchInputProps> = ({
  onSubmit,
  pastRuns = [],
  onSelectRun,
  isSubmitting = false,
  serverModel,
}) => {
  const [domain, setDomain] = useState('')
  const [question, setQuestion] = useState('')
  const [showEngineSettings, setShowEngineSettings] = useState(false)
  const [providerOverride, setProviderOverride] = useState<string | null>(null)
  const [modelNameOverride, setModelNameOverride] = useState<string | null>(null)
  const [apiKey, setApiKey] = useState('')
  const [mode, setMode] = useState<IntakeMode>('auto')
  const [depth, setDepth] = useState<RunDepth>('standard')
  const [maxUsd, setMaxUsd] = useState(5)

  // Follow the server's configured provider. The UI used to hardcode NVIDIA,
  // which overrode a locally configured model and sent every request to a
  // hosted provider the user may have no key for. An explicit pick wins.
  const serverProvider = serverModel?.provider || ''
  const selectedProvider = providerOverride ?? serverProvider ?? 'nvidia'
  const serverModelName = serverModel?.default_model || ''
  const customModel = modelNameOverride ?? serverModelName

  const handleProviderChange = (providerId: string) => {
    setProviderOverride(providerId)
    const match = PROVIDERS.find((p) => p.id === providerId)
    if (match && match.defaultModel) {
      setModelNameOverride(match.defaultModel)
    }
  }

  const canSubmit = domain.trim() !== '' && question.trim() !== '' && !isSubmitting

  const buildConfig = (): RunConfig => ({
    // Only send what the user actually chose. Sending the server's own
    // provider and model back would be harmless, but sending a provider
    // default from a different list would override the server's routing.
    model_provider: providerOverride ?? undefined,
    model_name: modelNameOverride?.trim() || undefined,
    api_key: apiKey.trim() || undefined,
    mode,
    depth,
    max_usd: maxUsd,
  })

  const handleSubmit = (e?: FormEvent) => {
    if (e) e.preventDefault()
    if (!canSubmit) return
    onSubmit(domain.trim(), question.trim(), buildConfig())
  }

  // Keyboard shortcut: Cmd + Enter or Ctrl + Enter
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        if (domain.trim() && question.trim() && !isSubmitting) {
          onSubmit(domain.trim(), question.trim(), {
            model_provider: providerOverride ?? undefined,
            model_name: modelNameOverride?.trim() || undefined,
            api_key: apiKey.trim() || undefined,
            mode,
            depth,
            max_usd: maxUsd,
          })
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [domain, question, isSubmitting, onSubmit, providerOverride, modelNameOverride, apiKey, mode, depth, maxUsd])

  const benchmarkPresets = [
    {
      domain: 'Solid-State Battery Anodes',
      question: 'What interface architecture eliminates dendritic lithium micro-shorts across solid ceramic electrolytes while preserving ionic conductivity?',
      badge: 'Energy Storage',
      icon: '⚡',
    },
    {
      domain: 'LLM KV-Cache Compression',
      question: 'How can we achieve sub-quadratic attention complexity for million-token context without losing needle-in-haystack recall accuracy?',
      badge: 'AI Architecture',
      icon: '🧠',
    },
    {
      domain: 'Compact Fusion Tokamaks',
      question: 'What cryogenic stabilization architecture mitigates high-temperature superconducting magnet quenching under rapid plasma turbulence?',
      badge: 'Deep Tech',
      icon: '⚛️',
    },
  ]

  return (
    <div className="rnd-studio">
      {/* Top Header Bar */}
      <header className="rnd-studio__topbar">
        <div className="rnd-studio__brand">
          <div className="rnd-studio__logo">
            <Atom size={18} />
          </div>
          <span className="rnd-studio__title">ForesightForge</span>
          <span className="rnd-studio__badge">R&D Council v2.5</span>
        </div>
        <div className="rnd-studio__status-pill">
          <span className="rnd-studio__status-dot" />
          <span>6 Fellow Agents Active</span>
        </div>
      </header>

      {/* Main Studio Content */}
      <main className="rnd-studio__main">
        <div className="rnd-studio__hero">
          <h1 className="rnd-studio__headline">Autonomous R&D Invention Studio</h1>
          <p className="rnd-studio__subheadline">
            Deconstruct complex system flaws, cross-pollinate breakthrough mechanisms from adjacent sciences, and synthesize verified engineering solutions.
          </p>
        </div>

        {/* Input Card */}
        <form className="rnd-studio__form" onSubmit={handleSubmit}>
          <div className="rnd-studio__modes" role="radiogroup" aria-label="Intake mode">
            {(
              [
                { id: 'auto', label: 'Auto-detect', hint: 'The council classifies your input' },
                { id: 'problem', label: 'Problem mode', hint: 'I have a specific bottleneck' },
                { id: 'topic', label: 'Topic Discovery', hint: 'Show me what is worth solving' },
              ] as { id: IntakeMode; label: string; hint: string }[]
            ).map((option) => (
              <button
                key={option.id}
                type="button"
                role="radio"
                aria-checked={mode === option.id}
                className={`rnd-studio__mode ${mode === option.id ? 'rnd-studio__mode--active' : ''}`}
                onClick={() => setMode(option.id)}
                disabled={isSubmitting}
              >
                <strong>{option.label}</strong>
                <small>{option.hint}</small>
              </button>
            ))}
          </div>

          <div className="rnd-studio__field">
            <div className="rnd-studio__label-row">
              <label htmlFor="rnd-domain" className="rnd-studio__label">
                System or Scientific Domain
              </label>
              <span className="rnd-studio__hint">e.g. Solid-State Electrolytes, Neuromorphic Photonics</span>
            </div>
            <input
              id="rnd-domain"
              type="text"
              className="rnd-studio__input"
              placeholder="Enter target technology domain..."
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              disabled={isSubmitting}
            />
          </div>

          <div className="rnd-studio__field">
            <div className="rnd-studio__label-row">
              <label htmlFor="rnd-question" className="rnd-studio__label">
                Architectural Bottleneck or Invention Goal
              </label>
              <span className="rnd-studio__hint">Shortcut: ⌘ + Enter</span>
            </div>
            <textarea
              id="rnd-question"
              className="rnd-studio__textarea"
              placeholder="Describe the architectural flaw, physical limit, or target breakthrough to solve..."
              rows={3}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={isSubmitting}
            />
          </div>

          {/* Benchmark Preset Selectors */}
          <div className="rnd-studio__benchmarks">
            <span className="rnd-studio__benchmarks-title">Load an R&D benchmark:</span>
            <div className="rnd-studio__presets-grid">
              {benchmarkPresets.map((preset, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="rnd-studio__preset-btn"
                  onClick={() => {
                    setDomain(preset.domain)
                    setQuestion(preset.question)
                  }}
                  disabled={isSubmitting}
                >
                  <span className="rnd-studio__preset-icon">{preset.icon}</span>
                  <div className="rnd-studio__preset-text">
                    <span className="rnd-studio__preset-domain">{preset.domain}</span>
                    <span className="rnd-studio__preset-category">{preset.badge}</span>
                  </div>
                  <ArrowRight size={12} className="rnd-studio__preset-arrow" />
                </button>
              ))}
            </div>
          </div>

          {/* LLM Inference Engine Config */}
          <div className="rnd-studio__engine-box">
            <div className="rnd-studio__engine-summary rnd-studio__engine-summary--static">
              <Cpu size={14} className="rnd-studio__engine-icon" />
              <span>Run limits:</span>
              <div className="rnd-studio__depth-pills" role="radiogroup" aria-label="Run depth">
                {(['quick', 'standard', 'deep'] as RunDepth[]).map((level) => (
                  <button
                    key={level}
                    type="button"
                    role="radio"
                    aria-checked={depth === level}
                    className={`rnd-studio__depth-pill ${depth === level ? 'rnd-studio__depth-pill--active' : ''}`}
                    onClick={() => setDepth(level)}
                    disabled={isSubmitting}
                  >
                    {level}
                  </button>
                ))}
              </div>
              <label className="rnd-studio__budget" htmlFor="rnd-budget">
                Budget
                <span className="rnd-studio__budget-input">
                  $<input
                    id="rnd-budget"
                    type="number"
                    min={0.5}
                    max={50}
                    step={0.5}
                    value={maxUsd}
                    onChange={(e) => setMaxUsd(Number(e.target.value) || 0.5)}
                    disabled={isSubmitting}
                  />
                </span>
              </label>
            </div>

            <button
              type="button"
              className="rnd-studio__engine-toggle"
              onClick={() => setShowEngineSettings((prev) => !prev)}
            >
              <div className="rnd-studio__engine-summary">
                <Cpu size={14} className="rnd-studio__engine-icon" />
                <span>Inference Engine:</span>
                <strong className="rnd-studio__engine-active">
                  {PROVIDERS.find((p) => p.id === selectedProvider)?.name || selectedProvider}
                </strong>
                <span className="rnd-studio__engine-model">({customModel || 'Auto'})</span>
              </div>
              <div className="rnd-studio__engine-toggle-icon">
                {showEngineSettings ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </div>
            </button>

            {showEngineSettings && (
              <div className="rnd-studio__engine-panel">
                <div className="rnd-studio__engine-providers">
                  {PROVIDERS.map((provider) => (
                    <button
                      key={provider.id}
                      type="button"
                      className={`rnd-studio__provider-pill ${selectedProvider === provider.id ? 'rnd-studio__provider-pill--active' : ''}`}
                      onClick={() => handleProviderChange(provider.id)}
                    >
                      <span className="rnd-studio__provider-emoji">{provider.icon}</span>
                      <span>{provider.name}</span>
                    </button>
                  ))}
                </div>

                <div className="rnd-studio__engine-inputs">
                  <div className="rnd-studio__engine-field">
                    <label className="rnd-studio__engine-label">Model Identifier</label>
                    <input
                      type="text"
                      className="rnd-studio__engine-input"
                      placeholder="e.g. meta/llama-3.3-70b-instruct"
                      value={customModel}
                      onChange={(e) => setModelNameOverride(e.target.value)}
                      disabled={isSubmitting}
                    />
                  </div>

                  <div className="rnd-studio__engine-field">
                    <div className="rnd-studio__engine-label-row">
                      <label className="rnd-studio__engine-label">
                        <Key size={11} /> API Key Override
                      </label>
                      <span className="rnd-studio__engine-subtext">Optional — defaults to server .env if empty</span>
                    </div>
                    <input
                      type="password"
                      className="rnd-studio__engine-input"
                      placeholder="Enter provider key (e.g. nvapi-...)"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      disabled={isSubmitting}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Submit Action */}
          <div className="rnd-studio__action-bar">
            <span className="rnd-studio__action-note">
              Multidisciplinary council executes multi-attempt parallel investigation
            </span>
            <button
              type="submit"
              className="rnd-studio__submit-btn"
              disabled={!canSubmit}
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={16} className="rnd-studio__spinner" />
                  <span>Council Deliberating...</span>
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  <span>Dispatch R&D Council</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Past Inquiries Vault */}
        {pastRuns && pastRuns.length > 0 && (
          <section className="rnd-studio__history">
            <div className="rnd-studio__history-header">
              <div className="rnd-studio__history-title">
                <Clock size={14} />
                <span>Recent Council Inquiries</span>
              </div>
              <span className="rnd-studio__history-count">{pastRuns.length} completed</span>
            </div>

            <div className="rnd-studio__history-list">
              {pastRuns.slice(0, 4).map((run) => (
                <div
                  key={run.id}
                  className="rnd-studio__history-card"
                  onClick={() => onSelectRun && onSelectRun(run.id)}
                  title="Open this research report"
                >
                  <div className="rnd-studio__history-card-body">
                    <span className="rnd-studio__history-domain">{run.domain}</span>
                    <p className="rnd-studio__history-question">{run.question}</p>
                  </div>
                  <div className="rnd-studio__history-meta">
                    <span className="rnd-studio__history-time">{formatRelativeTime(run.updated_at)}</span>
                    <span className="rnd-studio__history-status">
                      <span className="rnd-studio__status-dot rnd-studio__status-dot--green" />
                      {run.status === 'completed' ? 'Feasible' : run.status}
                    </span>
                    <ChevronRight size={14} className="rnd-studio__history-chevron" />
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

export default ResearchInput
