#!/usr/bin/env bash

GITLEAKS_VERSION="8.30.1"
GITLEAKS_SHA256="${GITLEAKS_SHA256:-551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb}"
GITLEAKS_DOWNLOAD_URL="${GITLEAKS_DOWNLOAD_URL:-https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz}"

usage() {
  cat >&2 <<'EOF'
Usage: gitleaks-scan.sh --mode pr --base <ref> --head <ref>
       gitleaks-scan.sh --mode tree
       gitleaks-scan.sh --mode history
EOF
}

install_gitleaks() (
  set -euo pipefail
  dest="$1"
  if [ "$(uname -s)-$(uname -m)" != "Linux-x86_64" ]; then
    echo "gitleaks-scan: the pinned download is linux x64, set GITLEAKS_BIN on this platform" >&2
    exit 1
  fi
  tarball="${dest}/gitleaks.tar.gz"
  curl -fsSL -o "$tarball" "$GITLEAKS_DOWNLOAD_URL"
  echo "${GITLEAKS_SHA256}  ${tarball}" | sha256sum -c - >&2
  tar -xzf "$tarball" -C "$dest" gitleaks
  echo "${dest}/gitleaks"
)

[ "${BASH_SOURCE[0]}" != "${0}" ] && return 0

set -euo pipefail

mode=""
base=""
head=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --mode | --base | --head)
      if [ "$#" -lt 2 ]; then
        echo "gitleaks-scan: $1 needs a value" >&2
        usage
        exit 2
      fi
      case "$1" in
        --mode) mode="$2" ;;
        --base) base="$2" ;;
        --head) head="$2" ;;
      esac
      shift 2
      ;;
    *)
      echo "gitleaks-scan: unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

case "$mode" in
  pr)
    if [ -z "$base" ] || [ -z "$head" ]; then
      echo "gitleaks-scan: --mode pr needs a non-empty --base and --head" >&2
      usage
      exit 2
    fi
    if [[ $base == -* || $head == -* ]]; then
      echo "gitleaks-scan: --base and --head must not start with a dash" >&2
      usage
      exit 2
    fi
    ;;
  tree | history) ;;
  *)
    echo "gitleaks-scan: unknown mode: ${mode:-<none>}" >&2
    usage
    exit 2
    ;;
esac

cd "$(git rev-parse --show-toplevel)"

if [ "$mode" = pr ]; then
  base_sha="$(git rev-parse --verify --quiet "${base}^{commit}")" || {
    echo "gitleaks-scan: base is not a commit in this repository: ${base}" >&2
    exit 2
  }
  head_sha="$(git rev-parse --verify --quiet "${head}^{commit}")" || {
    echo "gitleaks-scan: head is not a commit in this repository: ${head}" >&2
    exit 2
  }
fi

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

gitleaks="${GITLEAKS_BIN:-}"
if [ -z "$gitleaks" ]; then
  gitleaks="$(install_gitleaks "$workdir")"
fi

common_flags=(--redact --no-banner --no-color --verbose --exit-code 1 --gitleaks-ignore-path .)

case "$mode" in
  pr) "$gitleaks" git "${common_flags[@]}" --log-opts="${base_sha}..${head_sha}" . ;;
  tree) "$gitleaks" dir "${common_flags[@]}" . ;;
  history) "$gitleaks" git "${common_flags[@]}" . ;;
esac
