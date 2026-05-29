Place libmpv DLLs here before running or building.

1. Go to: https://sourceforge.net/projects/mpv-player-windows/files/libmpv/
2. Download the latest  mpv-dev-x86_64-*.7z
3. Extract ALL .dll files from the archive into THIS folder.

Required DLLs include:
  mpv-2.dll           (the main libmpv library)
  avcodec-*.dll       (FFmpeg codec)
  avformat-*.dll      (FFmpeg format)
  avutil-*.dll        (FFmpeg utilities)
  swscale-*.dll       (FFmpeg scaling)
  swresample-*.dll    (FFmpeg resampling)
  ... and any others in the archive.

After placing the DLLs here, run:
  python src\main.py         (development)
  build.bat                  (create distributable exe)
