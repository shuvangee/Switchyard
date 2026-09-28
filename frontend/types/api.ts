export type TaskCategory =
  | "extraction"
  | "classification"
  | "summarization"
  | "math"
  | "reasoning"
  | "coding"
  | "debugging"
  | "structured_output";

export type TaskDifficulty = "easy" | "medium" | "hard";

export type EvaluationType = "exact_match" | "classification_label" | "valid_json" | "manual";

export interface BenchmarkTask {
  id: string;
  title: string;
  category: TaskCategory;
  difficulty: TaskDifficulty;
  prompt: string;
  evaluation_type: EvaluationType;
  expected_output: string | null;
  metadata: Record<string, unknown>;
}

export interface ModelPerformanceSummary {
  total_executions: number;
  scored_executions: number;
  correct: number;
  avg_latency_ms: number | null;
  total_cost_usd: number | null;
}

// Real, measured results from the committed 92-task offline Groq
// benchmark — distinct from ModelPerformanceSummary, which reflects
// only this deployment's own live traffic (null on a fresh install).
export interface BenchmarkPerformanceSummary {
  n_executions: number;
  n_graded: number;
  n_correct: number;
  accuracy: number | null;
  avg_latency_ms: number | null;
  nominal_cost_usd: number | null;
}

export interface CategoryAccuracy {
  category: string;
  n_graded: number;
  n_correct: number;
  accuracy: number;
}

export interface ModelConfig {
  id: string;
  provider: string;
  model_id: string;
  display_name: string;
  enabled: boolean;
  input_cost_per_1k: number;
  output_cost_per_1k: number;
  capabilities: Record<string, unknown>;
  performance: ModelPerformanceSummary | null;
  benchmark_performance: BenchmarkPerformanceSummary | null;
  benchmark_performance_by_category: CategoryAccuracy[] | null;
}

export interface CategoryCoverage {
  category: TaskCategory;
  total: number;
  auto_graded: number;
  manual_only: number;
  ungraded: number;
}

export interface EvaluationCoverage {
  total_tasks: number;
  auto_graded: number;
  manual_only: number;
  ungraded: number;
  automated_pct: number | null;
  by_category: CategoryCoverage[];
}

export type ExecutionStatus = "success" | "error";
export type EvaluationStatus = "not_evaluated" | "correct" | "incorrect";
export type RunStatus = "running" | "completed";

export interface ModelExecution {
  id: number;
  task_id: string;
  model_config_id: string;
  provider: string;
  status: ExecutionStatus;
  response_text: string | null;
  error_message: string | null;
  latency_ms: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  estimated_cost_usd: number | null;
  evaluation_status: EvaluationStatus;
  evaluation_detail: string | null;
  started_at: string;
  completed_at: string;
}

export interface ExperimentRunSummary {
  id: string;
  name: string | null;
  status: RunStatus;
  task_count: number;
  model_count: number;
  execution_count: number;
  created_at: string;
  completed_at: string | null;
}

export interface ExperimentRunDetail {
  id: string;
  name: string | null;
  status: RunStatus;
  task_ids: string[];
  model_config_ids: string[];
  created_at: string;
  completed_at: string | null;
  executions: ModelExecution[];
}

export interface CreateExperimentRequest {
  task_ids?: string[];
  category?: TaskCategory;
  model_config_ids: string[];
  name?: string;
}

export type CategorySource = "explicit" | "heuristic";
export type ConfidenceLevel = "high" | "medium" | "low";
export type ValidationStatus = "not_validated" | "passed" | "failed";

// "d2-baseline" (preferred production strategy), "learned-v2" (V3's
// trained escalation classifier - does not currently beat d2-baseline),
// "always-20b" / "always-120b" (fixed single-model baselines, for
// direct comparison), "v2" (rule-based, mock-tier, pre-V3), or
// "learned-v1" (earlier exploratory model, not recommended).
// See docs/case-study/DECISIONS.md (2026-09-24/27).
export type RouterVersion =
  | "d2-baseline"
  | "learned-v2"
  | "always-20b"
  | "always-120b"
  | "v2"
  | "learned-v1";

export interface RouteRequest {
  prompt: string;
  category_hint?: TaskCategory;
  router_version?: RouterVersion;
  // Optional "bring your own key" Groq API key, scoped to this one
  // request. Never stored client-side beyond the form's own state
  // (no localStorage), never persisted server-side, never echoed back.
  groq_api_key?: string;
}

export interface TraceEvent {
  event_type: string;
  detail: string;
  timestamp: string;
}

export interface RequestLog {
  id: string;
  prompt: string;
  category: TaskCategory;
  category_source: CategorySource;
  difficulty: TaskDifficulty;
  structured_output_required: boolean;
  estimated_input_tokens: number;
  confidence: ConfidenceLevel;
  initial_model_config_id: string;
  selected_model_config_id: string;
  selected_provider: string;
  router_version: string;
  rationale: string;
  matched_rule: string | null;
  // A real predict_proba-derived number, only for strategies that have
  // one (learned-v1, learned-v2) - null for deterministic rules (v2,
  // D2), never a fabricated confidence percentage.
  router_score: number | null;
  escalated: boolean;
  attempt_count: number;
  validation_status: ValidationStatus;
  validation_detail: string | null;
  status: ExecutionStatus;
  response_text: string | null;
  error_message: string | null;
  latency_ms: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  estimated_cost_usd: number | null;
  trace_events: TraceEvent[];
  created_at: string;
}

export interface RequestLogSummary {
  id: string;
  prompt_preview: string;
  category: TaskCategory;
  difficulty: TaskDifficulty;
  initial_model_config_id: string;
  selected_model_config_id: string;
  selected_provider: string;
  router_version: string;
  escalated: boolean;
  status: ExecutionStatus;
  validation_status: ValidationStatus;
  latency_ms: number | null;
  estimated_cost_usd: number | null;
  created_at: string;
}

export interface RoutingAnalytics {
  total_requests: number;
  initial_model_counts: Record<string, number>;
  final_model_counts: Record<string, number>;
  escalation_count: number;
  escalation_rate: number | null;
  provider_error_count: number;
  avg_latency_ms: number | null;
  total_cost_usd: number | null;
  validation_passed: number;
  validation_failed: number;
  validation_not_validated: number;
}

export interface RouterStrategyMetrics {
  strategy: string;
  accuracy: number;
  correct: number;
  n: number;
  pct_20b: number;
  pct_120b: number;
  nominal_cost_usd: number;
  avg_latency_ms: number;
  is_out_of_sample: boolean;
  is_theoretical_upper_bound: boolean;
}

export interface RouterComparison {
  evaluation_method: string;
  n_evaluated_tasks: number;
  trained_at: string;
  chosen_algorithm: string;
  chosen_algorithm_reason: string;
  learned_beats_d2: boolean;
  learned_beats_always_120b: boolean;
  strategies: RouterStrategyMetrics[];
}
