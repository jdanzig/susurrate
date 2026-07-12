#!/usr/bin/env bash
# Benchmark local vs remote transcription, end to end, from THIS machine.
# Run it on the laptop: local = this machine's whisper; remote = POST to the mini.
#
#   contrib/benchmark.sh [runs] [remote_url]
#
# Needs: whisper-cli + a local model (SUSURRATE_MODEL or ggml-small.bin),
# ffmpeg, and for the remote half a reachable server + SUSURRATE_TOKEN.
set -u

RUNS="${1:-5}"
REMOTE="${2:-https://bots-mac-mini.tailc80c2f.ts.net}"
MODEL="${SUSURRATE_MODEL:-$HOME/.local/share/susurrate/models/ggml-small.bin}"
TOKEN="${SUSURRATE_TOKEN:-$(cat "$HOME/.local/share/susurrate/token" 2>/dev/null)}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# One representative ~4s clip, reused for every run so we compare like with like.
say -o "$TMP/c.aiff" "Hey, can you send me the quarterly report by Wednesday and loop in the whole team, thanks."
ffmpeg -y -loglevel error -i "$TMP/c.aiff" -ar 16000 -ac 1 "$TMP/c.wav"
ffmpeg -y -loglevel error -i "$TMP/c.aiff" -c:a aac -b:a 48k "$TMP/c.m4a"

# median of an array of seconds (bash + awk)
median() { printf '%s\n' "$@" | sort -n | awk '{a[NR]=$1} END{print (NR%2)? a[(NR+1)/2] : (a[NR/2]+a[NR/2+1])/2}'; }

echo "model: $MODEL"
echo "remote: $REMOTE"
echo "runs: $RUNS  (first run of each is a warm-up, excluded)"
echo

# --- LOCAL: this machine's whisper-cli, wall-clock per run ---
echo "== LOCAL (this machine) =="
local_times=()
for i in $(seq 0 "$RUNS"); do
  t=$( { /usr/bin/time -p whisper-cli -m "$MODEL" -f "$TMP/c.wav" -l auto \
        --no-timestamps --no-prints ; } 2>&1 >/dev/null | awk '/real/{print $2}')
  [ "$i" -eq 0 ] && { echo "  warm-up: ${t}s"; continue; }
  echo "  run $i: ${t}s"; local_times+=("$t")
done
LOCAL_MED=$(median "${local_times[@]}")
echo "  median: ${LOCAL_MED}s"
echo

# --- REMOTE: full round-trip to the server (upload + transcribe + text back) ---
echo "== REMOTE (${REMOTE}) =="
remote_times=()
for i in $(seq 0 "$RUNS"); do
  t=$(curl -s -o /dev/null -w '%{time_total}' -X POST \
       -H "Authorization: Bearer $TOKEN" --data-binary @"$TMP/c.m4a" \
       "$REMOTE/dictate")
  [ "$i" -eq 0 ] && { echo "  warm-up: ${t}s"; continue; }
  echo "  run $i: ${t}s"; remote_times+=("$t")
done
REMOTE_MED=$(median "${remote_times[@]}")
echo "  median: ${REMOTE_MED}s"
echo

echo "== RESULT =="
awk -v l="$LOCAL_MED" -v r="$REMOTE_MED" 'BEGIN{
  printf "  local  median: %.2fs\n  remote median: %.2fs\n", l, r
  if (l < r) printf "  -> LOCAL is faster by %.2fs\n", r-l
  else       printf "  -> REMOTE is faster by %.2fs\n", l-r
}'
