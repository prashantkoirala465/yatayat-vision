"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { createJob, getJobStatus, listViolations, type JobStatus, type Violation } from "@/lib/api";

export default function ViolationsPage() {
  const [violations, setViolations] = useState<Violation[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");

  const [file, setFile] = useState<File | null>(null);
  const [speedLimit, setSpeedLimit] = useState(100);
  const [simulateLive, setSimulateLive] = useState(false);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    listViolations(statusFilter || undefined)
      .then(setViolations)
      .catch((err) => setError(String(err)));
  }, [statusFilter]);

  useEffect(refresh, [refresh]);

  // poll job status until it's finished/failed, then refresh the list
  useEffect(() => {
    if (!job || job.status === "finished" || job.status === "failed") return;
    const timer = setTimeout(async () => {
      const updated = await getJobStatus(job.job_id);
      setJob(updated);
      if (updated.status === "finished") refresh();
    }, 3000);
    return () => clearTimeout(timer);
  }, [job, refresh]);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setUploadError(null);
    try {
      const created = await createJob(file, speedLimit, simulateLive);
      setJob({ job_id: created.job_id, status: "queued", result: null, error: null });
    } catch (err) {
      setUploadError(String(err));
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-zinc-50">Speed violations</h1>

      <form onSubmit={handleUpload} className="mt-6 flex flex-wrap items-end gap-3 rounded-lg border border-line bg-zinc-900/40 p-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted">Video</label>
          <input
            type="file"
            accept="video/*"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-sm text-zinc-300"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted">Speed limit (km/h)</label>
          <input
            type="number"
            value={speedLimit}
            onChange={(e) => setSpeedLimit(Number(e.target.value))}
            className="w-24 rounded border border-line bg-transparent px-2 py-1 text-sm text-zinc-50"
          />
        </div>
        <label className="flex items-center gap-1.5 pb-1.5 text-xs text-muted">
          <input
            type="checkbox"
            checked={simulateLive}
            onChange={(e) => setSimulateLive(e.target.checked)}
          />
          simulate live feed
        </label>
        <button
          type="submit"
          disabled={!file}
          className="rounded bg-zinc-50 px-4 py-1.5 text-sm font-medium text-black disabled:opacity-40"
        >
          Process video
        </button>
        {job && (
          <span className="text-sm text-muted">
            job {job.job_id.slice(0, 8)}: {job.status}
            {job.status === "finished" && ` (${job.result} flagged)`}
            {job.status === "failed" && ` - ${job.error}`}
          </span>
        )}
        {uploadError && <span className="text-sm text-red-400">{uploadError}</span>}
      </form>

      <div className="mt-8 flex items-center justify-between">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded border border-line bg-transparent px-2 py-1 text-sm text-zinc-300"
        >
          <option value="">all statuses</option>
          <option value="pending_review">pending_review</option>
          <option value="confirmed">confirmed</option>
          <option value="rejected">rejected</option>
        </select>
        <button onClick={refresh} className="text-sm text-muted hover:text-zinc-50">
          refresh
        </button>
      </div>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <table className="mt-4 w-full text-left text-sm">
        <thead>
          <tr className="border-b border-line text-muted">
            <th className="py-2 pr-4 font-normal">id</th>
            <th className="py-2 pr-4 font-normal">source</th>
            <th className="py-2 pr-4 font-normal">speed</th>
            <th className="py-2 pr-4 font-normal">plate</th>
            <th className="py-2 pr-4 font-normal">status</th>
            <th className="py-2 pr-4 font-normal">detected</th>
          </tr>
        </thead>
        <tbody>
          {violations?.map((v) => (
            <tr key={v.id} className="border-b border-line/50 text-zinc-200 hover:bg-zinc-900/40">
              <td className="py-2 pr-4">
                <Link href={`/violations/${v.id}`} className="text-zinc-50 underline underline-offset-2">
                  {v.id}
                </Link>
              </td>
              <td className="py-2 pr-4">{v.source_id}</td>
              <td className="py-2 pr-4">{v.speed_kmh.toFixed(1)} km/h</td>
              <td className="py-2 pr-4">{v.plate_text ?? <span className="text-muted">unreadable</span>}</td>
              <td className="py-2 pr-4">{v.status}</td>
              <td className="py-2 pr-4 text-muted">{new Date(v.detected_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {violations && violations.length === 0 && <p className="mt-4 text-sm text-muted">No violations yet.</p>}
    </div>
  );
}
