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

export interface RouteRequest {
  prompt: string;
  category_hint?: TaskCategory;
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
