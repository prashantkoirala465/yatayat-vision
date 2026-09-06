const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Violation {
  id: number;
  source_id: string;
  track_id: number;
  detected_at: string;
  speed_kmh: number;
  evidence_frame_path: string;
  plate_crop_path: string | null;
  plate_text: string | null;
  status: string;
}

export interface ViolationUpdate {
  plate_text?: string | null;
  status?: string;
}

export interface JobCreateResponse {
  job_id: string;
  source_id: string;
}

export interface JobStatus {
  job_id: string;
  status: string;
  result: number | null;
  error: string | null;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`request failed (${response.status}): ${await response.text()}`);
  }
  return response.json() as Promise<T>;
}

export async function listViolations(status?: string): Promise<Violation[]> {
  const url = new URL(`${API_URL}/violations`);
  if (status) url.searchParams.set("status", status);
  return handleResponse(await fetch(url));
}

export async function getViolation(id: number): Promise<Violation> {
  return handleResponse(await fetch(`${API_URL}/violations/${id}`));
}

export async function updateViolation(id: number, update: ViolationUpdate): Promise<Violation> {
  return handleResponse(
    await fetch(`${API_URL}/violations/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(update),
    }),
  );
}

export function evidenceImageUrl(id: number): string {
  return `${API_URL}/violations/${id}/evidence`;
}

export function plateCropUrl(id: number): string {
  return `${API_URL}/violations/${id}/plate-crop`;
}

export async function createJob(file: File, speedLimitKmh: number): Promise<JobCreateResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const url = new URL(`${API_URL}/jobs`);
  url.searchParams.set("speed_limit_kmh", String(speedLimitKmh)); // a query param, not a form field - see docs/models
  return handleResponse(await fetch(url, { method: "POST", body: formData }));
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  return handleResponse(await fetch(`${API_URL}/jobs/${jobId}`));
}
