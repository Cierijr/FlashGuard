# FlashGuard desktop preview

## For users

Use the packaged **FlashGuard-Windows-x64.zip** from [Releases](https://github.com/Cierijr/FlashGuard/releases). Extract the entire folder and run **FlashGuard.exe**. Keep the launcher open while using the browser interface. Python and the FFmpeg decoder are included in the package; a browser must already be installed. The source ZIP from the green Code button is not the packaged application.

The launcher opens the same review interface in your browser using a private loopback address. Choose video opens the Windows file chooser. The video is read directly from disk; it is never uploaded to a remote service. FFmpeg decodes it in order at 10 samples/sec and passes 32x18 RGB frames to the detector. Local preview streaming supports byte ranges, and preview playback remains limited to flagged intervals. Review notes, skip navigation, timestamp finding, filters, and TXT/JSON exports use the existing interface.

Close the launcher when finished. Closing only the browser tab leaves the launcher running. Windows may identify the preview as an unsigned application. Videos FFmpeg can analyze may not be previewable in the browser if that browser lacks the codec.

## Scope and limitations

Windows x64 preview; not a macOS/Linux download. The Python source can run on other systems with Python, Tk, NumPy, and FFmpeg installed, but those systems are not packaged here. No administrator access, API key, ChatGPT account, or network access is required to run the packaged app after download.

Sampling stays at 0.1 seconds, with the existing brightness/red thresholds, repeated-transition rule, grouping, and interval padding. FFmpeg resampling/scaling differs from browser seeking: individual sampled images, timestamps, and detections may differ. There is no claim of identical browser results or certified flash safety. No full-video copy is retained. Recovery saves numerical summaries, the previous sample's luminance/red data, detections, and the original video path locally. No sample cap is applied.

## Build and test (developers only)

From the repository root, on Windows:

```powershell
python -m pip install -r desktop/requirements-build.txt
python -m unittest discover -s desktop -p test_desktop.py -v
python -m PyInstaller --noconfirm --clean --onedir --windowed --name FlashGuard --collect-all imageio_ffmpeg --add-data "index.html;." --add-data "desktop/bridge.js;desktop" --add-data "desktop/focus_browser.ps1;." desktop/app.py
```

The workflow `.github/workflows/desktop-windows.yml` runs these tests on Windows, packages the runtime and decoder, runs the packaged self-test, preserves third-party notices, and publishes a prerelease ZIP plus a SHA256 checksum. The workflow runs when desktop source changes on main or via Actions > Build Windows desktop preview > Run workflow. Do not redistribute just the EXE: distribute the whole folder, notices, and bundled dependencies.

Run from source with `python desktop/app.py` after installing dependencies. A system FFmpeg is accepted as a development fallback when imageio-ffmpeg is not installed. The packaged app uses its included binary.

## Validation so far

Tests on the development Linux environment decode an actual generated 12-minute video with 7,200 samples and confirm detections near the beginning, middle, and end. They check invalid video handling, cancellation, local API access restrictions, video byte-range requests, and interface delivery. That tiny 32x18 fixture took approximately four seconds to analyze on the development machine; this is not a benchmark for full-resolution user videos. Browser regression tests still pass. Interactive Windows file selection/playback, full-resolution performance, and an independent-computer test remain required. The automated Windows build must succeed before the packaged download is available.

## Compact launcher and recovery

The launcher now has one **Return to FlashGuard tab** button. It starts minimized in the taskbar; the browser opens normally and retains its analysis progress display. Pong and the desktop progress bar have been removed. Restore the launcher from the taskbar if you need its return button.

Closing during analysis offers **Save progress and exit**. Reopen FlashGuard.exe to continue automatically in the browser tab it opens. The original video must stay in the same location and remain unchanged. Analysis pauses while the EXE is closed; it does not run in the background after exit. The decoder replays up to the saved frame before continuing detection, so reopening may involve a catch-up period. No sample is skipped to make recovery faster.

Progress is saved atomically about every five seconds while frames are being processed, and again during a normal close. A forced process exit can lose work since the last successful checkpoint. The saved session is local to this Windows user and computer, under `%LOCALAPPDATA%/FlashGuard/analysis-session.json.gz`. It contains the original file path, video identity, compact numeric sample summaries, and detected events, not a full copy of the video. Only one session is retained. Choosing another video replaces it; **Cancel analysis** discards the checkpoint. A completed analysis is saved so reopening restores its report. Review notes/skip choices edited in the browser should still be downloaded; those edits are not included in the decoder checkpoint.

A single-instance lock prevents a second launcher from writing over the active session. Reopening the EXE while it is already running asks the existing launcher to return to its browser tab. Recovery is available only for analyses started with this version. Older builds did not save checkpoints.

## Grouping and returning to the report tab

Nearby detected intervals now merge across gaps of up to three seconds, including gaps between brightness and red-pattern detections. The preview includes the intervening gap. The threshold and sampling density are unchanged. More distant sequences remain separate.

The launcher now has **Return to FlashGuard tab**. On Windows it uses built-in UI Automation and a unique tab title to select the existing session tab in Edge/Chrome/Firefox, restoring its browser window without navigating or replacing the report. A connection heartbeat avoids opening a duplicate when the existing tab is connected but Windows cannot switch to it. New tabs open only when no existing session is found or recently connected. Browser focus restrictions/accessibility settings can still require manually selecting the existing tab. No browser debugging port or extension is required. The focus helper PowerShell script is bundled with the application.

