#!/usr/bin/env bash

set -uo pipefail

here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
target="${here}/gitleaks-scan.sh"
fixture="${here}/fixtures/gitleaks-planted-secret.txt"

failures=0

report() {
  if [ -z "$2" ]; then
    printf 'PASS %s\n' "$1"
  else
    printf 'FAIL %s: %s\n' "$1" "$2"
    failures=$((failures + 1))
  fi
}

contains() {
  case "$1" in
    *"$2"*) return 0 ;;
    *) return 1 ;;
  esac
}

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# shellcheck source=/dev/null
source "$target"

bin_dir="${tmp}/bin"
mkdir "$bin_dir"
if [ -n "${GITLEAKS_BIN:-}" ]; then
  gitleaks_bin="$GITLEAKS_BIN"
else
  gitleaks_bin="$(install_gitleaks "$bin_dir")" || gitleaks_bin=""
fi
if [ -z "$gitleaks_bin" ] || [ ! -x "$gitleaks_bin" ]; then
  printf 'FAIL the verified gitleaks binary could not be obtained\n'
  exit 1
fi

planted_line="$(cat "$fixture")"
unmarked_line="${planted_line% gitleaks:allow}"
unmarked_line="${unmarked_line% #}"
planted_value="$(grep -oE 'ghp_[A-Za-z0-9]{36}' "$fixture")"
other_value="ghp_$(printf '%s' "${planted_value#ghp_}" | rev)"

git_in() {
  local repo="$1"
  shift
  git -C "$repo" -c user.name='Scan Test' -c user.email='scan-test@example.invalid' \
    -c commit.gpgsign=false "$@"
}

new_repo() {
  local repo="${tmp}/$1"
  mkdir "$repo"
  git -C "$repo" init -q -b main
  git_in "$repo" commit -q --allow-empty -m 'root'
  printf '%s' "$repo"
}

commit_file() {
  printf '%s\n' "$3" >"$1/$2"
  git_in "$1" add "$2"
  git_in "$1" commit -q -m "add $2"
}

scan() {
  local repo="$1"
  shift
  (cd "$repo" && GITLEAKS_BIN="$gitleaks_bin" bash "$target" "$@" 2>&1)
}


repo="$(new_repo planted)"
base="$(git_in "$repo" rev-parse HEAD)"
commit_file "$repo" config.txt "$unmarked_line"
head="$(git_in "$repo" rev-parse HEAD)"
out="$(scan "$repo" --mode pr --base "$base" --head "$head")"
rc=$?
detail=''
[ "$rc" -ne 0 ] || detail='pr mode exited zero on a committed secret'
report 'pr mode fails on a committed secret' "$detail"

detail=''
! contains "$out" "$planted_value" || detail='the raw secret value appears in the output'
contains "$out" 'config.txt' || detail="${detail:+${detail}; }the offending file is not named"
report 'pr mode names the file and redacts the value' "$detail"


repo="$(new_repo allowed)"
base="$(git_in "$repo" rev-parse HEAD)"
commit_file "$repo" config.txt "$planted_line"
head="$(git_in "$repo" rev-parse HEAD)"
out="$(scan "$repo" --mode pr --base "$base" --head "$head")"
rc=$?
detail=''
[ "$rc" -eq 0 ] || detail="exit status was ${rc}: ${out}"
report 'pr mode passes a line carrying the allow marker' "$detail"


repo="$(new_repo ranged)"
commit_file "$repo" old.txt "github_token = ${other_value}"
base="$(git_in "$repo" rev-parse HEAD)"
commit_file "$repo" readme.txt 'nothing to see'
head="$(git_in "$repo" rev-parse HEAD)"
out="$(scan "$repo" --mode pr --base "$base" --head "$head")"
rc=$?
detail=''
[ "$rc" -eq 0 ] || detail="a secret before the base was reported, exit status ${rc}: ${out}"
report 'pr mode ignores a secret committed before the base' "$detail"

commit_file "$repo" new.txt "$unmarked_line"
head="$(git_in "$repo" rev-parse HEAD)"
out="$(scan "$repo" --mode pr --base "$base" --head "$head")"
rc=$?
detail=''
[ "$rc" -ne 0 ] || detail='a secret inside the range was not reported'
contains "$out" 'new.txt' || detail="${detail:+${detail}; }the in-range file is not named"
! contains "$out" 'old.txt' || detail="${detail:+${detail}; }the out-of-range file is named"
report 'pr mode reports the secret inside the range only' "$detail"


repo="$(new_repo tree)"
commit_file "$repo" planted.txt "$unmarked_line"
out="$(scan "$repo" --mode tree)"
rc=$?
detail=''
[ "$rc" -ne 0 ] || detail='tree mode exited zero on a secret in the tree'
! contains "$out" "$planted_value" || detail="${detail:+${detail}; }the raw secret value appears in the output"
report 'tree mode fails on a secret and redacts it' "$detail"

out="$(scan "$repo" --mode history)"
rc=$?
detail=''
[ "$rc" -ne 0 ] || detail='history mode exited zero on a secret in history'
report 'history mode fails on a secret in history' "$detail"

repo="$(new_repo tree-allowed)"
commit_file "$repo" planted.txt "$planted_line"
out="$(scan "$repo" --mode tree)"
rc=$?
detail=''
[ "$rc" -eq 0 ] || detail="exit status was ${rc}: ${out}"
report 'tree mode passes a line carrying the allow marker' "$detail"


repo="$(new_repo ignored)"
commit_file "$repo" planted.txt "$unmarked_line"
printf 'planted.txt:github-pat:1\n' >"${repo}/.gitleaksignore"
out="$(scan "$repo" --mode tree)"
rc=$?
detail=''
[ "$rc" -eq 0 ] || detail="exit status was ${rc}: ${out}"
report 'tree mode honours a root .gitleaksignore' "$detail"


fake_dir="${tmp}/fake"
mkdir "$fake_dir"
marker="${tmp}/binary-ran"
printf '#!/bin/sh\ntouch "%s"\nexit 0\n' "$marker" >"${fake_dir}/gitleaks"
chmod +x "${fake_dir}/gitleaks"
tar -czf "${tmp}/fake.tar.gz" -C "$fake_dir" gitleaks
fake_sha="$(sha256sum "${tmp}/fake.tar.gz" | cut -d ' ' -f 1)"
repo="$(new_repo checksum)"

out="$(cd "$repo" && env -u GITLEAKS_BIN GITLEAKS_DOWNLOAD_URL="file://${tmp}/fake.tar.gz" \
  GITLEAKS_SHA256="$(printf '%064d' 0)" bash "$target" --mode tree 2>&1)"
