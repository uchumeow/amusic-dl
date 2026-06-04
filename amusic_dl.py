#!/usr/bin/env python3
"""
amusic-dl — Apple Music → YouTube → MP3 downloader
Supports: songs, albums, playlists
"""

import re
import sys
import json
import subprocess
import shutil
import shlex
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import requests

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://music.apple.com",
    "Referer": "https://music.apple.com/",
})

_am_token: str | None = None


# ─── Apple Music API token ────────────────────────────────────────────────────

def get_am_token() -> str | None:
    global _am_token
    if _am_token:
        return _am_token

    print("[*] Fetching Apple Music API token...")
    try:
        r = SESSION.get("https://music.apple.com/us/browse", timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"[!] Failed to load Apple Music: {e}")
        return None

    bundle_match = re.search(r'src="(/assets/index[^"]+\.js)"', r.text)
    if not bundle_match:
        print("[!] Couldn't find Apple Music JS bundle.")
        return None

    bundle_url = "https://music.apple.com" + bundle_match.group(1)
    try:
        js = SESSION.get(bundle_url, timeout=20)
        js.raise_for_status()
    except Exception as e:
        print(f"[!] Failed to fetch JS bundle: {e}")
        return None

    token_match = re.search(r'eyJh[A-Za-z0-9+/=_\-\.]{50,}', js.text)
    if not token_match:
        print("[!] Couldn't find API token in JS bundle.")
        return None

    _am_token = token_match.group(0)
    return _am_token


# ─── Apple Music API ──────────────────────────────────────────────────────────

def am_api_get(path: str, params: dict = None) -> dict | None:
    token = get_am_token()
    if not token:
        return None
    url = f"https://amp-api.music.apple.com{path}"
    try:
        r = SESSION.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[!] Apple Music API error: {e}")
        return None


def fetch_playlist(playlist_id: str, storefront: str = "us") -> tuple[str, list]:
    """Returns (playlist_name, tracks)."""
    data = am_api_get(f"/v1/catalog/{storefront}/playlists/{playlist_id}", params={"include": "tracks"})
    if not data or not data.get("data"):
        return ("playlist", [])

    playlist_attrs = data["data"][0].get("attributes", {})
    playlist_name  = playlist_attrs.get("name", "playlist")

    tracks = []
    rel = data["data"][0].get("relationships", {}).get("tracks", {})
    tracks += _parse_track_items(rel.get("data", []))

    # Pagination
    next_url = rel.get("next")
    while next_url:
        token = get_am_token()
        try:
            r = SESSION.get(
                f"https://amp-api.music.apple.com{next_url}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15
            )
            r.raise_for_status()
            page = r.json()
        except Exception:
            break
        tracks += _parse_track_items(page.get("data", []))
        next_url = page.get("next")

    return (playlist_name, tracks)


def _parse_track_items(items: list) -> list:
    tracks = []
    for item in items:
        attrs = item.get("attributes", {})
        if not attrs.get("name"):
            continue
        artwork = attrs.get("artwork", {}).get("url", "")
        artwork = artwork.replace("{w}", "600").replace("{h}", "600")
        tracks.append({
            "trackName":        attrs.get("name", ""),
            "artistName":       attrs.get("artistName", ""),
            "collectionName":   attrs.get("albumName", ""),
            "releaseDate":      attrs.get("releaseDate", ""),
            "primaryGenreName": (attrs.get("genreNames") or [""])[0],
            "trackNumber":      attrs.get("trackNumber"),
            "artworkUrl100":    artwork,
        })
    return tracks


# ─── URL parsing ──────────────────────────────────────────────────────────────

def parse_apple_music_url(url: str) -> dict | None:
    parsed = urlparse(url)
    if "music.apple.com" not in parsed.netloc:
        return None
    qs = parse_qs(parsed.query)
    track_id   = qs.get("i", [None])[0]
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    storefront = path_parts[0] if len(path_parts) > 0 else "us"
    kind       = path_parts[1] if len(path_parts) > 1 else None
    entity_id  = path_parts[-1] if path_parts else None
    return {"track_id": track_id, "entity_id": entity_id, "kind": kind, "storefront": storefront}


# ─── iTunes API ───────────────────────────────────────────────────────────────

