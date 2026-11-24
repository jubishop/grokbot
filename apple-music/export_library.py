#!/usr/bin/env python3
"""Export Apple Music library artists with song counts.

Reads secrets from environment variables (never printed):
  APPLE_MUSIC_P8          contents of the MusicKit AuthKey_*.p8 private key
  APPLE_MUSIC_KEY_ID      MusicKit key ID
  APPLE_MUSIC_TEAM_ID     Apple developer team ID
  APPLE_MUSIC_USER_TOKEN  Music User Token (expires roughly every 6 months)

Writes (next to this script):
  library-artists.txt   "<song count>\t<artist>" lines, most songs first
  last-updated          UTC ISO-8601 timestamp plus song/artist totals
"""
import base64, collections, datetime, json, os, sys, time
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://api.music.apple.com"


def env(name):
    v = os.environ.get(name, "").strip()
    if not v:
        sys.exit(f"::error::Missing required secret {name}")
    return v


def b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def developer_token():
    key = serialization.load_pem_private_key(env("APPLE_MUSIC_P8").encode(), None)
    now = int(time.time())
    head = b64(json.dumps({"alg": "ES256", "kid": env("APPLE_MUSIC_KEY_ID")}).encode())
    body = b64(json.dumps({"iss": env("APPLE_MUSIC_TEAM_ID"), "iat": now, "exp": now + 3600}).encode())
    signing_input = f"{head}.{body}"
    r, s = utils.decode_dss_signature(key.sign(signing_input.encode(), ec.ECDSA(hashes.SHA256())))
    return signing_input + "." + b64(r.to_bytes(32, "big") + s.to_bytes(32, "big"))


def main():
    headers = {"Authorization": "Bearer " + developer_token(),
               "Music-User-Token": env("APPLE_MUSIC_USER_TOKEN")}
    counts = collections.Counter()
    url = API + "/v1/me/library/songs?limit=100"
    while url:
        resp = None
        for attempt in range(4):
            try:
                resp = requests.get(url, headers=headers, timeout=30)
            except requests.RequestException as e:
                print(f"Request failed ({type(e).__name__}), retrying...", file=sys.stderr)
                time.sleep(2 ** attempt)
                continue
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            break
        if resp is None:
            sys.exit("::error::Apple Music API unreachable")
        if resp.status_code in (401, 403):
            sys.exit(f"::error::Apple Music API returned {resp.status_code}. The Music User Token "
                     "has probably expired (or the developer key is invalid). Sign in again in the "
                     "radio app and update the APPLE_MUSIC_USER_TOKEN secret.")
        if resp.status_code != 200:
            sys.exit(f"::error::Apple Music API error {resp.status_code}")
        j = resp.json()
        for item in j.get("data", []):
            counts[item.get("attributes", {}).get("artistName", "?")] += 1
        nxt = j.get("next")
        if not nxt:
            url = None
        elif "limit=" in nxt:
            url = API + nxt
        else:
            url = API + nxt + ("&" if "?" in nxt else "?") + "limit=100"

    if not counts:
        sys.exit("::error::Apple Music API returned an empty library; refusing to overwrite the export")
    songs, artists = sum(counts.values()), len(counts)
    rows = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].casefold()))
    with open(os.path.join(HERE, "library-artists.txt"), "w") as f:
        f.write("\n".join(f"{n}\t{a}" for a, n in rows) + "\n")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(os.path.join(HERE, "last-updated"), "w") as f:
        f.write(f"{stamp}\t{songs} songs\t{artists} artists\n")
    print(f"{songs} songs, {artists} artists")


if __name__ == "__main__":
    main()
