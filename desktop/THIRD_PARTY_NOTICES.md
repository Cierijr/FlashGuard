# Third-party components

This application bundles Python, NumPy, imageio-ffmpeg, its FFmpeg executable, and a PyInstaller bootloader. Applicable licenses and notices are preserved in the distribution's licenses directory and bundled package data. FFmpeg's exact license/configuration is recorded in FFmpeg-LICENSE.txt and FFmpeg-BUILD.txt.

- Python: https://www.python.org/psf/license/
- NumPy: https://github.com/numpy/numpy (BSD license and bundled dependency notices)
- imageio-ffmpeg: https://github.com/imageio/imageio-ffmpeg (BSD-2-Clause)
- FFmpeg: https://ffmpeg.org/legal.html ; bundled binary provenance: https://github.com/imageio/imageio-binaries/tree/master/ffmpeg ; FFmpeg source: https://ffmpeg.org/releases/ ; Windows build source and configuration: https://www.gyan.dev/ffmpeg/builds/
- PyInstaller: https://pyinstaller.org/en/stable/license.html (GPL with bootloader exception)

The bundled FFmpeg executable is a separate subprocess. Its specific build flags determine applicable LGPL/GPL terms. Retain its notices and corresponding-source access information when redistributing. This preview does not provide a proprietary license grant for third-party components.
