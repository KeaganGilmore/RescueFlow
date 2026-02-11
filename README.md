<div align="center">

# 🌊 RescueFlow Academy

**A modern, AI-powered learning platform for NSRI training material.**

[![License: CC BY-NC-ND 4.0](https://img.shields.io/badge/License-CC%20BY--NC--ND%204.0-lightgrey.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-KeaganGilmore-181717?logo=github)](https://github.com/KeaganGilmore)
[![Discord](https://img.shields.io/badge/Discord-keagan2980-5865F2?logo=discord&logoColor=white)](https://discord.com/users/keagan2980)

</div>

---

> **⚠️ Disclaimer:** This project is **not affiliated with, endorsed by, or officially connected to** the National Sea Rescue Institute (NSRI) in any way. I'm simply a volunteer who wanted a faster, more modern interface to study the training material. All course content is derived from NSRI's publicly available training PDFs.

---

## What is RescueFlow?

RescueFlow takes NSRI training PDFs and transforms them into a structured, interactive learning platform — complete with:

- 📚 **Course Catalog** — Browse available modules with AI-generated thumbnails and progress tracking
- 📖 **Clean Reading Experience** — Markdown-rendered content with proper typography, images, and formatting
- 🧠 **Auto-Generated Quizzes** — AI creates knowledge-check questions for educational sections (skips reference pages)
- 💾 **Progress Tracking** — Your completed chapters are saved locally in the browser
- 🖼️ **Smart Image Handling** — Deduplicates repeated header/footer images, sanitizes filenames for web

## Architecture

```
RescueFlow/
├── pdfs/                  # Drop your training PDFs here
├── build.py               # AI-powered build script (GPT-4o + DALL-E 3)
├── docs/                  # Static site (GitHub Pages ready)
│   ├── index.html         # Single-page learning application
│   ├── course_data.js     # Generated course data (JSON)
│   └── images/            # Extracted + generated images
│       └── thumbnails/    # AI-generated course covers
├── run_local.bat          # Quick-start local server (Windows)
├── LICENSE                # CC BY-NC-ND 4.0
└── DONATIONS.md           # Support the project
```

## Getting Started

### Prerequisites

- **Python 3.10+**
- **OpenAI API Key** ([get one here](https://platform.openai.com/api-keys))

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/KeaganGilmore/RescueFlow.git
cd RescueFlow

# 2. Install dependencies
pip install pymupdf openai python-dotenv httpx

# 3. Add your API key
echo OPENAI_API_KEY=sk-your-key-here > .env

# 4. Add PDFs
# Place your NSRI training PDFs in the pdfs/ folder

# 5. Build the course data
python build.py
```

### Running Locally

**Windows:**
```bash
run_local.bat
# Opens http://localhost:8000
```

**Any OS:**
```bash
python -m http.server 8000 --directory docs
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

## Build Script Details

The `build.py` script does the following:

| Step | What It Does | API Cost |
|------|-------------|----------|
| **PDF Extraction** | Extracts text, images, and links from each page | Free |
| **Image Dedup** | MD5 hashing to skip repeated headers/footers | Free |
| **Content Processing** | GPT-4o converts each page to structured Markdown with semantic titles | ~$0.01/page |
| **Quiz Generation** | GPT-4o creates quizzes for educational content only | Included above |
| **Thumbnail Generation** | DALL-E 3 creates a professional cover image per course | ~$0.04/thumbnail |

**Thumbnail caching:** Thumbnails are cached in `docs/images/thumbnails/`. Delete the PNG to regenerate a specific one. The content processing always runs fresh to pick up any prompt improvements.

## Deploying to GitHub Pages

The `docs/` folder is ready for GitHub Pages:

1. Push to GitHub
2. Go to **Settings → Pages**
3. Set source to `Deploy from a branch`, branch `main`, folder `/docs`
4. Your site will be live at `https://yourusername.github.io/RescueFlow/`

## Contributing

Contributions are welcome! If you're also an NSRI volunteer and want to help improve the platform:

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-improvement`)
3. Commit your changes
4. Push and open a Pull Request

## Contact

| | |
|---|---|
| **Author** | Keagan Gilmore |
| **Email** | [keagangilmore@gmail.com](mailto:keagangilmore@gmail.com) |
| **GitHub** | [github.com/KeaganGilmore](https://github.com/KeaganGilmore) |
| **Discord** | keagan2980 |

## License

This project is licensed under [CC BY-NC-ND 4.0](LICENSE) — you may share it with attribution for non-commercial purposes, but no derivatives are permitted.

---

<div align="center">
  <sub>Built with ❤️ for the sea rescue community</sub>
</div>
