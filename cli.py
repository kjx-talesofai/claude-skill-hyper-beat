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

Zero external dependencies. Python stdlib only.
"""

import argparse
import json
import os
import sys

# Find the dj-agent project root to import catalog clients.
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))


def _find_project_root(start_dir):
    """Walk up until we find a directory containing catalog/jamendo_client.py."""
    d = start_dir
    while d != "/":
        if os.path.isfile(os.path.join(d, "catalog", "jamendo_client.py")):
            return d
        d = os.path.dirname(d)
    for candidate in ["/workspace/dj-agent", os.path.expanduser("~/dj-agent")]:
        if os.path.isfile(os.path.join(candidate, "catalog", "jamendo_client.py")):
            return candidate
    raise RuntimeError(
        "Cannot find dj-agent project root. "
        "hyper-beat requires catalog/{jamendo,incompetech,ccmixter,ia}_client.py."
    )


PROJECT_ROOT = _find_project_root(SKILL_DIR)
sys.path.insert(0, PROJECT_ROOT)

from catalog.jamendo_client import JamendoClient
from catalog.incompetech_client import IncompetechClient
from catalog.ccmixter_client import CcMixterClient
from catalog.ia_client import IAClient

JAMENDO_CLIENT_ID = os.environ.get("JAMENDO_CLIENT_ID", "e7650837")
DB_PATH = os.path.join(PROJECT_ROOT, "data", "catalog.db")

# ── Provider search functions ────────────────────────────

def search_jamendo(keywords, limit=10):
    """Search Jamendo. Returns empty list on failure (graceful fallback)."""
    try:
        client = JamendoClient(JAMENDO_CLIENT_ID, DB_PATH)
        result = client.search_tracks(
            fuzzytags=keywords,
            limit=min(limit, 50),
            order="popularity_total",
            audioformat="mp32",
        )
        tracks = []
        for t in result.get("results", [])[:limit]:
            musicinfo = (t.get("musicinfo", {}) or {}).get("tags", {}) or {}
            tags = musicinfo.get("genres", []) or []
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


def search_incompetech(keywords, limit=10):
    """Search Incompetech by feel keywords. Returns empty list on failure."""
    try:
        client = IncompetechClient()
        pieces = client.search(keywords, limit=limit)
        return [client.to_track(p) for p in pieces]
    except Exception as e:
        print(f"[hyper-beat] Incompetech search failed: {e}", file=sys.stderr)
        return []


def search_ccmixter(keywords, limit=10):
    """Search ccMixter by tags. Returns empty list on failure."""
    try:
        client = CcMixterClient()
        items = client.search(keywords, limit=limit)
        return [client.to_track(i) for i in items]
    except Exception as e:
        print(f"[hyper-beat] ccMixter search failed: {e}", file=sys.stderr)
        return []


def search_ia(keywords, limit=10):
    """Search Internet Archive audio_music. Returns empty list on failure."""
    try:
        client = IAClient("audio_music")
        items = client.search(keywords, limit=limit)
        tracks = []
        for item in items:
            mp3s = client.get_mp3_files(item["id"])
            if mp3s:
                tracks.append(client.to_track(item, mp3s[0]))
        return tracks[:limit]
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
    """Single-provider search."""
    provider = args.provider or "jamendo"
    keywords = args.query.split() if args.query else []
    fn = PROVIDERS.get(provider)
    if not fn:
        print(f"Unknown provider: {provider}. Choices: {', '.join(PROVIDERS)}", file=sys.stderr)
        sys.exit(1)
    tracks = fn(keywords, limit=args.limit)
    output = {
        "providers": [provider],
        "query": args.query,
        "count": len(tracks),
        "tracks": tracks,
    }
    if args.format == "json":
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        _print_text(output)


def cmd_multi(args):
    """Multi-provider blended search, graceful fallback on each."""
    wanted = [p.strip() for p in (args.providers or "jamendo,incompetech,ccmixter,ia").split(",")]
    keywords = args.query.split() if args.query else []
    all_tracks = []
    used = []
    for name in wanted:
        fn = PROVIDERS.get(name)
        if not fn:
            print(f"[hyper-beat] skipping unknown provider: {name}", file=sys.stderr)
            continue
        try:
            tracks = fn(keywords, limit=args.limit)
            all_tracks.extend(tracks)
            used.append(name)
        except Exception as e:
            print(f"[hyper-beat] provider {name} skipped: {e}", file=sys.stderr)
    # Deduplicate by (name, artist)
    seen = set()
    unique = []
    for t in all_tracks:
        key = (t["name"].lower(), t["artist"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(t)
    output = {
        "providers": used,
        "query": args.query,
        "count": len(unique),
        "tracks": unique[:args.limit],
    }
    if args.format == "json":
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        _print_text(output)


def _print_text(output):
    providers = output["providers"]
    tracks = output["tracks"]
    print(f"🎵 {', '.join(providers)}: {len(tracks)} tracks for \"{output['query']}\"")
    for t in tracks:
        dur = f"{t['duration']//60}:{t['duration']%60:02d}" if t.get("duration") else "?:??"
        tags = " · ".join((t.get("tags") or [])[:3])
        pid = t["id"][:12]
        print(f"  [{t['provider'][:4]:4s}] {pid:>12}  {t['name'][:35]:<35}  {t['artist'][:22]:<22}  {dur}  {tags}")


# ── Main ─────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Hyper Beat — free-licensed music search across 4 providers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    # search (single provider)
    p = sub.add_parser("search", help="Search a single music provider")
    p.add_argument("query", nargs="?", help="Search terms (e.g. 'ambient piano')")
    p.add_argument("--provider", choices=list(PROVIDERS), default="jamendo",
                   help="Which provider to use")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--format", choices=["json", "text"], default="text")

    # multi (blended)
    p = sub.add_parser("multi", help="Search across multiple providers with graceful fallback")
    p.add_argument("query", nargs="?", help="Search terms")
    p.add_argument("--providers", default="jamendo,incompetech,ccmixter,ia",
                   help="Comma-separated provider list")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--format", choices=["json", "text"], default="text")

    # Provider-specific shortcuts
    for name in PROVIDERS:
        p = sub.add_parser(name, help=f"Search {name} directly")
        p.add_argument("query", nargs="?", help="Search terms")
        p.add_argument("--limit", type=int, default=10)
        p.add_argument("--format", choices=["json", "text"], default="text")

    args = parser.parse_args()

    if args.command == "search":
        cmd_search(args)
    elif args.command == "multi":
        cmd_multi(args)
    elif args.command in PROVIDERS:
        # Provider shortcut: rewrite as search with that provider
        args.provider = args.command
        cmd_search(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
