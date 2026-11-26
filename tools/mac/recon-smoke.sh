#!/usr/bin/env bash
# WP-21 (D-022): end-to-end smoke run of the Mac reconstruction replacements on a folder of photos.
#
#   . ~/golmok-tools/env.sh                       # from tools/mac/install-recon-tools.sh
#   tools/mac/recon-smoke.sh <images folder> [work folder]
#
# Steps (CPU for COLMAP, Metal through wgpu for Brush), each timed with /usr/bin/time -l into <work>/logs:
#   1 colmap feature_extractor (SIFT, use_gpu 0, one shared camera)   -> <work>/database.db
#   2 colmap exhaustive_matcher, or sequential_matcher with SMOKE_MATCHER=sequential
#   3 colmap mapper (incremental)                                     -> <work>/sparse/0
#   4 colmap global_mapper (GLOMAP) if SMOKE_GLOBAL=1 (default)       -> <work>/sparse_global/0  (comparison only)
#   5 colmap image_undistorter -> PINHOLE images + model              -> <work>/undistorted
#     (Brush reads only focal length and principal point and ignores lens distortion, so it trains on these.)
#   6 brush_app <work>/undistorted, SMOKE_STEPS steps                 -> <work>/brush/splat_<steps>.ply
#   7 golmok-splat inspect / clean / tiles on that PLY                -> <work>/post
# The splat stays in the COLMAP world frame of step 3 (Brush does not recenter or rescale), so a mesh built from
# the same sparse model shares its coordinates. Results: <work>/summary.txt.
#
# Settings (environment): GOLMOK_TOOLS_PREFIX (default ~/golmok-tools), SMOKE_MATCHER (exhaustive|sequential),
# SMOKE_GLOBAL (1|0), SMOKE_STEPS (3000), SMOKE_MAX_RES (1600, Brush image long side), SMOKE_SIFT_MAX (3200,
# SIFT image long side), SMOKE_CAMERA_MODEL (OPENCV), GOLMOK_SPLAT (golmok-splat command; default: the repo's
# tools/.venv one, else PATH). Datasets, models and PLYs stay in the work folder, which must be outside the repo
# (.ply is git-ignored anyway). Needs only macOS system bash 3.2.
set -euo pipefail

die() {
    echo "recon-smoke: $*" >&2
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

[ $# -ge 1 ] && [ $# -le 2 ] || die "usage: recon-smoke.sh <images folder> [work folder]"
IMAGES="$(cd -- "$1" >/dev/null 2>&1 && pwd -P)" || die "no such folder: $1"
RepoRoot="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." >/dev/null && pwd -P)"
WORK="${2:-$HOME/golmok_data/recon-smoke/sfm-splat/run-$(date +%Y%m%d-%H%M%S)}"
WORK="$(canonical "$WORK")" || die "work folder: use a path without . or .. parts that do not exist yet: ${2:-}"
in_repo "$WORK" && die "work folder must be outside the repo ($RepoRoot): $WORK"
in_repo "$IMAGES" && die "images must be outside the repo ($RepoRoot): $IMAGES"

PREFIX="${GOLMOK_TOOLS_PREFIX:-$HOME/golmok-tools}"
PREFIX="${PREFIX%/}"
MATCHER="${SMOKE_MATCHER:-exhaustive}"
GLOBAL="${SMOKE_GLOBAL:-1}"
STEPS="${SMOKE_STEPS:-3000}"
MAX_RES="${SMOKE_MAX_RES:-1600}"
SIFT_MAX="${SMOKE_SIFT_MAX:-3200}"
CAMERA_MODEL="${SMOKE_CAMERA_MODEL:-OPENCV}"
case "$MATCHER" in exhaustive | sequential) ;; *) die "SMOKE_MATCHER must be exhaustive or sequential" ;; esac

COLMAP="$PREFIX/envs/recon/bin/colmap"
BRUSH="$PREFIX/bin/brush_app"
[ -x "$COLMAP" ] || die "missing $COLMAP; run tools/mac/install-recon-tools.sh first"
[ -x "$BRUSH" ] || die "missing $BRUSH; run tools/mac/install-recon-tools.sh first"
if [ -n "${GOLMOK_SPLAT:-}" ]; then
    SPLAT_CLI="$GOLMOK_SPLAT"
