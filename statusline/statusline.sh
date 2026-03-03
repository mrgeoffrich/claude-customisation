#!/bin/bash
input=$(cat)

MODEL=$(echo "$input" | jq -r '.model.display_name')
DIR=$(echo "$input" | jq -r '.workspace.current_dir')
PCT=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)

CYAN='\033[36m'; GREEN='\033[32m'; YELLOW='\033[33m'; RED='\033[31m'; RESET='\033[0m'
DIM='\033[2m'; MAGENTA='\033[35m'; LTBLUE='\033[38;5;117m'

# Pick bar color based on context usage
if [ "$PCT" -ge 90 ]; then BAR_COLOR="$RED"
elif [ "$PCT" -ge 70 ]; then BAR_COLOR="$YELLOW"
else BAR_COLOR="$GREEN"; fi

FILLED=$((PCT / 10)); EMPTY=$((10 - FILLED))
BAR=$(printf "%${FILLED}s" | tr ' ' '█')$(printf "%${EMPTY}s" | tr ' ' '░')

BRANCH=""
git rev-parse --git-dir > /dev/null 2>&1 && BRANCH="${LTBLUE}⎇ $(git branch --show-current 2>/dev/null)${RESET}"

# ── Account usage limits (5h + 7d) ──────────────────────────────────────────
# Cache for 2 minutes to avoid hammering the API on every statusline refresh
CACHE_FILE="/tmp/claude-usage-cache.json"
CACHE_TTL=120

get_token() {
  # Linux: credentials in plain text file
  if [ -f "$HOME/.claude/.credentials.json" ]; then
    jq -r '.claudeAiOauth.accessToken // empty' "$HOME/.claude/.credentials.json" 2>/dev/null
    return
  fi
  # macOS: credentials in Keychain
  if command -v security &>/dev/null; then
    local creds
    creds=$(security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null)
    [ -n "$creds" ] && echo "$creds" | jq -r '.claudeAiOauth.accessToken // empty' 2>/dev/null
  fi
}

fetch_usage() {
  local token="$1"
  curl -s --max-time 4 "https://api.anthropic.com/api/oauth/usage" \
    -H "Authorization: Bearer $token" \
    -H "anthropic-beta: oauth-2025-04-20" \
    -H "Content-Type: application/json" 2>/dev/null
}

usage_color() {
  local pct="$1"
  if [ "$pct" -ge 90 ]; then echo "$RED"
  elif [ "$pct" -ge 70 ]; then echo "$YELLOW"
  else echo "$GREEN"; fi
}

# Convert ISO reset time to compact relative string (e.g. "2h13m", "4d3h")
format_reset() {
  local iso="$1"
  [ -z "$iso" ] && return
  local reset_epoch now_epoch diff_s
  reset_epoch=$(date -juf "%Y-%m-%dT%H:%M:%S" "${iso%%.*}" +%s 2>/dev/null) || return
  now_epoch=$(date -u +%s)
  diff_s=$((reset_epoch - now_epoch))
  [ "$diff_s" -le 0 ] && { echo "now"; return; }
  local days=$((diff_s / 86400)) hrs=$(( (diff_s % 86400) / 3600 )) mins=$(( (diff_s % 3600) / 60 ))
  if [ "$days" -gt 0 ]; then printf "%d:%02d:%02d" "$days" "$hrs" "$mins"
  else printf "%d:%02d" "$hrs" "$mins"
  fi
}

USAGE_SEGMENT=""

# Use cache if fresh, otherwise fetch
if [ -f "$CACHE_FILE" ]; then
  CACHE_AGE=$(( $(date +%s) - $(date -r "$CACHE_FILE" +%s 2>/dev/null || echo 0) ))
else
  CACHE_AGE=$((CACHE_TTL + 1))
fi

if [ "$CACHE_AGE" -gt "$CACHE_TTL" ]; then
  TOKEN=$(get_token)
  if [ -n "$TOKEN" ]; then
    RESP=$(fetch_usage "$TOKEN")
    if echo "$RESP" | jq -e '.five_hour' &>/dev/null; then
      echo "$RESP" > "$CACHE_FILE"
    fi
  fi
fi

if [ -f "$CACHE_FILE" ]; then
  FIVE_H_RAW=$(jq -r '.five_hour.utilization // empty' "$CACHE_FILE" 2>/dev/null)
  SEVEN_D_RAW=$(jq -r '.seven_day.utilization // empty' "$CACHE_FILE" 2>/dev/null)
  FIVE_H_RESET=$(jq -r '.five_hour.resets_at // empty' "$CACHE_FILE" 2>/dev/null)
  SEVEN_D_RESET=$(jq -r '.seven_day.resets_at // empty' "$CACHE_FILE" 2>/dev/null)

  if [ -n "$FIVE_H_RAW" ] && [ -n "$SEVEN_D_RAW" ]; then
    FIVE_H_PCT=$(echo "$FIVE_H_RAW" | cut -d. -f1)
    SEVEN_D_PCT=$(echo "$SEVEN_D_RAW" | cut -d. -f1)

    FIVE_H_COLOR=$(usage_color "${FIVE_H_PCT:-0}")
    SEVEN_D_COLOR=$(usage_color "${SEVEN_D_PCT:-0}")

    FIVE_H_ETA=$(format_reset "$FIVE_H_RESET")
    SEVEN_D_ETA=$(format_reset "$SEVEN_D_RESET")

    FIVE_H_ETA_STR=""
    [ -n "$FIVE_H_ETA" ] && FIVE_H_ETA_STR="${DIM}~${FIVE_H_ETA}${RESET}"
    SEVEN_D_ETA_STR=""
    [ -n "$SEVEN_D_ETA" ] && SEVEN_D_ETA_STR="${DIM}~${SEVEN_D_ETA}${RESET}"

    USAGE_SEGMENT=" | ${MAGENTA}5h:${RESET}${FIVE_H_COLOR}${FIVE_H_PCT}%${RESET}${FIVE_H_ETA_STR} ${MAGENTA}7d:${RESET}${SEVEN_D_COLOR}${SEVEN_D_PCT}%${RESET}${SEVEN_D_ETA_STR}"
  fi
fi

echo -e "${CYAN}[$MODEL]${RESET} ${DIR##*/} $BRANCH | ${BAR_COLOR}${BAR}${RESET} ${PCT}%${USAGE_SEGMENT}"
