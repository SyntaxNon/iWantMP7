"""iwantMP7 — URL-only downloader, silent transport, themed shell."""
from __future__ import annotations

import ctypes
import io
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
BIN = ROOT / "bin"
YTDLP = BIN / "yt-dlp.exe"
DOWNLOADS = Path.home() / "Downloads"
URL_RE = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)
MAX_HEIGHT = 1080
NAME_TAG = "iWantMP7"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

INK = {
    "deep":   (92, 52, 20),
    "mid":    (191, 92, 24),
    "orange": (255, 145, 45),
    "soft":   (255, 176, 92),
    "pale":   (255, 214, 165),
    "warn":   (230, 110, 90),
    "good":   (180, 210, 140),
}
GLYPHS = {
    "I": ["█████", "  █  ", "  █  ", "  █  ", "  █  ", "  █  ", "█████"],
    "W": ["█   █", "█   █", "█   █", "█ █ █", "█ █ █", "██ ██", "█   █"],
    "A": [" ███ ", "█   █", "█   █", "█████", "█   █", "█   █", "█   █"],
    "N": ["█   █", "██  █", "█ █ █", "█ █ █", "█  ██", "█   █", "█   █"],
    "T": ["█████", "  █  ", "  █  ", "  █  ", "  █  ", "  █  ", "  █  "],
    "M": ["█   █", "██ ██", "█ █ █", "█ █ █", "█   █", "█   █", "█   █"],
    "P": ["████ ", "█   █", "█   █", "████ ", "█    ", "█    ", "█    "],
    "7": ["█████", "    █", "   █ ", "  █  ", "  █  ", "  █  ", "  █  "],
}
BANNER = "\n".join(
    "".join(GLYPHS[ch][row] + "  " for ch in "IWANTMP7").rstrip()
    for row in range(7)
)

WIDTH = 84
SAMPLE_INTERVAL = 0.25


def vt() -> None:
    if sys.platform == "win32":
        kern = ctypes.windll.kernel32
        kern.SetConsoleMode(kern.GetStdHandle(-11), 0x0007)


def clear_screen() -> None:
    if sys.platform == "win32":
        os.system("cls")
    else:
        sys.stdout.write("\x1b[3J\x1b[H\x1b[2J")
    sys.stdout.flush()


def paint(text: str, tone: str) -> str:
    r, g, b = INK[tone]
    return f"\x1b[38;2;{r};{g};{b}m{text}\x1b[0m"


class Console:
    def line(self, text: str = "", tone: str = "deep") -> None:
        print(paint(text, tone))

    def progress(self, text: str, tone: str = "mid",
                 clear: bool = False) -> None:
        prefix = "\x1b[1G\x1b[2K" if clear else "\r"
        sys.stdout.write(prefix + paint(text, tone))
        sys.stdout.flush()

    def clear(self) -> None:
        sys.stdout.write("\x1b[1G\x1b[2K")
        sys.stdout.flush()


OUT = Console()


def line(text: str = "", tone: str = "deep") -> None:
    OUT.line(text, tone)


class ExitApp(Exception):
    pass


def ask(prompt: str) -> str:
    try:
        return input(paint(prompt, "orange")).strip()
    except (EOFError, KeyboardInterrupt):
        raise ExitApp


def runtime_args() -> list[str]:
    known = [
        Path("C:/Program Files/nodejs/node.exe"),
        Path("C:/Program Files (x86)/nodejs/node.exe"),
    ]
    if shutil.which("node") or any(p.exists() for p in known):
        return ["--js-runtimes", "node"]
    return []


def clean_error(text: str) -> str:
    text = re.sub(r"^ERROR:\s*", "", text.strip(), flags=re.I)
    text = re.sub(r"^\[[^\]]+\]\s*(?:[\w-]+\s*:\s*)?", "", text)
    return re.sub(r"\s+", " ", text).strip()


def boot() -> None:
    vt()
    clear_screen()
    print()
    for i in range(1, 26):
        bar = "[" + "#" * i + "." * (25 - i) + "]"
        tone = "good" if i == 25 else "mid"
        OUT.progress(f"  {bar} {i * 4:3d}%  waking the system", tone)
        time.sleep(0.035)
    OUT.clear()
    line("  > ready", "orange")


def banner() -> None:
    print()
    for i, src in enumerate(BANNER.strip("\n").splitlines()):
        line(src, "orange" if i % 2 == 0 else "soft")
    line("  url in -> mp3 / mp4 out   |   yt - tiktok - instagram", "deep")