def lookup_itunes_track(track_id: str) -> dict | None:
    try:
        r = requests.get(f"https://itunes.apple.com/lookup?id={track_id}&entity=song", timeout=10)
        r.raise_for_status()
        results = r.json().get("results", [])
        for item in results:
            if item.get("wrapperType") == "track":
                return item
        return results[0] if results else None
    except Exception as e:
        print(f"[!] iTunes API error: {e}")
        return None


def lookup_itunes_album(album_id: str) -> list:
    try:
        r = requests.get(f"https://itunes.apple.com/lookup?id={album_id}&entity=song", timeout=10)
        r.raise_for_status()
        results = r.json().get("results", [])
        return [item for item in results if item.get("wrapperType") == "track"]
    except Exception as e:
        print(f"[!] iTunes API error: {e}")
        return []


# ─── Metadata ─────────────────────────────────────────────────────────────────

def format_metadata(meta: dict) -> dict:
    artwork = meta.get("artworkUrl100") or ""
    artwork = artwork.replace("{w}", "600").replace("{h}", "600").replace("100x100", "600x600")
    return {
        "title":        meta.get("trackName") or meta.get("collectionName", "Unknown"),
        "artist":       meta.get("artistName", "Unknown Artist"),
        "album":        meta.get("collectionName", ""),
        "track_number": meta.get("trackNumber"),
        "year":         (meta.get("releaseDate") or "")[:4],
        "genre":        meta.get("primaryGenreName", ""),
        "artwork_url":  artwork,
    }