rc=$?
detail=''
[ "$rc" -ne 0 ] || detail='a checksum mismatch exited zero'
[ ! -e "$marker" ] || detail="${detail:+${detail}; }the downloaded binary ran despite the mismatch"
report 'a wrong checksum aborts before the binary runs' "$detail"

if [ "$(uname -s)-$(uname -m)" = "Linux-x86_64" ]; then
  out="$(cd "$repo" && env -u GITLEAKS_BIN GITLEAKS_DOWNLOAD_URL="file://${tmp}/fake.tar.gz" \
    GITLEAKS_SHA256="$fake_sha" bash "$target" --mode tree 2>&1)"
  rc=$?
  detail=''
  [ "$rc" -eq 0 ] || detail="exit status was ${rc}: ${out}"
  [ -e "$marker" ] || detail="${detail:+${detail}; }a verified download did not run"
  report 'a matching checksum lets the downloaded binary run' "$detail"
fi


repo="$(new_repo arguments)"
head="$(git_in "$repo" rev-parse HEAD)"

out="$(scan "$repo" --mode pr --base '' --head "$head")"
rc=$?
detail=''
[ "$rc" -ne 0 ] || detail='an empty base exited zero'
contains "$out" 'Usage:' || detail="${detail:+${detail}; }no usage text"
report 'an empty base ref is rejected with usage' "$detail"

out="$(scan "$repo" --mode pr --base "$head" --head '')"
rc=$?
detail=''
[ "$rc" -ne 0 ] || detail='an empty head exited zero'
contains "$out" 'Usage:' || detail="${detail:+${detail}; }no usage text"
report 'an empty head ref is rejected with usage' "$detail"

out="$(scan "$repo" --mode nonsense)"
rc=$?
detail=''
[ "$rc" -ne 0 ] || detail='an unknown mode exited zero'
contains "$out" 'Usage:' || detail="${detail:+${detail}; }no usage text"
report 'an unknown mode is rejected with usage' "$detail"

out="$(scan "$repo")"
rc=$?
detail=''
[ "$rc" -ne 0 ] || detail='a missing mode exited zero'
contains "$out" 'Usage:' || detail="${detail:+${detail}; }no usage text"
report 'a missing mode is rejected with usage' "$detail"

out="$(scan "$repo" --mode pr --base '-p' --head "$head")"
rc=$?
detail=''
[ "$rc" -ne 0 ] || detail='a base starting with a dash exited zero'
report 'a base that looks like an option is rejected' "$detail"

out="$(scan "$repo" --mode pr --base does-not-exist --head "$head")"
rc=$?
detail=''
[ "$rc" -ne 0 ] || detail='an unresolvable base exited zero'
report 'an unresolvable base ref is rejected' "$detail"

if [ "$failures" -ne 0 ]; then
  printf '\n%d failure(s)\n' "$failures"
  exit 1
fi
printf '\nall gitleaks-scan cases passed\n'
