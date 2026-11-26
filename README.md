# IWantMP7

Fast URL-only downloader for YouTube, TikTok, and Instagram to MP4 or MP3 on Windows.

## One-line launch on any PC

Paste this in PowerShell:

```powershell
irm "https://raw.githubusercontent.com/SyntaxNon/IWantMP7/main/install.ps1" -OutFile "$env:TEMP\iwant-install.ps1"; powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\iwant-install.ps1"
```

`install.ps1` must be in the repo root. No manual file download and no `iex`: it installs
the app under `%LOCALAPPDATA%\iwantMP7`, fetches an embedded Python 3.12 runtime,
`yt-dlp`, `ffmpeg`, and the Minecraft font automatically, then registers `iwant` so it
can be launched from any folder. No system Python or admin rights required.

```powershell
iwant
```

The installer validates archives, extracts with `tar.exe`, falls back to a mirror
if a download is corrupt, and clears the web-mark on every downloaded file.

## Files

- `iwantMP7.py` — application source
- `install.ps1` — self-contained bootstrapper (Python source embedded, binaries auto-fetched)
- `run.bat` — direct launcher
- `README.md` — this file

## Use

Paste an `http(s)` URL, choose MP4 or MP3. Files land in `C:\Users\username\Downloads`.

Menu:

- `[1] mp4`
- `[2] mp3`
- `[3] urls.txt`
- `[4] credits`
- `[0] exit`

`urls.txt` takes one URL per line. Lines starting with `#` are ignored.

## Output

Files are named `<title> [iWantMP7].mp4` or `<title> [iWantMP7].mp3`.

## Credits

- Download engine: github.com/yt-dlp/yt-dlp
- Media tooling: gyan.dev/ffmpeg/builds
- Console font: github.com/Overv/WebCraft
