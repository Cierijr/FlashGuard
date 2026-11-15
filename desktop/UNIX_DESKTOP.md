# FlashGuard Desktop on macOS and Linux

The desktop version uses FFmpeg for sequential video analysis and opens the
report in your default browser. Analysis and recovery data stay on your device.

## Choose a package

- Apple Silicon Mac: `FlashGuard-macOS-arm64.tar.gz`
- Intel Mac: `FlashGuard-macOS-x64.tar.gz`
- Linux desktop on an Intel or AMD 64-bit CPU: `FlashGuard-Linux-x64.tar.gz`

Use the matching archive from [GitHub Releases](https://github.com/Cierijr/FlashGuard/releases)
when available. The macOS builds are tested on macOS 15 runners. The Linux build
targets Ubuntu 22.04 x86-64 and newer compatible desktop distributions with a
graphical session and an installed browser. Linux ARM, ChromeOS, iOS, and Android
are outside these desktop packages.

## Extract and launch

Open a terminal in the downloaded archive's directory. Substitute the filename
you downloaded in the first command.

```sh
tar -xzf FlashGuard-macOS-arm64.tar.gz
cd FlashGuard
./FlashGuard
```

Keep the extracted files together and keep FlashGuard open while using the browser
report. The packages bundle Python and FFmpeg. The macOS release is a preview
without Apple notarization, so Gatekeeper may block it. If a managed computer
blocks the package, contact its administrator or use the browser-only version.
On macOS and Linux, if the report tab is already open, select it manually when
the launcher prompts you. Automatic tab selection uses a Windows-specific helper.

## Run from source

Install Python 3.12 with Tk support and a desktop browser. On Linux, Tk support
may be a separate distribution package. Open a terminal at the repository root.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install numpy==2.2.6 imageio-ffmpeg==0.6.0
python desktop/app.py
```

If the Python environment cannot supply FFmpeg, install a compatible FFmpeg
through your operating system's package manager and set `IMAGEIO_FFMPEG_EXE`
to the absolute binary path.

The browser-only alternative is to extract the repository source ZIP and open
`index.html`. Its processing time depends on the browser, codec, and hardware.
Sampled analysis can miss events and does not establish viewing safety.