elif [ -x "$RepoRoot/tools/.venv/bin/golmok-splat" ]; then
    SPLAT_CLI="$RepoRoot/tools/.venv/bin/golmok-splat"
else
    SPLAT_CLI="$(command -v golmok-splat || true)"
fi

N_IMAGES="$(find "$IMAGES" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.tif' -o -iname '*.tiff' \) | wc -l | tr -d ' ')"
[ "$N_IMAGES" -gt 0 ] || die "no .jpg/.png/.tif images in $IMAGES"

mkdir -p "$WORK/logs" "$WORK/sparse" "$WORK/brush" "$WORK/post"
WORK="$(cd -- "$WORK" >/dev/null && pwd -P)"
# Nothing may land in the caller's folder (e.g. the repo): every tool runs from inside the work folder.
cd "$WORK"
SUMMARY="$WORK/summary.txt"
: >"$SUMMARY"
say() {
    echo "$*" | tee -a "$SUMMARY"
}

# timed NAME CMD...: run with /usr/bin/time -l, log to logs/NAME.log, add wall time and peak RSS to the summary.
timed() {
    local name="$1"
    shift
    local log="$WORK/logs/$name.log" start end rss foot
    start="$(date +%s)"
    if ! /usr/bin/time -l "$@" >"$log" 2>&1; then
        tail -n 20 "$log" >&2
        die "step $name failed (log: $log)"
    fi
    end="$(date +%s)"
    rss="$(awk '/maximum resident set size/ {printf "%.0f", $1 / 1048576}' "$log")"
    foot="$(awk '/peak memory footprint/ {printf "%.0f", $1 / 1048576}' "$log")"
    say "step $name: $((end - start)) s wall, peak RSS ${rss:-?} MiB, peak footprint ${foot:-?} MiB"
}

gpu_sample() {
    ioreg -r -d 1 -c IOAccelerator 2>/dev/null | grep -o '"Device Utilization %"=[0-9]*' | head -n 1 | sed 's/.*=//'
}

say "recon-smoke $(date '+%Y-%m-%d %H:%M:%S %z')"
say "images: $IMAGES ($N_IMAGES files)"
say "work: $WORK"
say "machine: $(sysctl -n machdep.cpu.brand_string), $(sysctl -n hw.ncpu) cores, $(($(sysctl -n hw.memsize) / 1073741824)) GB, load $(sysctl -n vm.loadavg)"
say "$("$COLMAP" version 2>&1 | head -n 1)"
say "$("$BRUSH" --version)"

DB="$WORK/database.db"
rm -f "$DB"
timed 1-feature_extractor "$COLMAP" feature_extractor --database_path "$DB" --image_path "$IMAGES" \
    --ImageReader.camera_model "$CAMERA_MODEL" --ImageReader.single_camera 1 \
    --FeatureExtraction.use_gpu 0 --FeatureExtraction.max_image_size "$SIFT_MAX"
timed "2-${MATCHER}_matcher" "$COLMAP" "${MATCHER}_matcher" --database_path "$DB" --FeatureMatching.use_gpu 0

rm -rf "$WORK/sparse/0" "$WORK/sparse_global"
timed 3-mapper "$COLMAP" mapper --database_path "$DB" --image_path "$IMAGES" --output_path "$WORK/sparse"
[ -f "$WORK/sparse/0/cameras.bin" ] || die "mapper produced no model"
"$COLMAP" model_analyzer --path "$WORK/sparse/0" >"$WORK/logs/3-model_analyzer.log" 2>&1
say "mapper model (sparse/0):"
grep -E "Cameras|Images|Registered images|Points|Observations|Mean track length|Mean observations per image|Mean reprojection error" \
    "$WORK/logs/3-model_analyzer.log" | sed 's/^.*\] /  /' | tee -a "$SUMMARY"
n_models="$(find "$WORK/sparse" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
say "  models from mapper: $n_models (only sparse/0 is used)"

