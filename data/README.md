# data/

This directory is gitignored — datasets and trained model weights are too large to commit and, for anything derived from footage of real vehicles, shouldn't live in a repo history regardless of size.

Nothing lives here yet. As each dataset gets used, the script or notebook that fetches/builds it lands in `cv-service/scripts/` or `cv-service/notebooks/`, and a short writeup of what was used and why goes in `docs/data-cards/`.
