export type Source = {
  id: string
  title: string
  url: string
  excerpt: string
  content?: string
  search_snippet?: string
  publisher?: string
  published_at?: string | null
  retrieved_at?: string
  query?: string
  provider?: string
}

export type ReviewStatus = 'reviewed' | 'excluded' | 'disputed'

export type SourceReview = {
  status: ReviewStatus
  note?: string
  highlightedPassage?: string
  updatedAt?: string
}

export type ClaimStatus = 'supported' | 'contested' | 'provisional'
export type ConfidenceLevel = 'high' | 'moderate' | 'low'

export type Claim = {
  id: string
  runId: string
  text: string
  status: ClaimStatus
  confidence: ConfidenceLevel
  supportingSourceIds: string[]
  opposingSourceIds: string[]
  quotedPassage?: string
  author: string
  createdAt: string
  updatedAt?: string
}

export type OpenQuestion = {
  id: string
  runId: string
  text: string
  status: 'open' | 'investigating' | 'addressed'
  notes?: string
  createdAt: string
}

export type ComplexityLevel = 'simple_fact_finding' | 'comparative_analysis' | 'multi_faceted_research'

export type SubagentTask = {
  subagent_id: string
  role: string
  focus: string
  boundaries: string
  search_strategy: string
  broad_query: string
  narrow_query_templates: string[]
}

export type ResearchPlan = {
  complexity: ComplexityLevel
  rationale: string
  subagent_count: number
  tool_budget_per_agent: number
  objectives: string[]
  subtasks: SubagentTask[]
}

export type InterleavedThinkingStep = {
  step_index: number
  action: string
  scratchpad: string
  decision: string
}

export type SubagentExecution = {
  subagent_id: string
  role: string
  status: string
  queries_executed: string[]
  sources_found: number
  thinking_trace: InterleavedThinkingStep[]
  key_findings: string[]
}

export type CitationAttribution = {
  claim_id: string
  source_id: string
  source_title: string
  source_url: string
  exact_passage: string
  attribution_type: string
  match_confidence: number
}

export type JudgeRubricScorecard = {
  factual_accuracy: number
  citation_accuracy: number
  completeness: number
  source_quality: number
  tool_efficiency: number
  overall_score: number
  verdict: 'PASS' | 'NEEDS_EVIDENCE'
  evaluator_notes?: string
}

export type BrainstormedIdea = {
  id: string
  title: string
  transferred_domain: string
  mechanism: string
  flaw_addressed: string
  feasibility_score: number
  experiment_protocol: string
  expected_impact: string
}

export type FlawOvercomeStrategy = {
  bottleneck: string
  solution_strategy: string
  primary_mechanism: string
  expected_gain: string
}

export type ArchitecturePrimitive = {
  name: string
  category: string
  mechanism: string
  role_in_system: string
  bottleneck_equation_or_limit: string
}

export type CoreArchitectureModel = {
  system_name: string
  domain: string
  foundational_summary: string
  primitives: ArchitecturePrimitive[]
  flaw_hotspot: string
  governing_equation?: string
}

export type ForecastModel = {
  verdict: string
  headline: string
  confidence_score: number
  confidence_label: string
  confidence_summary: string
  key_drivers: string[]
  key_risks: string[]
  master_quote: string
  brainstormed_ideas?: BrainstormedIdea[]
  overcome_strategies?: FlawOvercomeStrategy[]
  core_architecture?: CoreArchitectureModel
}

export type DisagreementItem = {
  id: string
  speaker_a: string
  role_a: string
  avatar_a: string
  stance_a: string
  speaker_b: string
  role_b: string
  avatar_b: string
  stance_b: string
}

export type ProjectionPoint = {
  year: number
  renewables: number
  fossil: number
  nuclear: number
}

export type ActiveSpeaker = {
  id: string
  name: string
  role?: string
  speech: string
  stage?: string
}

export type Run = {
  id: string
  domain: string
  question: string
  status: 'running' | 'completed' | 'needs_evidence' | 'failed' | 'awaiting_input' | 'paused' | 'cancelled'
  round: number
  attempt?: number
  max_attempts?: number
  current_stage: string
  created_at?: string
  updated_at: string
  mode?: RunMode
  limits?: RunLimits
  spend?: RunSpend
  claims?: Claim[]
  sources?: Source[]
  audit?: { stage: string; event: string; detail: string }[]
  plan?: ResearchPlan
  subagent_executions?: SubagentExecution[]
  citation_verifications?: CitationAttribution[]
  evaluation?: JudgeRubricScorecard
  forecast?: ForecastModel
  disagreements?: DisagreementItem[]
  projections?: ProjectionPoint[]
  brainstormed_ideas?: BrainstormedIdea[]
  overcome_strategies?: FlawOvercomeStrategy[]
  active_speaker?: ActiveSpeaker
  core_architecture?: CoreArchitectureModel
  attempt_history?: { attempt: number; max_attempts: number; status: string; convergence_score: number }[]
  // PRD-aligned state
  intake?: IntakeClassification
  clarifying_questions?: ClarifyingQuestion[]
  scope?: DiscoveryScope
  pain_points?: PainPoint[]
  transcript?: PanelTurn[]
  panel_round?: number
  convergence?: number
  problem_candidates?: ProblemCandidate[]
  selected_problem_ids?: string[]
  ideas?: ResearchIdea[]
  ranked_ideas?: ResearchIdea[]
  validation_results?: ValidationResult[]
  checkpoints?: CheckpointRequest[]
  evidence?: { id: string; claim: string; source_url: string; quality: QualityGrade; verified: boolean }[]
  gaps?: { id: string; description: string; kind: string; evidence_ids: string[] }[]
}

