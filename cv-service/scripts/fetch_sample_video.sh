#!/usr/bin/env bash
# Fetches a real highway traffic clip for local tracking/speed-estimation
# development - not committed to the repo (gitignored under data/), so this
# script is how anyone (including a fresh clone) gets it back.
#
# Source: Roboflow's own public example asset for their `supervision`
# library's tracking/speed-estimation tutorials - a fixed-camera highway
# view, free to use for exactly this kind of demo/testing purpose.
set -euo pipefail

DEST_DIR="$(dirname "$0")/../data/samples"
mkdir -p "$DEST_DIR"
curl -sL -o "$DEST_DIR/vehicles.mp4" https://media.roboflow.com/supervision/video-examples/vehicles.mp4
echo "saved to $DEST_DIR/vehicles.mp4"