def safe_name(s: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", s).strip()


# ─── YouTube & download ───────────────────────────────────────────────────────

def find_youtube_url(query: str) -> str | None:
    cmd = ["yt-dlp", "--no-playlist", "--print", "webpage_url", "--no-warnings", f"ytsearch1:{query}"]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        url = result.stdout.strip()
        if not url.startswith("http"):
            if result.stderr.strip():
                print(f"[!] yt-dlp: {result.stderr.strip()}")
            return None
        return url
    except Exception as e:
        print(f"[!] YouTube search failed: {e}")
        return None


def download_mp3(youtube_url: str, meta: dict, output_dir: Path) -> bool:
    output_path = str(output_dir / f"{safe_name(meta['artist'])} - {safe_name(meta['title'])}.%(ext)s")

    pp_args = []
    for key, val in [("title", meta["title"]), ("artist", meta["artist"]),
                     ("album", meta["album"]), ("date", meta["year"]), ("genre", meta["genre"])]:
        if val:
            pp_args += ["--postprocessor-args", f"ffmpeg:-metadata {key}={shlex.quote(str(val))}"]
    if meta.get("track_number"):
        pp_args += ["--postprocessor-args", f"ffmpeg:-metadata track={shlex.quote(str(meta['track_number']))}"]

    cmd = [
        "yt-dlp", "--no-playlist", "-x",
        "--audio-format", "mp3", "--audio-quality", "0",
        "--embed-metadata", "--embed-thumbnail",
        *pp_args, "-o", output_path, youtube_url,
    ]
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def download_one(raw_meta: dict, output_dir: Path, index: int = None, total: int = None) -> bool:
    meta   = format_metadata(raw_meta)
    prefix = f"[{index}/{total}] " if index and total else ""
    print(f"\n{prefix}{meta['artist']} — {meta['title']}")
    yt_url = find_youtube_url(f"{meta['artist']} - {meta['title']}")
    if not yt_url:
        print("  [!] No YouTube result, skipping.")
        return False
    print(f"  YouTube: {yt_url}")
    ok = download_mp3(yt_url, meta, output_dir)
    print(f"  {'[✓] Done' if ok else '[✗] Failed'}")
    return ok


def download_batch(tracks: list, output_dir: Path):
    passed, failed = 0, 0
    for i, track in enumerate(tracks, 1):
        ok      = download_one(track, output_dir, index=i, total=len(tracks))
        passed += ok
        failed += not ok
        if i < len(tracks):
            time.sleep(1)
    print(f"\n[✓] Done — {passed} downloaded, {failed} failed")
    print(f"    Saved to: {output_dir}")


# ─── Deps ─────────────────────────────────────────────────────────────────────

def check_deps():
    missing = []
    if not shutil.which("yt-dlp"):
        missing.append("yt-dlp  (sudo pacman -S yt-dlp)")
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg  (sudo pacman -S ffmpeg)")
    if missing:
        print("[!] Missing dependencies:")
        for m in missing:
            print(f"    • {m}")
        sys.exit(1)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    check_deps()

    if len(sys.argv) > 1:
        am_url = sys.argv[1].strip()
    else:
        am_url = input("Apple Music URL: ").strip()

    if am_url in ("--help", "-h"):
        print("Usage: amusic-dl \"<apple-music-url>\"")
        print("Supports: songs, albums, playlists")
        sys.exit(0)

    if not am_url:
        print("[!] No URL provided.")
        sys.exit(1)

    ids = parse_apple_music_url(am_url)
    if not ids:
        print("[!] That doesn't look like an Apple Music link.")
        sys.exit(1)

    default_dir = Path.home() / "Music"
    raw_dir     = input(f"Save to (default: {default_dir}): ").strip()
    base_dir    = Path(raw_dir).expanduser() if raw_dir else default_dir
    base_dir.mkdir(parents=True, exist_ok=True)

    kind       = ids.get("kind")
    storefront = ids.get("storefront", "us")

    # ── Playlist ──
    if kind == "playlist":
        print("\n[*] Fetching playlist tracks...")
        playlist_name, tracks = fetch_playlist(ids["entity_id"], storefront)
        if not tracks:
            print("[!] Couldn't retrieve playlist tracks.")
            sys.exit(1)

        output_dir = base_dir / safe_name(playlist_name)
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"[*] Playlist : {playlist_name}")
        print(f"[*] Tracks   : {len(tracks)}")
        print(f"[*] Folder   : {output_dir}\n")
        for i, t in enumerate(tracks, 1):
            m = format_metadata(t)
            print(f"  {i:>2}. {m['artist']} — {m['title']}")

        proceed = input(f"\nDownload all {len(tracks)} tracks? [Y/n]: ").strip().lower()
        if proceed == "n":
            sys.exit(0)
        download_batch(tracks, output_dir)

    # ── Single track ──
    elif ids.get("track_id"):
        print("\n[*] Fetching track metadata...")
        raw_meta = lookup_itunes_track(ids["track_id"])
        if not raw_meta:
            print("[!] Couldn't find metadata.")
            sys.exit(1)
        meta = format_metadata(raw_meta)
        print(f"\n  Title  : {meta['title']}")
        print(f"  Artist : {meta['artist']}")
        print(f"  Album  : {meta['album']}")
        print(f"  Year   : {meta['year']}")
        print(f"  Genre  : {meta['genre']}")
        print("\n[*] Searching YouTube...")
        yt_url = find_youtube_url(f"{meta['artist']} - {meta['title']}")
        if not yt_url:
            print("[!] No YouTube result found.")
            sys.exit(1)
        print(f"    Found: {yt_url}")
        proceed = input("\nProceed with download? [Y/n]: ").strip().lower()
        if proceed == "n":
            sys.exit(0)
        print()
        if download_mp3(yt_url, meta, base_dir):
            print(f"\n[✓] Done! Saved to: {base_dir}")
        else:
            print("\n[✗] Download failed.")
            sys.exit(1)

    # ── Album ──
    elif ids.get("entity_id"):
        print("\n[*] Fetching album tracks...")
        tracks = lookup_itunes_album(ids["entity_id"])
        if not tracks:
            print("[!] Couldn't find album tracks.")
            sys.exit(1)
        meta0 = format_metadata(tracks[0])

        output_dir = base_dir / safe_name(f"{meta0['artist']} - {meta0['album']}")
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n  Album  : {meta0['album']}")
        print(f"  Artist : {meta0['artist']}")
        print(f"  Tracks : {len(tracks)}")
        print(f"  Folder : {output_dir}\n")
        for t in tracks:
            print(f"  {str(t.get('trackNumber', '?')):>2}. {t.get('trackName', '?')}")

        proceed = input(f"\nDownload all {len(tracks)} tracks? [Y/n]: ").strip().lower()
        if proceed == "n":
            sys.exit(0)
        download_batch(tracks, output_dir)

    else:
        print("[!] Unrecognized URL format.")
        sys.exit(1)


if __name__ == "__main__":
    main()
