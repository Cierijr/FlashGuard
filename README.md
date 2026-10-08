# FlashGuard

IST440W video accessibility prototype — Julianna Cieri.

FlashGuard analyzes a video file on your computer, marks possible rapid brightness or red transitions, and displays timestamps and simple visual cues from before each flagged interval. Selecting an interval opens a warning; playback requires an explicit click.

## Run on another computer

1. Download this repository using **Code → Download ZIP**, then extract it.
2. Open `index.html` in a recent desktop Chrome, Edge, or Firefox browser.
3. Click **Choose video** and select a local MP4 or WebM file your browser supports.
4. Wait for analysis and read the report. Video preview is optional and may contain flashing.
5. To analyze another video, choose another file. Reports are replaced when you choose a new video.

No installation, Python, Node.js, account, ChatGPT, API key, server, or cloud GPU is needed. All styling and application code are included in `index.html`. After downloading, the application works offline. Videos are read locally and are not uploaded. Browser/operating-system codec support determines which files work.

If your browser prevents local-file video access, install Python 3 and run `python -m http.server 8000 --bind 127.0.0.1` from this folder (on Windows, try `py -m http.server 8000 --bind 127.0.0.1`). Open http://127.0.0.1:8000. Stop the server with Ctrl+C.

## Current capabilities and limits

- Real frame sampling and analysis; reports are not prewritten demonstration results.
- One video at a time; multiple files can be analyzed sequentially. Batch processing is not implemented.
- No 30-second limit. At most 3,600 frames are sampled. Videos up to six minutes are sampled at approximately 10 frames per second; longer videos use wider sampling intervals and can miss brief events.
- Each sampled frame is reduced to 32 × 18 pixels. The heuristic counts large brightness/red transitions and groups repeated transitions into intervals. Three transitions are not necessarily three complete flashes.
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
