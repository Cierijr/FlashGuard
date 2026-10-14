# FlashGuard

IST440W video accessibility prototype — Julianna Cieri.

FlashGuard analyzes a video file on your computer, marks possible rapid brightness or red transitions, and displays timestamps and simple visual cues from before each flagged interval. Selecting an interval opens a warning; playback requires an explicit click.

## Run on another computer

1. Download this repository using **Code → Download ZIP**, then extract it.
2. Open `index.html` in a recent desktop Chrome, Edge, or Firefox browser.
3. Click **Choose video** and select a local MP4 or WebM file your browser supports.
4. Watch the progress percentage and elapsed-time updates. You can cancel analysis. When finished, a separate results view shows the summary, timestamps, and pre-scene cues. Video preview is optional and may contain flashing.
5. Use **Choose another video** to return home. Reports are replaced when you choose a new video.

No installation, Python, Node.js, account, ChatGPT, API key, server, or cloud GPU is needed. All styling and application code are included in `index.html`. After downloading, the application works offline. Videos are read locally and are not uploaded. Browser/operating-system codec support determines which files work.

If your browser prevents local-file video access, install Python 3 and run `python -m http.server 8000 --bind 127.0.0.1` from this folder (on Windows, try `py -m http.server 8000 --bind 127.0.0.1`). Open http://127.0.0.1:8000. Stop the server with Ctrl+C.

## Current capabilities and limits

- Real frame sampling and analysis; reports are not prewritten demonstration results.
- One video at a time; multiple files can be analyzed sequentially. Batch processing is not implemented.
- No 30-second limit. At most 3,600 frames are sampled. Videos up to six minutes are sampled at approximately 10 frames per second; longer videos use wider sampling intervals and can miss brief events.
- Each sampled frame is reduced to 32 × 18 pixels. The heuristic counts large brightness/red transitions and groups repeated transitions into intervals. It now requires at least six alternating transitions of the same type within one second (approximately three complete cycles) before creating a candidate interval. This is a heuristic, not a standards-based flash measurement. Requiring repetition reduces isolated-motion false alarms but can also miss real events.
- This is not a validated WCAG compliance test or a medical safety assessment. False alarms and missed events are possible. No detections does not mean safe to watch.
- Pre-scene cues describe estimated brightness and color from one frame. They do not identify people, objects, or actions.
- No streaming links, protected video extraction, automatic downloads, server uploads, report persistence, or report export.
- Keep the browser tab active during analysis. Processing speed depends on video decoding, duration, and the computer.

## Troubleshooting

- **Cannot read video:** use a browser-supported MP4 or WebM encoding; the extension alone does not guarantee compatibility.
- **Could not seek:** try a different local file or browser. Some damaged or unusual files cannot be decoded reliably.
- **Slow processing:** keep the tab active and try a short clip first. Long videos may take substantial time.
- **No flagged sections:** the heuristic found no repeated transitions at the sampled resolution. This is not a safety guarantee.

## Files

- `index.html`: complete application, interface, styles, detector, cues, and preview.
- `README.md`: installation-free launch instructions and limitations.
- `VERIFICATION.md`: checks performed and remaining evaluation.
- `GITHUB_SETUP.md`: repository creation and submission steps.

## Development

Edit `index.html` with a text editor and reload the browser. There are no dependencies or build step. Use short, lawfully obtained test videos. Evaluate detection against annotated intervals before claiming accuracy. Do not ask photosensitive users to view flashing test material.

## October 14 enhancements

1. **Repeated-flash detection:** tracks the direction of brightness and red changes to reject isolated or one-direction changes. The standing-up example still needs to be retested; no measured accuracy improvement is claimed.
2. **Event grouping:** merges overlapping intervals and intervals with gaps of up to one second into one warning.
3. **Preview controls:** brightness slider (10–100%, initially 50%) and playback speed (0.5×, 0.75×, 1×). These controls do not eliminate seizure risk.
4. **Processing and results feedback:** percentage, elapsed-time heartbeat, frame count, cancellation, completed report summary, and sampling limitation notice.
5. **Separate views:** home/analysis and report/preview views within the same offline HTML file. No account or page download is needed between views.
6. **Click to pause/resume:** clicking the preview or using Space/Enter pauses or resumes; the existing button and paused indicator remain. Playback stops at the flagged interval endpoint; replay returns to its start.

## Optional developer checks

With Node.js installed, run `node test.cjs` from the repository folder. It checks synthetic detector cases and mocked interface behavior. Node.js is not needed to use FlashGuard. These tests do not replace browser/video decoding tests or independent-computer testing.
