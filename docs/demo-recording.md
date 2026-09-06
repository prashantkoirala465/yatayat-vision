# Demo recording checklist

Recording the actual screen capture is a manual step for the user — not something this repo can generate. This is the script to follow when doing it.

## Before recording

- [ ] `cd infra && docker compose --profile full up --build` — confirm all five containers report healthy/running, dashboard loads at `http://localhost:3000`
- [ ] Have a real video clip ready to upload (`cv-service/data/samples/vehicles.mp4`, or the user's own footage with bystander faces/plates blurred per `docs/ethics-and-privacy.md`)
- [ ] Clear out any leftover demo data from a previous take (`docker compose down -v` resets postgres, or just note the starting violation count)

## What to actually show, in order

1. **The problem** (10-15s, talking over a static slide or the README): Nepal's plate/speed enforcement gap, the embossed-plate OCR challenge — see README.md's "Why" section for the framing.
2. **Upload a video** through the dashboard's upload form, speed limit set to something the clip will trigger, "simulate live feed" checkbox on — narrate that this paces the recorded file like a live camera feed (`docs/models/live_streaming.md`).
3. **Job status polling** — show it go queued → started → finished in the UI, not just a instant cut, so it reads as a real background job, not a canned response.
4. **The violations list** populated with the new entry — speed, plate (or the honest "unreadable" state — don't cherry-pick only clips where OCR worked; showing the honest failure mode is part of this project's actual story, see `docs/models/plate_ocr.md`).
5. **Open the violation detail page** — evidence frame, plate crop, and the manual plate-text correction field actually being typed into and saved (the human-review workflow this project is built around, not just an automated black box).
6. **One architecture beat**: point at `docs/architecture.md`'s diagram, mention the API/worker split and why (`docs/deployment.md`) — 15-20s, establishes this wasn't a toy script.

## After recording

- [ ] Trim dead air at the start/end
- [ ] Re-watch once end-to-end before treating it as final — a broken take is easier to just re-record than to explain away in the README
- [ ] Link it from the root `README.md` once it exists (not done yet — there's no recording to link to)
