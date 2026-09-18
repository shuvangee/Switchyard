type Tone = "neutral" | "success" | "error" | "warning";

const TONE_CLASS: Record<Tone, string> = {
  neutral: "pill pill-neutral",
  success: "pill pill-success",
  error: "pill pill-error",
  warning: "pill pill-warning",
};

export function Pill({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return <span className={TONE_CLASS[tone]}>{children}</span>;
}

const EXECUTION_STATUS_TONE: Record<string, Tone> = {
  success: "success",
  error: "error",
};

export function ExecutionStatusPill({ status }: { status: string }) {
  return <Pill tone={EXECUTION_STATUS_TONE[status] ?? "neutral"}>{status}</Pill>;
}

const EVALUATION_STATUS_TONE: Record<string, Tone> = {
  correct: "success",
  incorrect: "error",
  not_evaluated: "neutral",
};

export function EvaluationStatusPill({ status }: { status: string }) {
  return <Pill tone={EVALUATION_STATUS_TONE[status] ?? "neutral"}>{status.replace("_", " ")}</Pill>;
}

const RUN_STATUS_TONE: Record<string, Tone> = {
  completed: "success",
  running: "warning",
};

export function RunStatusPill({ status }: { status: string }) {
  return <Pill tone={RUN_STATUS_TONE[status] ?? "neutral"}>{status}</Pill>;
}
