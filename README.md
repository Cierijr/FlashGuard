# START HERE — Download the Faster FlashGuard for Windows

## [⬇ Download FlashGuard for Windows](https://github.com/Cierijr/FlashGuard/releases/download/desktop-preview-4/FlashGuard-Windows-x64.zip)

**Download → Extract All → Open FlashGuard.exe**

Open the extracted **FlashGuard** folder and keep all its files together. Keep the launcher open while using the browser window it opens. Python and FFmpeg are included—no separate installation required. This is a Windows 64-bit preview.

For a short download guide in the file list, open **[START_HERE_FASTER_WINDOWS_DOWNLOAD.md](START_HERE_FASTER_WINDOWS_DOWNLOAD.md)**.

## Windows desktop preview for faster long-video analysis

The new desktop version uses continuous local FFmpeg decoding instead of repeated browser seeks. It keeps approximately 10 samples/sec and the existing detection rules. The Windows package bundles Python and FFmpeg; users extract the entire folder and launch **FlashGuard.exe**, then use the familiar browser interface.

Get **FlashGuard-Windows-x64.zip** from [Releases](https://github.com/Cierijr/FlashGuard/releases) after the Windows build succeeds. **Code > Download ZIP is source code, not the packaged application.** See [desktop setup, validation, and limitations](desktop/README.md). Windows interactive and independent-computer testing remain outstanding. The browser-only option below remains available.


IST440W video accessibility prototype — Julianna Cieri.

FlashGuard analyzes a video file on your computer, marks possible rapid brightness or red transitions, and displays timestamps and simple visual cues from before each flagged interval. Selecting an interval opens a warning; playback requires an explicit click. Playback is limited to individual flagged intervals. Next-section navigation skips marked intervals and wraps around.

## Browser-only alternative (slower for long videos)

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
- No 30-second limit. The entire video is sampled at approximately 10 frames per second (one sample every 0.1 seconds), with no 3,600-sample cap. Longer videos retain the same sampling density and take longer to process. Progress and cancellation remain available. Sampling can still miss events, including flashes between samples.
- Each sampled frame is reduced to 32 × 18 pixels. The heuristic counts large brightness/red transitions and groups repeated transitions into intervals. It now requires at least six alternating transitions of the same type within one second (approximately three complete cycles) before creating a candidate interval. This is a heuristic, not a standards-based flash measurement. Requiring repetition reduces isolated-motion false alarms but can also miss real events.
- This is not a validated WCAG compliance test or a medical safety assessment. False alarms and missed events are possible. No detections does not mean safe to watch.
- Pre-scene cues describe estimated brightness and color from one frame. They do not identify people, objects, or actions.
- No streaming links, protected video extraction, video downloads, server uploads, or stored analysis history. Reports can be explicitly downloaded to your computer. Section marks and review notes remain only for the current video until exported.
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
2. **Event grouping:** merges overlapping intervals and intervals with gaps of up to three seconds into one warning.
3. **Preview controls:** brightness slider (10–100%, initially 50%) and playback speed (0.5×, 0.75×, 1×). These controls do not eliminate seizure risk.
4. **Processing and results feedback:** percentage, elapsed-time heartbeat, frame count, cancellation, completed report summary, and sampling limitation notice.
5. **Separate views:** home/analysis and report/preview views within the same offline HTML file. No account or page download is needed between views.
6. **Click to pause/resume:** clicking the preview or using Space/Enter pauses or resumes; the existing button and paused indicator remain. Playback stops at the flagged interval endpoint; replay returns to its start.

## Optional developer checks

With Node.js installed, run `node test.cjs` from the repository folder. It checks synthetic detector cases and mocked interface behavior. Node.js is not needed to use FlashGuard. These tests do not replace browser/video decoding tests or independent-computer testing.

## October 23 section review features

Each flagged report section has two independent checkboxes:

- **Mark for review:** marks that detected interval for later review and reveals an optional note field, such as “Review this section”. It does not change playback.
- **Skip in next-section navigation:** excludes that detected interval from the Next flagged section button. It does not mark it for review. No intervals are checked for skipping by default.

You can use either choice or both. Click the section's preview button to inspect it behind the existing playback warning. Marking or entering a note does not start playback. Changing a skip checkbox pauses playback so you can finish adjusting the list.

### Save the report

Choose `.txt` or `.json` and press **Save report to computer**. Both downloads contain all detections, precise timestamps, pre-scene cues, analysis and playback settings, whether each section is marked for review, its optional review note, and whether it is marked for skipping. A marked-for-review section without a typed note is exported as “Review this section”. Unchecking review clears it from exported review notes; an unchecked note draft can remain in the field until the video is replaced.

Exports include the local filename, not the video itself. Filters never omit detections or marks from the saved report. Save before choosing a new video or closing/reloading this page: no analysis history or permanent in-app storage is kept.

### Navigate flagged sections

The **Next flagged section** button under the player selects the next section that is not marked for skipping. For example, from section 1, if sections 2 and 3 are marked, it selects section 4. After the last section it wraps to the first unmarked section. If all sections are marked, the button is disabled; unchecking one enables it again. With only one unmarked section, navigation returns to that section.

Selection shows the existing warning and does not autoplay. A marked section can still be deliberately opened from its report card. There is no full-video playback option; each preview stops at the selected interval's end. Filters do not change next-section navigation or exports.

### Find and navigate

- **Find timestamp:** enter seconds, `M:SS`, or `H:MM:SS` to select the containing flagged interval or next matching interval. It pauses playback and requires preview confirmation.
- **Detected pattern:** filter the list by brightness changes or red transitions, where detected. Merged detections retain both labels when available. Filters do not change marks, exports, or skip choices.
- **Next flagged section:** the button beneath the player selects the next unmarked detection and wraps around, presenting its warning without autoplay. It ignores list filters and is disabled when no unmarked detection exists.

There is no separate manual timestamp panel; review choices and notes belong to detected sections.

The application remains one offline HTML file. Download a new copy from GitHub to receive updates; existing downloaded copies do not update automatically.


### Processing speed and progress (October 30 update)

Videos with at least 600 samples (approximately one minute) use two independent browser video decoders on contiguous ranges. A shared boundary sample preserves transitions across the range split. Shorter videos use one decoder. Sampling remains approximately every 0.1 seconds for the entire video; no sample cap has been restored. Settings exported with reports include the worker count and processing strategy.

Progress displays completed/total samples, frames processed per second, and an estimated remaining time after the first 20 samples. The final scene-description stage has its own status. Estimates vary with video resolution, codec/keyframe structure, browser, and computer load. Parallel decoding uses additional resources and is not guaranteed to be faster on every machine. No fixed real-world speedup has been measured. Cancellation and local-only processing remain available.


## Updated grouping and browser return

Candidate intervals separated by no more than three seconds are grouped into one continuous warning. The merged warning includes the gap and preserves all detected pattern labels; sequences farther apart remain separate. Detection thresholds and sample spacing are unchanged. This helps reduce fragmented warnings, but individual videos still need review.

The desktop **Return to FlashGuard tab** button uses a unique session title to find and select the existing report tab in supported Windows browsers. It does not reload the report. A connection heartbeat prevents duplicate tabs if automatic tab selection fails. Windows/browser accessibility restrictions can still prevent activation; the launcher then asks you to select the existing tab manually.
