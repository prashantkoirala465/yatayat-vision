# Live streaming (Module 7)

The plan called for one `FrameSource` abstraction behind file / RTSP / HLS / simulated-live implementations, plus an explicit spike into whether a real, pullable Nepal traffic camera stream exists — with the public demo defaulting to the simulated-live fallback regardless of how that spike turned out.

## What didn't need building

Reading `ultralytics.data.build.load_inference_source` directly (not assumed) confirmed Ultralytics' own `.track(source=...)` already dispatches a plain file path to `LoadImagesAndVideos` and an `rtsp://`/`rtmp://`/`http(s)://` URL (or a webcam index) to `LoadStreams`. `VehicleTracker` just forwards `source` straight through, so it already supports a real live stream with zero additional code — the "FrameSource abstraction" the plan asked for already exists inside the dependency, and adding a parallel one of our own would just be a wrapper around it.

## What was actually new: `simulate_live()`

The one thing nothing else provides is making a *recorded* file behave like a live feed for demo purposes. `app/streaming/frame_source.py`'s `simulate_live()` paces a frame iterator to arrive no faster than a target fps, sleeping when processing is ahead of schedule and letting it fall behind (not catch up) when processing is genuinely too slow — the same as a real live system under load. Verified two ways:

- Synthetic timing tests (`tests/test_frame_source.py`): 5 frames at 10fps takes ~0.4s; a processing step already slower than the target fps isn't held back further.
- Real integration: the actual tracker against `data/samples/vehicles.mp4` runs unpaced at ~11.5fps; paced to a 5fps target, 30 frames took 5.81s (expected ~6.0s).

Wired into `PipelineConfig.simulate_live` (default `False`, so batch processing behaves exactly as before) and exposed through both entry points: `scripts/violation_demo.py --simulate-live` and the jobs API (`POST /jobs?simulate_live=true`, surfaced in the dashboard as a checkbox on the upload form).

## The spike: does a real, pullable Nepal traffic camera stream exist?

Short answer: not one that was found. Two paths were tried:

- **TrafficVision.Live** — an earlier attempt returned HTTP 403; refetched with a browser User-Agent and got a real HTTP 200, but the saved HTML has no `.m3u8`/`.mpd`/`rtsp://` URL anywhere in it — it's a JS-rendered single-page app that resolves its stream URLs client-side, not something a plain HTTP fetch (or this pipeline) can pull directly. Getting a URL out of it would need a headless browser to run its JS and intercept the network requests — possible, but a meaningfully bigger and more fragile piece of infrastructure than the value it buys for a portfolio demo.
- **YouTube Live** — `yt-dlp` can resolve a YouTube Live video into a real, consumable HLS URL, so a genuinely live Nepal-based channel would have worked. A channel search surfaced "WEBCAM NEPAL LIVE" with a search-result snippet specifically claiming a Thamel intersection traffic view. Listing the channel's actual live/past streams (`yt-dlp --skip-download --print ... .../streams`) shows every stream is a scenic mountain or lodge cam — Everest View, Kagbeni, Thame, Annapurna Base Camp, Lukla, Dingboche, Namche Bazaar, plus an unrelated London pond cam. No Thamel intersection, no traffic view of any kind. The search snippet doesn't match what the channel actually streams.

No other candidate aggregator (OpenCCTV.org, SkylineWebcams) was found to expose a Nepal traffic feed either, on the same brief look.

## Where this leaves Module 7

The MVP demo runs on the simulated-live fallback, as the plan always intended regardless of this spike's outcome — the architecture genuinely supports a real live source (no code changes needed, just point `--source` at a real `rtsp://`/`http(s)://` URL), but no such source for Nepal traffic was actually found. If one turns up later — a real municipal or ISP-hosted traffic cam, or a headless-browser-based resolver for TrafficVision.Live — plugging it in needs nothing beyond passing its URL as `source`.
