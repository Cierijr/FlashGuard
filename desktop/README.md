# FlashGuard desktop preview

## For users

Use the packaged **FlashGuard-Windows-x64.zip** from [Releases](https://github.com/Cierijr/FlashGuard/releases). Extract the entire folder and run **FlashGuard.exe**. Keep the launcher open while using the browser interface. Python and the FFmpeg decoder are included in the package; a browser must already be installed. The source ZIP from the green Code button is not the packaged application.

The launcher opens the same review interface in your browser using a private loopback address. Choose video opens the Windows file chooser. The video is read directly from disk; it is never uploaded to a remote service. FFmpeg decodes it in order at 10 samples/sec and passes 32x18 RGB frames to the detector. Local preview streaming supports byte ranges, and preview playback remains limited to flagged intervals. Review notes, skip navigation, timestamp finding, filters, and TXT/JSON exports use the existing interface.

Close the launcher when finished. Closing only the browser tab leaves the launcher running. Windows may identify the preview as an unsigned application. Videos FFmpeg can analyze may not be previewable in the browser if that browser lacks the codec.

## Scope and limitations

Windows x64 preview; not a macOS/Linux download. The Python source can run on other systems with Python, Tk, NumPy, and FFmpeg installed, but those systems are not packaged here. No administrator access, API key, ChatGPT account, or network access is required to run the packaged app after download.

Sampling stays at 0.1 seconds, with the existing brightness/red thresholds, repeated-transition rule, grouping, and interval padding. FFmpeg resampling/scaling differs from browser seeking: individual sampled images, timestamps, and detections may differ. There is no claim of identical browser results or certified flash safety. No frames or full-video copies are retained. Compact frame summaries and candidate events are held in memory during analysis. No sample cap is applied.

## Build and test (developers only)

From the repository root, on Windows:

```powershell
python -m pip install -r desktop/requirements-build.txt
python -m unittest discover -s desktop -p test_desktop.py -v
python -m PyInstaller --noconfirm --clean --onedir --windowed --name FlashGuard --collect-all imageio_ffmpeg --add-data "index.html;." --add-data "desktop/bridge.js;desktop" desktop/app.py
```

The workflow `.github/workflows/desktop-windows.yml` runs these tests on Windows, packages the runtime and decoder, runs the packaged self-test, preserves third-party notices, and publishes a prerelease ZIP plus a SHA256 checksum. The workflow runs when desktop source changes on main or via Actions > Build Windows desktop preview > Run workflow. Do not redistribute just the EXE: distribute the whole folder, notices, and bundled dependencies.

Run from source with `python desktop/app.py` after installing dependencies. A system FFmpeg is accepted as a development fallback when imageio-ffmpeg is not installed. The packaged app uses its included binary.

## Validation so far

Tests on the development Linux environment decode an actual generated 12-minute video with 7,200 samples and confirm detections near the beginning, middle, and end. They check invalid video handling, cancellation, local API access restrictions, video byte-range requests, and interface delivery. That tiny 32x18 fixture took approximately four seconds to analyze on the development machine; this is not a benchmark for full-resolution user videos. Browser regression tests still pass. Interactive Windows file selection/playback, full-resolution performance, and an independent-computer test remain required. The automated Windows build must succeed before the packaged download is available.
