# 🎵 amusic-dl

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Dependency: yt--dlp](https://img.shields.io/badge/Dependency-yt--dlp-red.svg)](https://github.com/yt-dlp/yt-dlp)

**amusic-dl** is a lightweight, efficient Python tool to bridge the gap between Apple Music and your local library. It fetches high-quality metadata from Apple Music and downloads the corresponding audio from YouTube using `yt-dlp`, ensuring your music is perfectly tagged and organized.

---

## ⚡ Quick Install (One-Liner)

Copy and paste the command for your system into your terminal:

### 🐧 Linux / 🍎 macOS
```bash
python3 -m pip install git+https://github.com/uchumeow/amusic-dl.git
```

### 🪟 Windows (PowerShell)
```powershell
python -m pip install git+https://github.com/uchumeow/amusic-dl.git
```

> **Note:** Ensure you have [Python](https://www.python.org/) and [Git](https://git-scm.com/) installed and added to your PATH.

---

## ✨ Features

- **High-Quality Metadata:** Automatically fetches track titles, artists, albums, release years, and genres.
- **Smart Search:** Uses optimized YouTube search queries to find the best audio match.
- **Batch Downloading:** Supports entire **Albums** and **Playlists** with a single link.
- **Auto-Tagging:** Embeds ID3 tags and album artwork directly into the MP3 files.
- **Clean Organization:** Automatically creates folders for albums and playlists to keep your library tidy.

---

## 🚀 Getting Started

### Prerequisites

You'll need a few tools installed on your system:

1.  **Python 3.8+**
2.  **yt-dlp**: The engine for downloading.
3.  **FFmpeg**: Required for audio conversion and metadata embedding.

#### Installation on Arch Linux
```bash
sudo pacman -S yt-dlp ffmpeg python-requests
```

#### Installation on Ubuntu/Debian
```bash
sudo apt update
sudo apt install yt-dlp ffmpeg python3-requests
```

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/uchumeow/amusic-dl.git
   cd amusic-dl
   ```

2. (Optional) Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 📖 Usage

Run the script and follow the prompts, or pass a URL directly.

### Command Line Argument
```bash
python amusic_dl.py "https://music.apple.com/us/album/your-favorite-album/123456789"
```

### Interactive Mode
Simply run the script:
```bash
python amusic_dl.py
```
You will be prompted to paste your Apple Music link and choose a download directory (defaults to `~/Music`).

---

## 🛠️ How it Works

1.  **Scrape:** It extracts the unique ID from your Apple Music URL.
2.  **Lookup:** It hits the Apple Music/iTunes API to get the "canonical" metadata.
3.  **Search:** It searches YouTube for `Artist - Title`.
4.  **Process:** `yt-dlp` downloads the audio, while `ffmpeg` converts it to MP3 and writes the metadata tags.

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

This tool is for educational purposes and personal use only. Please support the artists by streaming their music on official platforms or purchasing their albums.