export type ExtractionFilter = 'all' | 'full-text' | 'snippet-only'
export type DateFilter = 'all' | 'dated' | 'undated'
export type SortOption = 'retrieved' | 'title' | 'publisher' | 'date'

export type ActiveWorkspaceView = 'meeting' | 'orchestrator' | 'outcome' | 'vault' | 'observability'

export type AgentRole = 'orchestrator' | 'research' | 'planning' | 'data' | 'review' | 'synthesis'

export type LiveProgressEvent = {
  type: string
  domain?: string
  question?: string
  query?: string
  title?: string
  url?: string
  publisher?: string
  result_count?: number
  source_count?: number
  extracted?: boolean
  published_at?: string | null
  error?: string
  detail?: string
  run?: Run
  subagent_id?: string
  role?: string
  focus?: string
  boundaries?: string
  complexity?: ComplexityLevel
  subagent_count?: number
  rationale?: string
  objectives?: string[]
  subtasks?: SubagentTask[]
  action?: string
  scratchpad?: string
  decision?: string
  metric_name?: string
  source_title?: string
  source_url?: string
  attribution_type?: string
  match_confidence?: number
  attempt_focus?: string
  claim_id?: string
  source_id?: string
  passage?: string
  evaluation?: JudgeRubricScorecard
  attempt?: number
  max_attempts?: number
  disagreements?: DisagreementItem[]
  projections?: ProjectionPoint[]
  forecast?: ForecastModel
  brainstormed_ideas?: BrainstormedIdea[]
  overcome_strategies?: FlawOvercomeStrategy[]
  idea?: BrainstormedIdea
  speaker_id?: string
  speaker_name?: string
  speech?: string
  stage?: string
  active_speaker?: ActiveSpeaker
  core_architecture?: CoreArchitectureModel
  // PRD-aligned live events
  mode?: string
  spend?: RunSpend
  limits?: RunLimits
  round?: number
  questions?: ClarifyingQuestion[]
  candidates?: ProblemCandidate[]
  ranked_ideas?: ResearchIdea[]
  panel_turn?: PanelTurn
  kind?: string
}

export type ToastMessage = {
  id: string
  title: string
  detail?: string
  type?: 'success' | 'info' | 'warning'
}

// --- PRD-aligned domain types (HLD section 13) -------------------------------

export type RunMode = 'problem' | 'topic' | 'ambiguous'
export type Depth = 'quick' | 'standard' | 'deep'
export type ValidationLevel = 'L0' | 'L1' | 'L2' | 'L3'
export type QualityGrade = 'A' | 'B' | 'C' | 'D'
export type IdeaStatus = 'proposed' | 'challenged' | 'killed' | 'validated' | 'shortlisted'
export type PanelStance = 'support' | 'challenge' | 'defend' | 'question' | 'neutral'

export type RunLimits = {
  depth: Depth
  max_usd: number
  max_debate_rounds: number
  max_panel_rounds: number
  max_wall_seconds: number
  max_queries: number
  max_sources: number
}

export type RunSpend = {
  usd: number
  tokens: number
  calls: number
  tool_calls?: number
}

export type IntakeClassification = {
  mode: RunMode
  confidence: number
  reasoning: string
  classified_by: 'model' | 'heuristic'
  problem_statement?: string
  topic?: string
  assumed_mode?: 'problem' | 'topic'
  assumption?: string
}

export type ClarifyingQuestion = {
  id: string
  question: string
  answer: string
}

export type DiscoveryScope = {
  topic: string
  framing: string
  subtopics: string[]
  keywords: string[]
  boundaries: string
  search_queries: string[]
  source_types: string[]
}

export type PainPoint = {
  id: string
  text: string
  cluster: string
  severity: number
  evidence_ids: string[]
  cite_labels: string[]
}

export type PanelTurn = {
  id: string
  round: number
  persona: string
  persona_id: string
  initials: string
  color: string
  position: string
  cites: string[]
  cite_labels: string[]
  evidence_ids: string[]
  challenges: string[]
  stance: PanelStance
  status: 'speaking' | 'done'
  is_moderator?: boolean
}

export type ProblemCandidate = {
  id: string
  statement: string
  why_it_matters: string
  evidence_ids: string[]
  cite_labels: string[]
  severity: number
  tractability: number
  gap_size: number
  cluster: string
  rank?: number
  status: 'candidate' | 'selected' | 'rejected'
  origin: 'discovery' | 'intake'
  score?: number
}

export type ResearchIdea = {
  id: string
  title: string
  operator: string
  description: string
  why_it_should_work: string
  targets: string
  transferred_domain?: string
  evidence_ids: string[]
  status: IdeaStatus
  critiques: unknown[]
  validation_level: ValidationLevel
  next_test: string
  cheapest_test: string
  risks: string[]
  kill_reason?: string | null
  expected_impact?: string
  feasibility?: number
  impact?: number
  novelty?: number
  cost_to_test?: number
  score?: number
  rank?: number
}

export type ValidationResult = {
  idea_id: string
  title: string
  validation_level: ValidationLevel
  rationale: string
  cheapest_test: string
}

export type CheckpointRequest = {
  id: string
  kind: 'problem_selection' | 'gap_review' | 'shortlist' | 'discovery_selection' | 'nudge'
  title: string
  prompt: string
  options: { id: string; label: string; detail?: string }[]
  created_at: string
  resolved: boolean
  decision?: {
    action: string
    selected_ids: string[]
    edits: Record<string, string>
    note: string
    redirect: string
    resolved_at: string
  }
}
