"""Exercise the distributed desktop binary and player with real video in CI."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import expect, sync_playwright

from checkpoint import SessionStore, fingerprint


def make_video(decoder, path, encoder):
    # Headless-only fixture. Two alternating brightness bursts at 1s and 7s.
    frame = bytes([0]) * (64 * 36 * 3)
    white = bytes([255]) * len(frame)
    samples = b"".join(
        white if (10 <= i < 20 or 70 <= i < 80) and i % 2 else frame
        for i in range(100)
    )
    subprocess.run(
        [str(decoder), "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", "64x36", "-r", "10", "-i", "pipe:0", "-c:v", encoder,
         "-pix_fmt", "yuv420p", str(path)],
        input=samples, check=True, capture_output=True,
    )


def verify_player(browser, address):
    page = browser.new_page(accept_downloads=True)
    try:
        page.goto(address)
        expect(page.locator("#summary")).to_contain_text("2 potential flashing", timeout=30000)
        cards = page.locator("#segments .segment")
        expect(cards).to_have_count(2)
        cards.nth(0).click()
        expect(page.locator("#confirm")).to_be_visible()
        page.wait_for_function("document.getElementById('player').readyState >= 2")
        assert page.locator("#player").evaluate("(v) => v.paused")
        page.locator("#confirm").click()
        page.wait_for_function("""() => {
            const v = document.getElementById('player');
            return !v.paused && v.currentTime > 0.8 && v.videoWidth === 64;
        }""")
        page.locator("#pause").click()
        assert page.locator("#player").evaluate("(v) => v.paused")
        page.locator("#pause").click()
        expect(page.locator("#playState")).to_have_text("Section ended", timeout=10000)
        page.locator("#nextFlag").click()
        expect(page.locator("#confirm")).to_be_visible()
        page.locator("#confirm").click()
        page.wait_for_function("""() => {
            const v = document.getElementById('player');
            return !v.paused && v.currentTime > 6.8;
        }""")
        page.locator("#exportFormat").select_option("json")
        with page.expect_download() as download:
            page.locator("#saveReport").click()
        report = json.loads(Path(download.value.path()).read_text())
        intervals = report["flaggedIntervals"]
        assert len(intervals) == 2
    finally:
        page.close()


def check(package, extension, encoder, browser_name, playwright):
    binary = package / "FlashGuard"
    decoders = [p for p in package.rglob("ffmpeg-*") if p.is_file() and os.access(p, os.X_OK)]
    assert len(decoders) == 1, decoders
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        video = base / f"fixture.{extension}"
        make_video(decoders[0], video, encoder)
        store = SessionStore(base / "state")
        # Seed a zero-frame recovery checkpoint to use the real analysis path
        # without automating an operating-system-specific native file chooser.
        store.save(dict(schema=1, status="partial", identity=fingerprint(video),
                        count=0, events=[], cues=[], previous=None, elapsedSeconds=0))
        subprocess.run([str(binary), "--self-test"], check=True, timeout=30)
        with (base / "launcher.log").open("w+") as log:
            env = dict(os.environ, FLASHGUARD_DATA_DIR=str(store.directory), BROWSER="/usr/bin/true %s")
            process = subprocess.Popen([str(binary)], env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 30
                while not store.runtime.exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.1)
                address = json.loads(store.runtime.read_text())["address"]
                with getattr(playwright, browser_name).launch() as browser:
                    verify_player(browser, address)
                saved = store.load()
                assert saved["status"] == "complete"
                report = saved["result"]
                assert report["settings"]["analyzedSamples"] == 100
                for second in (1.5, 7.5):
                    assert any(s["start"] <= second <= s["end"] for s in report["segments"])
                print(f"PASS: released binary analyzed {extension} and {browser_name} played both intervals.")
            except Exception:
                log.seek(0)
                print(log.read(), file=sys.stderr)
                raise
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        package = Path(sys.argv[1]).resolve()
        check(package, "mp4", "libx264", "chromium", playwright)
        check(package, "webm", "libvpx", "firefox", playwright)
