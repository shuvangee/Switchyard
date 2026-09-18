import type {
  BenchmarkTask,
  CreateExperimentRequest,
  ExperimentRunDetail,
  ExperimentRunSummary,
  ModelConfig,
} from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(response.status, body || `request to ${path} failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export function getBenchmarks(params?: {
  category?: string;
  difficulty?: string;
}): Promise<BenchmarkTask[]> {
  const search = new URLSearchParams();
  if (params?.category) search.set("category", params.category);
  if (params?.difficulty) search.set("difficulty", params.difficulty);
  const qs = search.toString();
  return apiFetch<BenchmarkTask[]>(`/benchmarks${qs ? `?${qs}` : ""}`);
}

export function getBenchmark(id: string): Promise<BenchmarkTask> {
  return apiFetch<BenchmarkTask>(`/benchmarks/${encodeURIComponent(id)}`);
}

export function getModels(): Promise<ModelConfig[]> {
  return apiFetch<ModelConfig[]>("/models");
}

export function getExperiments(): Promise<ExperimentRunSummary[]> {
  return apiFetch<ExperimentRunSummary[]>("/experiments");
}

export function getExperiment(id: string): Promise<ExperimentRunDetail> {
  return apiFetch<ExperimentRunDetail>(`/experiments/${encodeURIComponent(id)}`);
}

export function createExperiment(payload: CreateExperimentRequest): Promise<ExperimentRunDetail> {
  return apiFetch<ExperimentRunDetail>("/experiments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
