# grokbot

Helper jobs for Justin's Grok Bot. Each job lives in its own folder and runs on GitHub Actions; its output is committed here so Grok Bot can read it from `raw.githubusercontent.com`.

## Jobs

### `apple-music/` – weekly Apple Music library export

- Workflow: [`.github/workflows/apple-music-export.yml`](.github/workflows/apple-music-export.yml), Mondays 8:30 AM Pacific (16:30 UTC) or on demand.
- Output: [`apple-music/library-artists.txt`](apple-music/library-artists.txt) (`<song count><TAB><artist>`, most songs first) and [`apple-music/last-updated`](apple-music/last-updated).
- Secrets (repo Actions secrets, never committed): `APPLE_MUSIC_P8`, `APPLE_MUSIC_KEY_ID`, `APPLE_MUSIC_TEAM_ID`, `APPLE_MUSIC_USER_TOKEN`.
- If the run fails with 401/403, the Music User Token has expired: sign in again in the radio app and update `APPLE_MUSIC_USER_TOKEN`.

Grok Bot uses the artist list for its weekly Seattle concert check.
