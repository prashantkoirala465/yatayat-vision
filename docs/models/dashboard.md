# Review dashboard (Module 6)

FastAPI now actually serves the pipeline's output: `app/routers/violations.py` (list/detail/patch/evidence-image/plate-crop-image) and `app/routers/jobs.py` (upload a video, enqueue background processing, poll status). The Next.js dashboard (`dashboard/`) is a pure client of this API — no direct DB access, matching Cortex's split.

## Architecture: keeping the API server lean

`app/pipeline.py` (detector + tracker + speed + violation dedup + plate localization/OCR) pulls in the full ML stack — ultralytics, opencv, paddleocr, torch. The API server itself shouldn't need any of that just to list violations or enqueue a job.

RQ's `Queue.enqueue()` accepts a string import path (`"app.tasks.process_video_job"`) instead of a direct function reference — used here specifically so `app/routers/jobs.py`, and therefore `app/main.py`, never imports `app.tasks` (and its heavy transitive dependencies) at all. Verified with a clean venv containing only `requirements.txt`: `from app.main import app` succeeds without `ultralytics`/`opencv`/`paddleocr`/`torch` installed. Only the RQ worker process (a separate `rq worker video_processing` invocation) needs the full stack.

## Real bugs found through actual testing, not assumed away

Two came from genuinely exercising this end-to-end (uploading real files, driving the real UI), not from reasoning about the code in the abstract:

1. **`PATCH` couldn't clear a field to null.** `{"plate_text": null}` silently kept the old value, because a plain `if update.plate_text is not None` check can't distinguish "field omitted from the request" from "field explicitly set to null" — both arrive as Python `None`. Fixed with `update.model_dump(exclude_unset=True)`, which only touches fields actually present in the request body. Caught by manually clearing a test correction via curl and finding the old value was still there; two regression tests now cover it (`test_update_violation_can_explicitly_clear_plate_text`, `test_update_violation_omitted_field_is_untouched`).
2. **`speed_limit_kmh` is a query parameter, not a form field**, in the `POST /jobs` upload endpoint — FastAPI's default for a plain scalar parameter alongside an `UploadFile`. An earlier manual curl test passed it with `-F` (form data) and appeared to work, but only because the value happened to match the endpoint's default (100.0) — it was actually being silently ignored the whole time. Confirmed via the endpoint's own OpenAPI schema (`"in": "query"`), not by assumption. The dashboard's `createJob()` and its test both encode this correctly (query param), with the test's own comment recording why, so this can't silently regress.

A third thing wasn't a bug in application logic but still would have gone unnoticed without actually opening a browser: the violations table's `<td>`/`<th>` cells had no horizontal padding, so columns visually ran together (`"idsource"`, `"111.9 km/hunreadable"`) despite being structurally correct HTML. Only visible in an actual screenshot, not in the component code.

## Verified end-to-end, for real

Full chain, driven exactly as a user would: uploaded `data/samples/vehicles.mp4` through the running dashboard's file input → watched the job move through `queued → started → finished` via the UI's own polling → confirmed the resulting violation (real speed, real evidence frame) appeared in the list → opened its detail page, saw the actual evidence image render from the API → typed a Devanagari plate correction and changed status through the real form inputs → reloaded the page from scratch and confirmed both persisted server-side (not just local React state).

Also fresh-clone verified: cloned the repo new, installed both `requirements.txt` and the dashboard's `package.json` from nothing, ran migrations against fresh containers, and confirmed all 25 backend tests and 9 frontend tests pass with no local state carried over.

## Known simplifications (by design)

- File uploads are read fully into memory before being written to disk (`await file.read()`) — fine at the video sizes this project deals with; a production deployment handling large uploads would stream to disk in chunks instead.
- The RQ job's calibration is the same illustrative one from Modules 3/4 — real per-camera calibration is a Module 7+ concern once real, calibrated footage exists.
- No auth on any endpoint yet — this is a local review tool for now, not a deployed multi-user system.