def detect_site(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if "youtube" in host or "youtu.be" in host:
        return "youtube"
    if "tiktok" in host:
        return "tiktok"
    if "instagram" in host:
        return "instagram"
    return host or "?"


def site_args(url: str) -> list[str]:
    host = (urlparse(url).hostname or "").lower()
    if "tiktok" in host or "instagram" in host:
        return ["--no-check-certificates"]
    return []


def video_format() -> str:
    height = MAX_HEIGHT
    return (
        f"bv*[vcodec^=avc1][height<={height}]+ba[acodec^=mp4a]/"
        f"bv*[vcodec^=avc1][height<={height}]+ba/"
        f"b[vcodec^=avc1][height<={height}]/"
        f"bv*[height<={height}]+ba/b[height<={height}]/best"
    )


def format_size(entry: dict) -> int:
    for key in ("filesize", "filesize_approx"):
        value = entry.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return int(value)
    return 0


def fetch_meta(url: str) -> tuple[str, int | None, int | None]:
    fallback = f"{detect_site(url)} video"
    cmd = [str(YTDLP), "-J", "--skip-download", "--no-playlist",
           "--no-warnings", "--quiet", *runtime_args(), *site_args(url),
           "-f", video_format(), "--merge-output-format", "mp4", url]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30, creationflags=NO_WINDOW,
        )
    except OSError:
        return fallback, None, None
    if proc.returncode != 0:
        return fallback, None, None
    try:
        info = json.loads(proc.stdout)
    except (json.JSONDecodeError, TypeError):
        return fallback, None, None

    title = str(info.get("title") or fallback).strip()[:46] or fallback
    requested = info.get("requested_formats") or []
    video_total = sum(format_size(f) for f in requested) or None
    if not video_total:
        video_total = format_size(info) or None

    audio_total = max(
        (format_size(f) for f in info.get("formats", [])
         if f.get("vcodec") == "none"),
        default=0,
    )
    duration = info.get("duration")
    if not audio_total and isinstance(duration, (int, float)):
        audio_total = int(duration) * 40000
    return title, video_total, audio_total or None


def preview(url: str, title: str) -> None:
    site = detect_site(url)
    if len(site) > 18:
        site = site[:17] + "."
    head = f"{site}  ->  "
    tail = "  ->  mp4 / mp3 ?"
    room = max(8, WIDTH - 6 - len(head) - len(tail))
    body = head + title[:room] + tail
    print()
    line("  +" + "-" * (WIDTH - 4) + "+", "deep")
    line("  | " + body.ljust(WIDTH - 6) + " |", "soft")
    line("  +" + "-" * (WIDTH - 4) + "+", "deep")
    line("  [1] mp4  video + audio    [2] mp3  audio only", "orange")


