#!/usr/bin/env bash
# WP-21 (D-022): install the free Mac replacements for the reconstruction tools in user space, without sudo,
# Homebrew or any account, and print their versions. Run again at any time: finished steps are skipped.
#
#   tools/mac/install-recon-tools.sh [PREFIX]      # PREFIX defaults to $HOME/golmok-tools (outside the repo)
#
# What it installs, each from its official source and pinned:
#   - micromamba 2.10.0-0 (BSD-3-Clause) from github.com/mamba-org/micromamba-releases, sha256 checked.
#   - conda-forge env "recon" with
#       colmap 4.2.1 "cpu_lgpl" build: no CUDA, no CGAL, no SuiteSparse/CHOLMOD (the GPL parts), BSD-3-Clause;
#       ffmpeg "lgpl" build (--disable-gpl, so no x264/x265); libheif "lgpl" build (no x265);
#       exiftool (Perl, GPL-1.0-or-later OR Artistic). All are separate programs, never linked into the game.
#   - Brush v0.3.0 brush-app-aarch64-apple-darwin (Apache-2.0) from github.com/ArthurBrussee/brush, sha256 checked.
# It writes $PREFIX/env.sh (source it to put the tools on PATH) and $PREFIX/envs/recon-explicit.txt (exact
# package list with URLs and hashes, to reproduce the env with `micromamba create -p … --file`).
# It does not remove com.apple.quarantine or change Gatekeeper settings; curl downloads are not quarantined.
# Needs only macOS system bash 3.2, curl, tar, shasum.
set -euo pipefail

PREFIX="${1:-${GOLMOK_TOOLS_PREFIX:-$HOME/golmok-tools}}"
PREFIX="${PREFIX%/}"

MICROMAMBA_VERSION="2.10.0-0"
MICROMAMBA_SHA256="c547639f5caf742236641c362746abb4a3505774753ecd08fe341643670c4c01"
MICROMAMBA_URL="https://github.com/mamba-org/micromamba-releases/releases/download/$MICROMAMBA_VERSION/micromamba-osx-arm64"

BRUSH_VERSION="v0.3.0"
BRUSH_ASSET="brush-app-aarch64-apple-darwin.tar.xz"
BRUSH_SHA256="65b2631398c839be3c1d4d7160fe2326389dec87830aac0710985e6690a1048c"
BRUSH_URL="https://github.com/ArthurBrussee/brush/releases/download/$BRUSH_VERSION/$BRUSH_ASSET"

# conda-forge match specs. The build-string globs pick the variants without GPL libraries.
RECON_SPECS="colmap=4.2.1=cpu_lgpl* ffmpeg=9.1.0=lgpl* libheif=*=lgpl* exiftool=13.64"

die() {
    echo "install-recon-tools: $*" >&2
    exit 1
}

# canonical PATH: absolute, symlinks resolved (pwd -P) through the deepest existing folder, without creating
# anything. A not-yet-existing tail may not contain . or .. parts, so the result is exact.
canonical() {
    local p="$1" rest="" base
    case "$p" in /*) ;; *) p="$PWD/$p" ;; esac
    while [ ! -d "$p" ]; do
        base="${p##*/}"
        case "$base" in . | ..) return 1 ;; esac
        [ -z "$base" ] || rest="/$base$rest"
        p="$(dirname -- "$p")"
    done
    p="$(cd -- "$p" >/dev/null && pwd -P)" || return 1
    p="${p%/}$rest"
    printf '%s\n' "${p:-/}"
}

# in_repo PATH: true when the canonical PATH is the repo or inside it. APFS ignores case, so compare lowercased.
in_repo() {
    local a b
    a="$(printf '%s/' "$1" | tr '[:upper:]' '[:lower:]')"
    b="$(printf '%s/' "$RepoRoot" | tr '[:upper:]' '[:lower:]')"
    case "$a" in "$b"*) return 0 ;; esac
    return 1
}

[ "$(uname -s)" = "Darwin" ] || die "macOS only (uname -s = $(uname -s))"
[ "$(uname -m)" = "arm64" ] || die "Apple Silicon only (uname -m = $(uname -m))"
[ "$(id -u)" != "0" ] || die "do not run as root; everything goes into user space"
RepoRoot="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." >/dev/null && pwd -P)"
PREFIX_ARG="$PREFIX"
PREFIX="$(canonical "$PREFIX")" || die "PREFIX: use a path without . or .. parts that do not exist yet: $PREFIX_ARG"
in_repo "$PREFIX" && die "PREFIX must be outside the repo ($RepoRoot): $PREFIX"

mkdir -p "$PREFIX/bin" "$PREFIX/downloads" "$PREFIX/envs"

sha256_of() {
    shasum -a 256 "$1" | awk '{print $1}'
}

