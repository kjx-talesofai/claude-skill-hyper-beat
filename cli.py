#!/usr/bin/env python3
"""
Hyper Beat — unified free-licensed music search across 4 providers.

Usage:
  hyper-beat search "ambient piano" --limit 10
  hyper-beat multi "dark electronic" --providers jamendo,incompetech,ccmixter,ia
  hyper-beat jamendo "jazz acoustic" --limit 15
  hyper-beat incompetech "calming peaceful" --limit 10
  hyper-beat ccmixter "ambient chill" --limit 10
  hyper-beat ia "electronic experimental" --limit 10

Fully self-contained. Zero external dependencies — Python stdlib only.
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.parse

JAMENDO_CLIENT_ID = os.environ.get("JAMENDO_CLIENT_ID", "e7650837")
JAMENDO_API = "https://api.jamendo.com/v3.0"
INCOMPETECH_BASE = "https://incompetech.com/music/royalty-free"
CCMIXTER_BASE = "https://ccmixter.org"
IA_BASE = "https://archive.org"
TIMEOUT = 20
USER_AGENT = "hyper-beat/1.0"


def _fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read())


def _fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


# ── Jamendo (direct API, no DB) ──────────────────────────

def search_jamendo(keywords, limit=10):
    try:
        params = urllib.parse.urlencode({
            "client_id": JAMENDO_CLIENT_ID,
            "format": "json",
            "fuzzytags": " ".join(keywords),
            "limit": min(limit, 50),
            "order": "popularity_total",
            "audioformat": "mp32",
            "include": "musicinfo",
        })
        data = _fetch_json(f"{JAMENDO_API}/tracks/?{params}")
        tracks = []
        for t in data.get("results", [])[:limit]:
            tags = ((t.get("musicinfo", {}) or {}).get("tags", {}) or {}).get("genres", []) or []
            tracks.append({
                "id": str(t.get("id", "")),
                "name": t.get("name", ""),
                "artist": t.get("artist_name", ""),
                "album": t.get("album_name", ""),
                "duration": int(t.get("duration", 0)),
                "audio": t.get("audio", ""),
                "image": t.get("image") or t.get("album_image", ""),
                "tags": tags,
                "provider": "jamendo",
                "license": t.get("license_ccurl", "CC"),
            })
        return tracks
    except Exception as e:
        print(f"[hyper-beat] Jamendo search failed: {e}", file=sys.stderr)
        return []


# ── Incompetech (in-memory catalog search) ───────────────

_INCOMPETECH_CACHE = {"pieces": None, "genres": None}


def _load_incompetech():
    if _INCOMPETECH_CACHE["pieces"] is None:
        _INCOMPETECH_CACHE["pieces"] = _fetch_json(f"{INCOMPETECH_BASE}/pieces.json")
        genre_list = _fetch_json(f"{INCOMPETECH_BASE}/genre.json")
        _INCOMPETECH_CACHE["genres"] = {int(g["id"]): g["genre"] for g in genre_list}
    return _INCOMPETECH_CACHE["pieces"], _INCOMPETECH_CACHE["genres"]


def search_incompetech(keywords, limit=10):
    try:
        pieces, genres = _load_incompetech()
        results = []
        for p in pieces:
            title = (p.get("title") or "").lower()
            feel = (p.get("feel") or "").lower()
            desc = (p.get("description") or "").lower()
            genre_name = genres.get(int(p.get("genre", 0)), "").lower()
            score = 0
            for kw in keywords:
                kwl = kw.lower()
                if kwl in title: score += 3
                if kwl in feel: score += 3
                if kwl in desc: score += 2
                if kwl in genre_name: score += 2
            if score > 0:
                p["_score"] = score
                p["_genre_name"] = genre_name
                results.append(p)
        results.sort(key=lambda x: x["_score"], reverse=True)
        tracks = []
        for p in results[:limit]:
            filename = urllib.parse.quote(p["filename"])
            dur = p.get("length", "00:00")
            total_sec = sum(int(x) * 60**i for i, x in enumerate(reversed(dur.split(":"))))
            tags = [t for t in [p.get("feel", ""), p.get("_genre_name", "")] if t]
            tracks.append({
                "id": p.get("uuid", ""),
                "name": p.get("title", "").strip(),
                "artist": "Kevin MacLeod",
                "album": "",
                "duration": total_sec,
                "audio": f"{INCOMPETECH_BASE}/mp3-royaltyfree/{filename}",
                "image": "",
                "tags": tags or ["instrumental"],
                "provider": "incompetech",
                "license": "https://creativecommons.org/licenses/by/4.0/",
            })
        return tracks
    except Exception as e:
        print(f"[hyper-beat] Incompetech search failed: {e}", file=sys.stderr)
        return []


# ── ccMixter (XML query API) ─────────────────────────────

def _ccmixter_stream_url(track_id):
    try:
        m3u = _fetch_text(f"{CCMIXTER_BASE}/api/query/stream.m3u?f=m3u&ids={track_id}")
        for line in m3u.split("\n"):
            if line.strip().startswith("http"):
                return line.strip()
    except Exception:
        pass
    return ""


def search_ccmixter(keywords, limit=10):
    try:
        tag_str = ",".join(keywords[:5])
        url = (f"{CCMIXTER_BASE}/api/query?datasource=uploads&type=api"
               f"&tags={urllib.parse.quote(tag_str)}&limit={limit * 2}&f=xml")
        xml_text = _fetch_text(url)
        rows = re.findall(r"<tr>(.*?)</tr>", xml_text, re.DOTALL)
        tracks = []
        for row in rows[:limit]:
            cols = re.findall(r"<td>(.*?)</td>", row, re.DOTALL)
            if len(cols) < 15:
                continue
            raw_tags = [t.strip() for t in cols[4].split(",") if t.strip()]
            track_id = cols[0].strip()
            tracks.append({
                "id": track_id,
                "name": cols[1].strip() or "Untitled",
                "artist": cols[7].strip() or cols[3].strip(),
                "album": "",
                "duration": 0,
                "audio": _ccmixter_stream_url(track_id),
                "image": "",
                "tags": raw_tags[:5],
                "provider": "ccmixter",
                "license": cols[10].strip() if len(cols) > 10 else "CC",
            })
        return tracks
    except Exception as e:
        print(f"[hyper-beat] ccMixter search failed: {e}", file=sys.stderr)
        return []


# ── Internet Archive (advanced search + files) ───────────

def search_ia(keywords, limit=10, collection="audio_music"):
    try:
        q_parts = [f"collection:{collection}"]
        for kw in keywords[:4]:
            q_parts.append(f"(subject:{kw} OR title:{kw})")
        q = " AND ".join(q_parts)
        params_list = [
            ("q", q), ("sort[]", "downloads desc"),
            ("rows", str(min(limit * 3, 100))), ("output", "json"),
        ]
        for field in ["identifier", "title", "creator", "subject"]:
            params_list.append(("fl[]", field))
        qs = urllib.parse.urlencode(params_list)
        data = _fetch_json(f"{IA_BASE}/advancedsearch.php?{qs}")
        docs = data.get("response", {}).get("docs", [])
        tracks = []
        for doc in docs:
            if len(tracks) >= limit:
                break
            identifier = doc.get("identifier", "")
            if not identifier:
                continue
            try:
                files_data = _fetch_json(f"{IA_BASE}/metadata/{identifier}/files")
                files = files_data if isinstance(files_data, list) else files_data.get("result", [])
            except Exception:
                continue
            mp3 = None
            for f in (files or []):
                name = (f.get("name") or "").lower()
                fmt = (f.get("format") or "").lower()
                if ".mp3" in name or "mp3" in fmt:
                    mp3 = f
                    break
            if not mp3:
                continue
            filename = mp3.get("name", "")
            tracks.append({
                "id": f"{identifier}/{filename}",
                "name": mp3.get("title") or doc.get("title", "") or filename,
                "artist": doc.get("creator", "") or "Unknown",
                "album": "",
                "duration": 0,
                "audio": f"{IA_BASE}/download/{identifier}/{urllib.parse.quote(filename)}",
                "image": "",
                "tags": (doc.get("subject", []) or [])[:5] if isinstance(doc.get("subject"), list) else [],
                "provider": "ia",
                "license": "Public Domain / CC",
            })
        return tracks
    except Exception as e:
        print(f"[hyper-beat] IA search failed: {e}", file=sys.stderr)
        return []


PROVIDERS = {
    "jamendo": search_jamendo,
    "incompetech": search_incompetech,
    "ccmixter": search_ccmixter,
    "ia": search_ia,
}

# ── CLI commands ─────────────────────────────────────────


def cmd_search(args):
    provider = args.provider or "jamendo"
    keywords = args.query.split() if args.query else []
    fn = PROVIDERS.get(provider)
    if not fn:
        print(f"Unknown provider: {provider}. Choices: {', '.join(PROVIDERS)}", file=sys.stderr)
        sys.exit(1)
    tracks = fn(keywords, limit=args.limit)
    output = {"providers": [provider], "query": args.query, "count": len(tracks), "tracks": tracks}
    _emit(output, args.format)


def cmd_multi(args):
    wanted = [p.strip() for p in (args.providers or "jamendo,incompetech,ccmixter,ia").split(",")]
    keywords = args.query.split() if args.query else []
    all_tracks = []
    used = []
    for name in wanted:
        fn = PROVIDERS.get(name)
        if not fn:
            print(f"[hyper-beat] skipping unknown provider: {name}", file=sys.stderr)
            continue
        tracks = fn(keywords, limit=args.limit)
        all_tracks.extend(tracks)
        used.append(name)
    seen = set()
    unique = []
    for t in all_tracks:
        key = (t["name"].lower(), t["artist"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(t)
    output = {"providers": used, "query": args.query, "count": len(unique), "tracks": unique[:args.limit]}
    _emit(output, args.format)


def _emit(output, fmt):
    if fmt == "json":
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return
    print(f"🎵 {', '.join(output['providers'])}: {len(output['tracks'])} tracks for \"{output['query']}\"")
    for t in output["tracks"]:
        dur = f"{t['duration']//60}:{t['duration']%60:02d}" if t.get("duration") else "?:??"
        tags = " · ".join((t.get("tags") or [])[:3])
        print(f"  [{t['provider'][:4]:4s}] {t['id'][:12]:>12}  {t['name'][:35]:<35}  {t['artist'][:22]:<22}  {dur}  {tags}")


def main():
    parser = argparse.ArgumentParser(
        description="Hyper Beat — free-licensed music search across 4 providers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("search", help="Search a single music provider")
    p.add_argument("query", nargs="?")
    p.add_argument("--provider", choices=list(PROVIDERS), default="jamendo")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--format", choices=["json", "text"], default="text")

    p = sub.add_parser("multi", help="Search across multiple providers with graceful fallback")
    p.add_argument("query", nargs="?")
    p.add_argument("--providers", default="jamendo,incompetech,ccmixter,ia")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--format", choices=["json", "text"], default="text")

    for name in PROVIDERS:
        p = sub.add_parser(name, help=f"Search {name} directly")
        p.add_argument("query", nargs="?")
        p.add_argument("--limit", type=int, default=10)
        p.add_argument("--format", choices=["json", "text"], default="text")

    args = parser.parse_args()

    if args.command == "search":
        cmd_search(args)
    elif args.command == "multi":
        cmd_multi(args)
    elif args.command in PROVIDERS:
        args.provider = args.command
        cmd_search(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