class Pulse:
    FRAMES = "|/-\\"

    def __init__(self, label: str = "downloading",
                 total: int | None = None, before: set[Path] | None = None,
                 folder: Path = DOWNLOADS) -> None:
        self.label = label
        self.total = total
        self.before = before or set()
        self.folder = folder
        self.pct = ""
        self.bytes_seen = 0
        self.last_live = 0.0
        self.start_pct = 0
        self.peak_pct = 0
        self.done = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self) -> None:
        i = 0
        while not self.done.is_set():
            frame = self.FRAMES[i % 4]
            self._sample()
            if not self.pct:
                pos = (i // 2) % 20
                scan = "[" + "." * pos + "#" + "." * (19 - pos) + "]  ??%"
                tail = scan
            else:
                tail = self.pct
            OUT.progress(
                f"  {frame} {self.label} {tail}".ljust(WIDTH),
                "mid", clear=True)
            i += 1
            self.done.wait(0.06)

    def _shown(self) -> int:
        match = re.search(r"(\d+)%", self.pct)
        return int(match.group(1)) if match else 0

    def _sample(self) -> None:
        if time.monotonic() - self.last_live < SAMPLE_INTERVAL:
            return
        if not self.folder.exists():
            return
        try:
            live = sum(
                p.stat().st_size for p in self.folder.iterdir()
                if p.is_file() and p not in self.before
                and (p.name.endswith((".part", ".ytdl"))
                     or p.suffix.lower() in (".mp4", ".mp3", ".m4a", ".webm"))
            )
        except OSError:
            return
        self.bytes_seen = max(self.bytes_seen, live)
        if self.total:
            n = min(99, self.bytes_seen * 100 // self.total)
            if n <= self._shown():
                return
            self.peak_pct = max(self.peak_pct, n)
            filled = n * 20 // 100
            self.pct = "[" + "#" * filled + "." * (20 - filled) + f"] {n:3d}%"
        elif self.bytes_seen:
            mb = self.bytes_seen / 1048576
            pos = min(19, self.bytes_seen // 1048576 % 20)
            bar = "[" + "." * pos + "#" + "." * (19 - pos) + "]"
            self.pct = f"{bar} {mb:6.1f} MB"

    def set(self, value: str) -> None:
        match = re.search(r"(\d+(?:\.\d+)?)%", value)
        if not match:
            return
        n = max(int(float(match.group(1))), self.peak_pct)
        if n < 100:
            self.peak_pct = n
        filled = n * 20 // 100
        self.pct = "[" + "#" * filled + "." * (20 - filled) + f"] {n:3d}%"
        self.last_live = time.monotonic()

    def finish(self) -> None:
        match = re.search(r"(\d+)%", self.pct)
        current = int(match.group(1)) if match else 0
        self.start_pct = max(self.peak_pct, current)
        self.pct = "[" + "#" * 20 + "] 100%"

    def stop(self, success: bool = True) -> None:
        self.done.set()
        if self.thread:
            self.thread.join()
        start = self.start_pct
        for n in range(start + 5, 100, 5) if success else ():
            bar = "[" + "#" * (n // 5) + "." * (20 - n // 5) + f"] {n:3d}%"
            OUT.progress(
                f"  / {self.label} {bar}".ljust(WIDTH),
                "mid", clear=True)
            time.sleep(0.015)
        if "100%" in self.pct:
            OUT.progress(
                f"  done {self.pct}".ljust(WIDTH), "good", clear=True)
            time.sleep(0.18)
        OUT.clear()


def normalize_mp4(paths: list[Path]) -> list[str]:
    ffmpeg = BIN / "ffmpeg.exe"
    failures: list[str] = []
    if not ffmpeg.exists():
        return failures
    for src in (p for p in paths if p.suffix.lower() == ".mp4"):
        probe = subprocess.run(
            [str(ffmpeg), "-hide_banner", "-i", str(src)],
            capture_output=True, text=True, errors="replace",
            creationflags=NO_WINDOW,
        )
        if not re.search(r"Video:\s*(av1|av01|vp09|vp9|hevc|h265|hvc1)",
                         probe.stderr, re.I):
            continue
        tmp = src.with_name(src.stem + ".__h264.mp4")
        result = subprocess.run(
            [str(ffmpeg), "-y", "-hide_banner", "-loglevel", "error",
             "-i", str(src), "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac",
             "-b:a", "192k", "-movflags", "+faststart", str(tmp)],
            creationflags=NO_WINDOW,
        )
        if result.returncode == 0:
            tmp.replace(src)
        else:
            tmp.unlink(missing_ok=True)
            failures.append(src.name)
    return failures


def grab(url: str, mode: str, total: int | None = None) -> bool:
    try:
        DOWNLOADS.mkdir(parents=True, exist_ok=True)
        before = {p for p in DOWNLOADS.iterdir()}
        started = time.time()
    except OSError as exc:
        line(f"  error: {exc}", "warn")
        return False

    if mode == "mp4":
        args = ["-f", video_format(), "--merge-output-format", "mp4"]
    else:
        args = ["-x", "--audio-format", "mp3", "--audio-quality", "0"]

    args += [
        "--quiet", "--no-warnings", "--progress",
        "--progress-template", "download:%(progress._percent_str)s",
        "--no-playlist", "--force-overwrites", *runtime_args(),
        *site_args(url), "--ffmpeg-location", str(BIN),
        "-o", str(DOWNLOADS / f"%(title).80B [{NAME_TAG}].%(ext)s"), url,
    ]

    pulse = Pulse(total=total, before=before, folder=DOWNLOADS)
    pulse.start()
    try:
        proc = subprocess.Popen(
            [str(YTDLP), *args],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0,
            creationflags=NO_WINDOW,
        )
    except OSError as exc:
        pulse.stop(False)
        line(f"  error: {exc}", "warn")
        return False
    if proc.stdout is None:
        pulse.stop(False)
        line("  error: no process output", "warn")
        return False
    stream = io.TextIOWrapper(proc.stdout, encoding="utf-8", errors="replace")
    buf = ""
    errors: list[str] = []
    try:
        while True:
            ch = stream.read(1)
            if not ch:
                break
            if ch in "\r\n":
                text = buf.strip()
                buf = ""
                if "ERROR" in text:
                    errors.append(text)
                elif "%" in text:
                    pulse.set(text)
            else:
                buf += ch
        if buf.strip():
            text = buf.strip()
            if "ERROR" in text:
                errors.append(text)
            elif "%" in text:
                pulse.set(text)
        code = proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        pulse.stop(False)
        line("  cancelled", "warn")
        return False
    finally:
        stream.close()
    if code == 0:
        pulse.finish()
    pulse.stop(code == 0)
    if errors:
        line(f"  error: {clean_error(errors[-1])[:140]}", "warn")

    if code == 0:
        ext = ".mp4" if mode == "mp4" else ".mp3"
        after = [p for p in DOWNLOADS.iterdir()]
        produced = [p for p in after
                    if p not in before and p.suffix.lower() == ext]
        marker = f"[{NAME_TAG}]{ext}"
        produced += [
            p for p in after
            if p.suffix.lower() == ext and p.name.endswith(marker)
            and p.stat().st_mtime >= started - 2
        ]
        produced = list(dict.fromkeys(produced))
        if not produced:
            line("  error: no output file", "warn")
            return False
        if mode == "mp4":
            for name in normalize_mp4(produced):
                line(f"  error: h264 failed: {name[:60]}", "warn")
        line(f"  > saved -> {DOWNLOADS}", "good")
        return True
    if not errors:
        line(f"  error: exit {code}", "warn")
    return False


def menu() -> None:
    while True:
        clear_screen()
        banner()
        print()
        body = "  | [1] mp4    [2] mp3    [3] urls.txt    [4] credits    [0] exit "
        line("  +" + "-" * (WIDTH - 4) + "+", "deep")
        line(body.ljust(WIDTH - 3) + "|", "pale")
        line("  +" + "-" * (WIDTH - 4) + "+", "deep")
        choice = ask("  select > ")

        if choice == "0":
            line("  see you, chef.", "soft")
            return

        if choice in ("1", "2"):
            url = ask("  paste url > ")
            if not URL_RE.match(url):
                line("  http(s) url only", "warn")
                continue
            pulse = Pulse("reading title")
            pulse.start()
            try:
                title, video_total, audio_total = fetch_meta(url)
            except subprocess.TimeoutExpired:
                title, video_total, audio_total = f"{detect_site(url)} video", None, None
            finally:
                pulse.stop(False)
            preview(url, title)
            pick = ask("  > ")
            mode = "mp3" if pick == "2" else "mp4"
            grab(url, mode, audio_total if mode == "mp3" else video_total)
            ask("  press enter to refresh > ")

        elif choice == "4":
            print()
            line("  +" + "-" * (WIDTH - 4) + "+", "deep")
            line("  |  iWantMP7 - credits", "soft")
            line("  |  author  : SyntaxNon", "pale")
            line("  |  github  : github.com/SyntaxNon/IWantMP7", "pale")
            line("  |  engine  : github.com/yt-dlp/yt-dlp", "pale")
            line("  |  ffmpeg  : gyan.dev/ffmpeg/builds", "pale")
            line("  |  font    : github.com/Overv/WebCraft", "pale")
            line("  +" + "-" * (WIDTH - 4) + "+", "deep")
            ask("  press enter to refresh > ")

        elif choice == "3":
            listing = ROOT / "urls.txt"
            if not listing.exists():
                line("  no urls.txt, one url per line", "warn")
                continue
            with listing.open("r", encoding="utf-8-sig",
                              errors="replace") as handle:
                urls = [x.strip() for x in handle
                        if x.strip() and not x.strip().startswith("#")]
            pick = ask("  mp4 / mp3 > ")
            mode = "mp3" if pick.lower() in ("2", "mp3") else "mp4"
            for url in urls:
                if URL_RE.match(url):
                    grab(url, mode)
                else:
                    line(f"  skipped: {url[:60]}", "warn")
            ask("  press enter to refresh > ")
        else:
            line("  no such option", "warn")


def main() -> None:
    vt()
    if not YTDLP.exists():
        line("  bin\\yt-dlp.exe missing, run install.ps1 first", "warn")
        return
    boot()
    menu()


if __name__ == "__main__":
    try:
        main()
    except (ExitApp, KeyboardInterrupt):
        line("  see you, chef.", "soft")
