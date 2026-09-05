# Ethics and privacy

This project processes video of real roads and real vehicles. A few positions worth stating up front, before any pipeline code exists:

## This is a research/portfolio prototype, not a deployed enforcement system

Nothing here issues real tickets, contacts real vehicle owners, or feeds a real traffic authority. Every violation record this system produces is for demonstrating that the pipeline works, not for acting on.

## No continuous surveillance of the public

The system is built to process a video source, not to run an always-on camera watching a public road indefinitely. Any live/streaming demo mode defaults to a recorded clip streamed frame-by-frame to simulate a live feed, rather than an actual continuously-operating public-facing camera. If a genuinely live public traffic camera stream is ever used, it's an existing, already-public, third-party-operated feed being read (not a new surveillance setup created for this project), and only within whatever terms that source actually allows.

## Demo footage handling

Any footage that appears publicly (README, demo recording, hosted instance) has had bystander faces and any vehicle/plate not relevant to the demo blurred before it's shown. Footage used only for local development and never made public isn't held to a lesser standard by omission — it's just not exposed to begin with.

## Known limitations, stated honestly

- Speed estimates come from a manual homography calibration with no lens-distortion correction — treat them as demo-accuracy, not legally admissible measurements.
- Embossed-plate OCR is genuinely experimental (see `docs/data-cards/` once that module lands) — a "could not read" result is an expected, honest outcome, not a bug to hide.