# fetch URL DEST SHA256: download once, then always verify.
fetch() {
    local url="$1" dest="$2" want="$3"
    if [ ! -f "$dest" ] || [ "$(sha256_of "$dest")" != "$want" ]; then
        echo "download: $url"
        curl -fL --retry 3 -o "$dest.part" "$url"
        mv "$dest.part" "$dest"
    fi
    local got
    got="$(sha256_of "$dest")"
    [ "$got" = "$want" ] || die "sha256 mismatch for $dest: got $got, want $want"
}

# 1. micromamba
MM="$PREFIX/bin/micromamba"
fetch "$MICROMAMBA_URL" "$PREFIX/downloads/micromamba-osx-arm64-$MICROMAMBA_VERSION" "$MICROMAMBA_SHA256"
if [ ! -x "$MM" ] || [ "$(sha256_of "$MM")" != "$MICROMAMBA_SHA256" ]; then
    cp "$PREFIX/downloads/micromamba-osx-arm64-$MICROMAMBA_VERSION" "$MM"
    chmod 755 "$MM"
fi
export MAMBA_ROOT_PREFIX="$PREFIX/mamba"

# 2. conda-forge env (COLMAP, ffmpeg, exiftool)
ENV="$PREFIX/envs/recon"
if [ -x "$ENV/bin/colmap" ] && [ -x "$ENV/bin/ffmpeg" ] && [ -x "$ENV/bin/exiftool" ]; then
    echo "env exists: $ENV"
else
    # shellcheck disable=SC2086  # RECON_SPECS is a word list on purpose
    "$MM" create -y -p "$ENV" -c conda-forge --override-channels $RECON_SPECS
fi
"$MM" env export -p "$ENV" --explicit --md5 >"$PREFIX/envs/recon-explicit.txt"

# The lgpl variants must not have pulled a GPL-only library in. Dual-licensed ones (FreeImage, freetype, gmp,
# perl) and the GCC runtime exception are fine; exiftool is the tool itself.
# (A function, not a case inside $(...): bash 3.2 cannot parse case patterns inside command substitution.)
list_gpl_only() {
    local f lic name
    for f in "$ENV"/conda-meta/*.json; do
        lic="$(sed -n 's/^ *"license": "\(.*\)",*$/\1/p' "$f" | head -n 1)"
        name="$(basename "$f" .json)"
        case "$lic" in
            *" OR "* | *" or "* | *"WITH GCC-exception"* | *LGPL*) ;;
            *GPL*)
                case "$name" in
                    exiftool-*) ;;
                    *) echo "$name ($lic)" ;;
                esac
                ;;
        esac
    done
}
gpl_only="$(list_gpl_only)"
[ -z "$gpl_only" ] || die "GPL-only packages in $ENV: $gpl_only"

# 3. Brush
BRUSH_DIR="$PREFIX/brush-${BRUSH_VERSION#v}"
fetch "$BRUSH_URL" "$PREFIX/downloads/$BRUSH_VERSION-$BRUSH_ASSET" "$BRUSH_SHA256"
if [ ! -x "$BRUSH_DIR/brush_app" ]; then
    mkdir -p "$BRUSH_DIR"
    tar -xJf "$PREFIX/downloads/$BRUSH_VERSION-$BRUSH_ASSET" -C "$BRUSH_DIR" --strip-components 1
fi
ln -sf "$BRUSH_DIR/brush_app" "$PREFIX/bin/brush_app"
if xattr -p com.apple.quarantine "$BRUSH_DIR/brush_app" >/dev/null 2>&1; then
    echo "note: $BRUSH_DIR/brush_app has com.apple.quarantine; macOS will ask before the first run" >&2
fi

# 4. env.sh
cat >"$PREFIX/env.sh" <<EOF
# Generated by tools/mac/install-recon-tools.sh. Source it: . "$PREFIX/env.sh"
export GOLMOK_TOOLS_PREFIX="$PREFIX"
export MAMBA_ROOT_PREFIX="$PREFIX/mamba"
export PATH="$PREFIX/bin:$ENV/bin:\$PATH"
EOF

# 5. versions
echo "--- versions (prefix $PREFIX)"
echo "micromamba $("$MM" --version)"
"$ENV/bin/colmap" version 2>&1 | head -n 1
"$ENV/bin/ffmpeg" -hide_banner -version | head -n 1
echo "ffmpeg license: $("$ENV/bin/ffmpeg" -hide_banner -L | sed -n '1,2p' | tr '\n' ' ')"
echo "exiftool $(PATH="$ENV/bin:$PATH" "$ENV/bin/exiftool" -ver)"
"$BRUSH_DIR/brush_app" --version
echo "brush codesign: $(codesign -dv "$BRUSH_DIR/brush_app" 2>&1 | sed -n 's/^Signature=//p')"
echo "--- next: . \"$PREFIX/env.sh\" && tools/mac/recon-smoke.sh <images folder> [work folder]"
