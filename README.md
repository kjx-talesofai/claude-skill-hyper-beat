<p align="center">
  <img src="https://assets.hypersampling.com/hyper-sampling-2.jpg" alt="hyper-sampling" height="50"/>
  &nbsp;&nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/kjx-talesofai/claude-skill-hypersampling/master/neta_logo.png" alt="neta.art" height="50"/>
</p>

# hyper-beat

An Agent Skill for free-licensed music search across four providers (Jamendo, Incompetech, ccMixter, Internet Archive) with semantic mood-to-track matching and graceful fallback. Works with Claude Code, Codex CLI, Cohub, and any agent runtime that supports the SKILL.md standard.

## Why

Different music providers excel at different things. Incompetech has laser-precise feel metadata but only 1.4K tracks. Jamendo has 500K tracks but noisy genre tags. ccMixter has niche remix culture but needs a proxy for streaming. Internet Archive has massive scale but weak metadata. Rather than hardcoding one, hyper-beat searches all four in parallel and deduplicates — giving you the feel precision of Incompetech, the scale of Jamendo and IA, and the niche depth of ccMixter, in one unified result set.

## Install as skill

**Global (personal):**
```bash
cp -r . ~/.claude/skills/hyper-beat/
```

**Project-local (Cohub space):**
```bash
cp -r . .agents/skills/hyper-beat/
ln -sf $(pwd)/cli.py ~/.local/bin/hyper-beat
```

The skill auto-triggers on music-related queries. No slash command needed.

## Quick use

```bash
# Multi-provider blend (recommended)
hyper-beat multi "dark electronic" --providers jamendo,incompetech,ccmixter,ia

# Mood-driven search (Incompetech for feel precision)
hyper-beat incompetech "calming peaceful melancholy" --limit 10

# Single provider
hyper-beat jamendo "jazz acoustic piano" --limit 15 --format json
hyper-beat ccmixter "ambient chill experimental"
hyper-beat ia "electronic industrial" --limit 10
```

For full usage, see `SKILL.md` (loaded by Cohub Agent when the skill triggers).

## Providers

| Provider | Scale | License | Strengths | Audio |
|---|---|---|---|---|
| **Jamendo** | 500K+ | Various CC | Genre tags, large catalog | ✅ CDN |
| **Incompetech** | 1,442 | CC BY 4.0 | Feel/BPM for precise mood-matching | ✅ Direct |
| **ccMixter** | Tens of thousands | Various CC | Remix culture, experimental | ⚠️ Needs proxy |
| **IA audio_music** | 505K+ | PD / CC | Massive scale, IA CDN | ✅ CDN |

## Repo structure

```
.
├── SKILL.md              # Agent skill instructions (loaded at runtime)
├── cli.py                # Unified CLI — zero dependencies, Python stdlib
└── README.md             # This file
```

Provider clients are shared with the companion `dj-agent` project in the same Cohub space (`catalog/{jamendo,incompetech,ccmixter,ia}_client.py`). The CLI auto-resolves their location at runtime.

## Protocol

hyper-beat is designed for Cohub's Agent runtime. It follows the [Agent Skill Protocol](https://github.com/talesofai) — a `SKILL.md` frontmatter declares the skill, and the CLI is available to the Agent's `bash` tool via `hyper-beat`.

### Unified output format

All commands return the same JSON structure:

```json
{
  "providers": ["jamendo", "incompetech"],
  "query": "ambient piano",
  "count": 12,
  "tracks": [
    {
      "id": "123",
      "name": "Track Name",
      "artist": "Artist",
      "album": "Album",
      "duration": 240,
      "audio": "https://...",
      "image": "https://...",
      "tags": ["ambient", "piano"],
      "provider": "jamendo",
      "license": "CC BY-SA"
    }
  ]
}
```

### Fallback behavior

- Jamendo requires `JAMENDO_CLIENT_ID` env var. Falls back gracefully — `multi` continues with remaining providers.
- ccMixter MP3s need a Referer header. Proxy through the companion `dj-agent` server's `/api/audio-proxy` endpoint (which delegates to Cloudflare workers).
- All provider errors are non-fatal in `multi` mode. Stderr shows which providers were skipped.

## Constraints

- Audio must remain on provider CDNs. Do not download or re-host.
- Respect Creative Commons attribution. License metadata is included in every track.
- Jamendo stream URLs may expire; re-search by track ID to refresh.

## Getting Jamendo API Access

Jamendo requires a developer account for API access. It's free — sign up here:

https://developer.jamendo.com/v3.0

Once registered, set your Client ID:

```bash
export JAMENDO_CLIENT_ID="your_client_id"
```

Without it, hyper-beat falls back to its demo key (rate-limited) and gracefully skips Jamendo when it fails.

## Acknowledgments

This project would not exist without the artists and platforms that make their music freely available under Creative Commons and Public Domain licenses. We are grateful to:

- **Jamendo** and its community of independent musicians
- **Kevin MacLeod** (Incompetech), for a lifetime of film-scoring and an AI-accessible catalog
- **ccMixter** and the remix community, stewarded by Creative Commons
- **The Internet Archive**, for preserving and sharing our collective cultural heritage

All music remains on the providers' own CDNs. No audio is copied, re-hosted, or redistributed by this project.

## Disclaimer

This tool searches publicly available, freely-licensed music catalogs. It does not host, distribute, or license any audio content. All rights remain with the respective artists and platforms. Users are responsible for complying with each track's specific Creative Commons license terms — attribution, non-commercial restrictions, and share-alike requirements vary per track.

## Author

Built by [Jiaxin Kou](https://hypersampling.com) · [Neta Art](https://www.neta.art) · [GitHub](https://github.com/kjx-talesofai)

## License

MIT