if [ "$GLOBAL" = "1" ]; then
    mkdir -p "$WORK/sparse_global"
    timed 4-global_mapper "$COLMAP" global_mapper --database_path "$DB" --image_path "$IMAGES" \
        --output_path "$WORK/sparse_global" --GlobalMapper.gp_use_gpu 0
    if [ -f "$WORK/sparse_global/0/cameras.bin" ]; then
        "$COLMAP" model_analyzer --path "$WORK/sparse_global/0" >"$WORK/logs/4-model_analyzer.log" 2>&1
        say "global_mapper model (sparse_global/0, not used below):"
        grep -E "Registered images|Points|Mean reprojection error" "$WORK/logs/4-model_analyzer.log" |
            sed 's/^.*\] /  /' | tee -a "$SUMMARY"
    else
        say "global_mapper: no model"
    fi
fi

rm -rf "$WORK/undistorted"
timed 5-image_undistorter "$COLMAP" image_undistorter --image_path "$IMAGES" --input_path "$WORK/sparse/0" \
    --output_path "$WORK/undistorted" --output_type COLMAP
"$COLMAP" model_converter --input_path "$WORK/undistorted/sparse" --output_path "$WORK/undistorted/sparse" \
    --output_type TXT >/dev/null 2>&1
say "undistorted camera: $(grep -v '^#' "$WORK/undistorted/sparse/cameras.txt" | head -n 1)"

# Brush. It runs inside $WORK/brush because it writes its kernel autotune cache to ./target in the current folder.
# GPU utilisation (IOAccelerator, no sudo) is system-wide: compare the samples during training with the idle ones.
PLY="$WORK/brush/splat_$STEPS.ply"
GPU_LOG="$WORK/logs/6-gpu.log"
gpu_idle="$(gpu_sample)"
: >"$GPU_LOG"
(
    while :; do
        gpu_sample >>"$GPU_LOG"
        sleep 2
    done
) &
SAMPLER=$!
stop_sampler() {
    kill "$SAMPLER" 2>/dev/null || true
    wait "$SAMPLER" 2>/dev/null || true
}
trap stop_sampler EXIT
(
    cd "$WORK/brush"
    export RUST_LOG="${RUST_LOG:-info}"
    timed 6-brush "$BRUSH" "$WORK/undistorted" --total-steps "$STEPS" \
        --export-every "$STEPS" --export-path "$WORK/brush" --export-name "splat_{iter}.ply" \
        --max-resolution "$MAX_RES" --eval-split-every 8 --eval-every "$STEPS"
)
stop_sampler
[ -f "$PLY" ] || PLY="$(find "$WORK/brush" -name '*.ply' | sort | tail -n 1)"
[ -n "$PLY" ] && [ -f "$PLY" ] || die "brush wrote no PLY (log: $WORK/logs/6-brush.log)"
say "brush ply: $PLY ($(du -h "$PLY" | awk '{print $1}'))"
gpu_max="$(sort -n "$GPU_LOG" | tail -n 1)"
gpu_n="$(wc -l <"$GPU_LOG" | tr -d ' ')"
say "gpu utilisation (system-wide): idle ${gpu_idle:-?} %, training max ${gpu_max:-?} % over $gpu_n samples"
grep -E "Using adapter|Loaded dataset|Eval iter" "$WORK/logs/6-brush.log" | sed -e 's/^.*\] /  /' -e 's/, vendor.*backend/ … backend/' |
    tee -a "$SUMMARY" || true

# Repo post-processing (docs/runbooks/recon-postprocess.md), as far as it applies without a zone manifest.
if [ -z "$SPLAT_CLI" ]; then
    say "golmok-splat: not found (cd tools && pip install -e \".[splat]\"); skipped"
    exit 0
fi
"$SPLAT_CLI" inspect --json "$PLY" >"$WORK/post/inspect.json"
say "golmok-splat inspect: $WORK/post/inspect.json"
timed 7-splat_clean "$SPLAT_CLI" clean "$PLY" --out "$WORK/post/clean.ply" --min-opacity 0.02
timed 7-splat_tiles "$SPLAT_CLI" tiles "$WORK/post/clean.ply" --out "$WORK/post/tiles"
say "tiles: $(find "$WORK/post/tiles" -type f | wc -l | tr -d ' ') files, $(du -sh "$WORK/post/tiles" | awk '{print $1}')"
say "done"
