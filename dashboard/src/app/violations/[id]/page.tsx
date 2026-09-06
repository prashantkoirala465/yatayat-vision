"use client";

import { useEffect, useState } from "react";
import { use } from "react";
import Link from "next/link";
import { evidenceImageUrl, getViolation, plateCropUrl, updateViolation, type Violation } from "@/lib/api";

export default function ViolationDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const violationId = Number(id);

  const [violation, setViolation] = useState<Violation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [plateDraft, setPlateDraft] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getViolation(violationId)
      .then((v) => {
        setViolation(v);
        setPlateDraft(v.plate_text ?? "");
      })
      .catch((err) => setError(String(err)));
  }, [violationId]);

  async function save(update: { plate_text?: string | null; status?: string }) {
    setSaving(true);
    try {
      const updated = await updateViolation(violationId, update);
      setViolation(updated);
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

  if (error) return <p className="mx-auto max-w-3xl px-6 py-10 text-sm text-red-400">{error}</p>;
  if (!violation) return <p className="mx-auto max-w-3xl px-6 py-10 text-sm text-muted">Loading…</p>;

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <Link href="/" className="text-sm text-muted hover:text-zinc-50">
        &larr; all violations
      </Link>

      <h1 className="mt-4 text-2xl font-semibold text-zinc-50">
        Violation #{violation.id} — {violation.speed_kmh.toFixed(1)} km/h
      </h1>
      <p className="mt-1 text-sm text-muted">
        {violation.source_id} · track {violation.track_id} · {new Date(violation.detected_at).toLocaleString()}
      </p>

      <div className="mt-6 grid grid-cols-2 gap-4">
        <div>
          <p className="mb-1 text-xs text-muted">Evidence frame</p>
          {/* eslint-disable-next-line @next/next/no-img-element -- served by the API, not a static/optimizable asset */}
          <img src={evidenceImageUrl(violation.id)} alt="Evidence frame" className="w-full rounded border border-line" />
        </div>
        <div>
          <p className="mb-1 text-xs text-muted">Plate crop</p>
          {violation.plate_crop_path ? (
            // eslint-disable-next-line @next/next/no-img-element -- served by the API, not a static/optimizable asset
            <img src={plateCropUrl(violation.id)} alt="Plate crop" className="rounded border border-line" />
          ) : (
            <p className="text-sm text-muted">No plate detected on this frame.</p>
          )}
        </div>
      </div>

      <div className="mt-6 flex flex-wrap items-end gap-3 rounded-lg border border-line bg-zinc-900/40 p-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted">Plate text</label>
          <input
            value={plateDraft}
            onChange={(e) => setPlateDraft(e.target.value)}
            placeholder="unreadable"
            className="w-48 rounded border border-line bg-transparent px-2 py-1 text-sm text-zinc-50"
          />
        </div>
        <button
          disabled={saving}
          onClick={() => save({ plate_text: plateDraft.trim() === "" ? null : plateDraft.trim() })}
          className="rounded bg-zinc-50 px-4 py-1.5 text-sm font-medium text-black disabled:opacity-40"
        >
          Save correction
        </button>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted">Status</label>
          <select
            value={violation.status}
            onChange={(e) => save({ status: e.target.value })}
            disabled={saving}
            className="rounded border border-line bg-transparent px-2 py-1 text-sm text-zinc-50"
          >
            <option value="pending_review">pending_review</option>
            <option value="confirmed">confirmed</option>
            <option value="rejected">rejected</option>
          </select>
        </div>
      </div>
    </div>
  );
}
