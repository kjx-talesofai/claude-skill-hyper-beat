---
name: hyper-beat
description: "Free-licensed music search across Jamendo, Incompetech, ccMixter, and Internet Archive. Semantic mood→track matching. Triggers: search music, find music, royalty-free music, CC music, free music, 找音乐, 免费音乐, 搜索音乐, 配乐, BGM."
---

# Hyper Beat

Unified free-licensed music search across four Creative-Commons / Public-Domain providers. Use `hyper-beat` to discover music by mood, genre, feel, or keywords — then feed the results into a playlist composer or DJ system.

The bundled CLI is at `cli.py`. It has zero external dependencies (Python stdlib only).

## Quick start

```bash
hyper-beat search "ambient piano" --limit 10 --format json
```

### Multi-provider blend (recommended for broad coverage)

```bash
hyper-beat multi "dark electronic" --providers jamendo,incompetech,ccmixter,ia --limit 10 --format json
```

### Mood-driven search (use Incompetech for feel precision)

```bash
hyper-beat incompetech "calming peaceful melancholy" --limit 10 --format json
```

### Specific provider search

```bash
hyper-beat jamendo "piano acoustic folk" --limit 15 --format json
hyper-beat ccmixter "ambient chill experimental" --limit 10 --format json
hyper-beat ia "jazz electronic" --limit 10 --format json
```

## Providers

| Provider | Scale | License | Strengths | Weaknesses |
|---|---|---|---|---|
| **Jamendo** | 500K+ | Various CC | Genre tags, large catalog, CDN streaming | Noisy tags, no feel metadata |
| **Incompetech** | 1,442 | CC BY 4.0 | Feel/BPM/description for precise mood-matching | Small catalog, film-score bias |
| **ccMixter** | Tens of thousands | Various CC | Remix culture, experimental, niche genres | Requires Referer proxy for audio |
| **IA audio_music** | 505K+ | PD / CC | Massive scale, Internet Archive CDN | Weak metadata, unfiltered content |

## When to use each provider

- **Mood/feel driven requests**: search Jamendo + Incompetech together. Incompetech's `feel` field is extremely precise for emotions.
- **Genre-driven requests**: Jamendo for mainstream genres, IA audio_music for obscure ones.
- **Electronic/experimental**: Supplement with ccMixter (remix community) and IA netlabels.
- **Film-score/cinematic**: Incompetech first (it was literally written for film scoring), then Jamendo `filmscore` tag.
- **Niche/obscure**: ccMixter + IA audio_music.

## Common patterns

### Agentic DJ curation workflow

When building a playlist for a user, follow this pattern:

```bash
# 1. Interpret the request into musical attributes
# 2. Search at least 3 providers with different keyword strategies
hyper-beat jamendo "orchestral cinematic piano" --limit 15 --format json
hyper-beat incompetech "calming peaceful gentle" --limit 10 --format json
hyper-beat ccmixter "ambient acoustic folk" --limit 10 --format json

# 3. Evaluate candidates (name, artist, tags, duration, provider)
# 4. Compose the final playlist from selected track IDs
```

### Mood keyword guide

| User says | Jamendo tags | Incompetech feels | ccMixter tags |
|---|---|---|---|
| 治愈/calming | `ambient piano acoustic relaxing` | `calm peaceful relaxed soothing` | `ambient chill relaxing_music` |
| 活力/energetic | `energetic electronic dance rock` | `energetic driving action grooving` | `electronic dance house edm` |
| 暗黑/dark | `industrial ambient dark experimental` | `dark horror suspense mysterious` | `dark_ambient industrial experimental` |
| 史诗/epic | `orchestral cinematic soundtrack epic` | `epic action dramatic heroic` | `orchestral cinematic epic` |
| 快乐/happy | `upbeat pop folk indie` | `happy bouncy uplifting cheerful` | `upbeat cheerful party` |
| 伤感/sad | `melancholic sad ambient` | `sad melancholy emotional dark` | `melancholy sad emotional` |
| 专注/focus | `ambient instrumental chillout` | `calming relaxed peaceful` | `ambient chill instrumental study` |

### Abstract concept translation

Translate non-musical concepts into musical attributes before searching:

- "宫崎骏" → `orchestral piano acoustic cinematic nostalgic gentle`
- "赛博朋克" → `electronic synth industrial dark futuristic`
- "中世纪" → `folk lute medieval orchestral` → Incompetech: `ren faire medieval fantasy`
- "热带海滩" → `world reggae upbeat` / `happy bouncy tropical`

## Output format

All commands return unified JSON when `--format json` is used:

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

## Jamendo environment fallback

Jamendo requires `JAMENDO_CLIENT_ID`. The CLI includes a demo key fallback (`e7650837`) which may be rate-limited. If Jamendo fails, the multi-provider search automatically continues with remaining providers — **do not block on Jamendo** if it returns empty results.

## Constraints

- Audio must remain on provider CDNs (Jamendo, Incompetech, ccMixter, IA). Do not download or re-host.
- Respected Creative Commons attribution and license metadata.
- Search results can be noisy — inspect candidates, search again with revised terms if needed.
- ccMixter MP3s require a Referer header; use audio through the `/api/audio-proxy` endpoint when embedding in a page.
- Jamendo stream URLs may expire; re-search by track ID to refresh.
