#!/usr/bin/env sh
# Brick Protocol installer (rustup / uv style steps, clone-first).
#
# Usage (on a fresh machine) -- there is NO hosted installer URL; get the
# script from the repository first, with your own gh/git login:
#   gh repo clone {OWNER}/BRICK ~/BRICK
#   sh ~/BRICK/support/onboarding/install.sh
# Replace {OWNER} with your GitHub org/user, e.g.:
#   gh repo clone {OWNER}/BRICK ~/BRICK
# (or: git clone https://github.com/{OWNER}/BRICK.git, then run
#  support/onboarding/install.sh from the checkout)
# Cloned somewhere other than $HOME/BRICK? Set BRICK_HOME to that path
# first (e.g. BRICK_HOME=/path/to/your/clone sh install.sh) -- the default
# target is $HOME/BRICK.
# Running the script before the target checkout exists? Set BRICK_REPO first
# (e.g. BRICK_REPO={OWNER}/BRICK sh install.sh).
#
# WHAT IT DOES (each step is plain and idempotent):
#   0. PREFLIGHT FIRST: diagnose EVERY precondition (pipx, git, uv, a
#      Python >= 3.11, disk headroom, and -- for a fresh clone -- gh login)
#      BEFORE the project payload is fetched (the repo clone and `uv sync`).
#      Missing TOOLCHAIN prerequisites are auto-installed in place as bounded
#      remediation (uv via its official standalone script; a too-old / missing
#      Python is resolved through uv's managed Python, so no brew/system Python
#      is required). Those bootstrap fetches are the ONLY network calls preflight
#      may make, and they are toolchain acquisition -- NOT the project download;
#      the repo clone / uv sync never starts until the whole checklist is green.
#      Anything that cannot be auto-fixed prints one exact Korean "치라"
#      (run-this-now) line and the run stops before the repo clone / sync.
#   3. clones the private repo using YOUR OWN gh login (no token in here).
#   4. runs `uv sync` in the checkout.
#   5. installs the `brick` entrypoint, runs first-use init, and verifies the
#      checkout before printing the required success signal.
#   6. prints the next step commands.
#
# SAFETY / LIMITS (read this honestly):
#   - This script is HTTPS-only and carries NO secret / token. It relies on the
#     teammate's OWN `gh auth login` (or git credential) as the access grant to
#     the private repo. There is nothing embedded here that grants access.
#   - The uv bootstrap path is still a live HTTPS `curl | sh` trust decision:
#     it relies on astral.sh transport/content at install time and is not pinned
#     to a script digest in this repository. Use a preinstalled `uv` binary or a
#     locally reviewed installer when that trust boundary is unacceptable.
#   - The clone target is ${BRICK_HOME:-$HOME/BRICK}. No /Users path is
#     hardcoded, so it works for any teammate on any machine.
#   - ALL logic lives inside main(), invoked on the LAST line as `main "$@"`.
#     This is deliberate anti-truncation: if the download is cut off mid-stream,
#     main() is never defined and never called, so a partial file cannot run a
#     half-baked install.
#
# This is the SCRIPT. The structural lint (install_script_lint) checks its
# shape/safety; it does NOT prove the script actually installs on a real fresh
# machine -- that proof is manual / Phase-4 infra.

set -eu

REPO_SLUG="${BRICK_REPO:-}"
# uv run resolves the synced .venv (where brick-protocol + PyYAML live); a
# bare python3 outside the venv raises ModuleNotFoundError.
ONBOARD_ENTRY="uv run python3 -m brick_protocol.support.operator.onboard codex"

print_install_splash() {
    assets_dir="$1/support/onboarding/assets"
    splash_file="$assets_dir/splash.ascii"

    if [ -t 1 ] &&
        [ -z "${NO_COLOR:-}" ] &&
        [ "${FORCE_COLOR:-}" != "0" ] &&
        [ "${TERM:-}" != "dumb" ]; then
        splash_file="$assets_dir/splash.ansi"
    fi

    if [ -r "$splash_file" ]; then
        printf '\n'
        cat "$splash_file"
        printf '\n'
    fi
}

# --- PREFLIGHT BLOCK START -------------------------------------------------
# Removing this block MUST turn the onboarding literal checker RED
# (check_onboarding_success_literal.py pins "선검사 (preflight):",
# "preflight_all", and "uv python install"). Each helper prints a single ✓
# line on success or ONE exact Korean "지금 치세요" prescription on failure,
# and every helper runs BEFORE the repo clone / uv sync payload -- the project
# download never starts until the whole checklist is green. Preflight MAY make
# bounded toolchain-bootstrap fetches here (installing uv and a uv-managed
# Python); those are prerequisite acquisition, not the project payload. pipx is
# checked first so the ordering lint (pipx before python3 / clone / sync) holds.

preflight_pipx() {
    if command -v pipx >/dev/null 2>&1; then
        printf '%s\n' "  ✓ pipx"
        return 0
    fi
    printf '%s\n' \
        "  ✗ pipx 없음 — 지금 치세요: brew install pipx && pipx ensurepath (그 뒤 새 터미널에서 다시 실행)" >&2
    return 1
}

preflight_git() {
    if command -v git >/dev/null 2>&1; then
        printf '%s\n' "  ✓ git"
        return 0
    fi
    printf '%s\n' \
        "  ✗ git 없음 — 지금 치세요: brew install git (또는 OS 패키지 매니저로 git 설치)" >&2
    return 1
}

# Overridable seam: actually bootstrap uv via the official standalone
# installer. Unit tests override this to avoid network / system change.
_bootstrap_uv() {
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # The uv installer puts uv under ~/.local/bin (or ~/.cargo/bin); add the
    # common locations to PATH for the rest of THIS run so the next steps can
    # find it without a new shell.
    PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    export PATH
}

preflight_uv() {
    if ! command -v uv >/dev/null 2>&1; then
        printf '%s\n' \
            "  … uv 없음 — astral.sh 공식 스탠드얼론 스크립트로 설치합니다 (HTTPS curl|sh, repo 안에서 digest pin 미검증)"
        _bootstrap_uv
    fi
    if command -v uv >/dev/null 2>&1; then
        printf '%s\n' "  ✓ uv"
        return 0
    fi
    printf '%s\n' \
        "  ✗ uv 설치 후에도 이번 셸에서 못 찾음 — 지금 치세요: source \$HOME/.local/bin/env (그 뒤 다시 실행)" >&2
    return 1
}

_python_is_supported() {
    command -v python3 >/dev/null 2>&1 || return 1
    python3 -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 11) else 1)' >/dev/null 2>&1
}

# Overridable seam: acquire a uv-managed CPython (>= 3.11) and echo its bin
# directory on stdout. Returns non-zero when uv cannot install a managed
# Python (e.g. offline). Unit tests override this to reproduce that failure.
_uv_python_provision() {
    uv python install >/dev/null 2>&1 || return 1
    managed_bin="$(uv python find 2>/dev/null)" || return 1
    [ -n "$managed_bin" ] || return 1
    dirname "$managed_bin"
}

preflight_python() {
    if _python_is_supported; then
        printf '%s\n' "  ✓ python3 (>= 3.11)"
        return 0
    fi
    # python3 missing or < 3.11: acquire a uv-managed CPython so no brew /
    # system Python is required (uv installs Python standalone).
    printf '%s\n' \
        "  … python3 3.11+ 미확보 — uv 관리 파이썬으로 자동 확보합니다 (uv python install)"
    if managed_dir="$(_uv_python_provision)" && [ -n "$managed_dir" ]; then
        PATH="$managed_dir:$PATH"
        export PATH
        printf '%s\n' "  ✓ python3 (>= 3.11, uv 관리 파이썬 사용: $managed_dir)"
        return 0
    fi
    printf '%s\n' \
        "  ✗ 파이썬 자동 확보 실패 — 지금 치세요: uv python install 3.12 (네트워크 확인 후 다시 실행)" >&2
    return 1
}

preflight_disk() {
    # Require a modest free-space floor (~500MB) on the clone target's nearest
    # existing parent so a big clone + uv sync does not die mid-download with a
    # cryptic ENOSPC. Unmeasurable environments pass with a note (never a hard
    # stop on a measurement gap).
    parent="$1"
    while [ -n "$parent" ] && [ "$parent" != "/" ] && [ ! -d "$parent" ]; do
        parent="$(dirname "$parent")"
    done
    avail_kb="$(df -Pk "$parent" 2>/dev/null | awk 'NR==2 {print $4}')"
    case "$avail_kb" in
        '' | *[!0-9]*)
            printf '%s\n' "  ✓ 디스크 여유 (측정 불가 — 건너뜀)"
            return 0
            ;;
    esac
    if [ "$avail_kb" -ge 512000 ]; then
        printf '%s\n' "  ✓ 디스크 여유"
        return 0
    fi
    printf '%s\n' \
        "  ✗ 디스크 공간 부족 (약 500MB 필요) — 지금 치세요: 디스크를 정리하거나 BRICK_HOME=여유있는경로 로 다시 실행" >&2
    return 1
}

preflight_gh() {
    # gh + auth are only needed for a FRESH clone; an existing checkout uses git
    # credentials on pull, so skip the gh gate when the target already exists.
    target="$1"
    repo_slug="$2"
    if [ -d "$target/.git" ]; then
        printf '%s\n' "  ✓ gh 로그인 (이미 받은 저장소 — 생략)"
        return 0
    fi
    if [ -z "$repo_slug" ]; then
        printf '%s\n' \
            "  ✗ 받을 저장소 미지정 — 지금 치세요: BRICK_REPO={OWNER}/BRICK sh support/onboarding/install.sh" >&2
        return 1
    fi
    if ! command -v gh >/dev/null 2>&1; then
        printf '%s\n' \
            "  ✗ gh CLI 없음 — 지금 치세요: https://cli.github.com 에서 설치 후 gh auth login" >&2
        return 1
    fi
    if ! gh auth status >/dev/null 2>&1; then
        printf '%s\n' \
            "  ✗ GitHub 로그인 안 됨 — 지금 치세요: gh auth login" >&2
        return 1
    fi
    printf '%s\n' "  ✓ gh 로그인"
    return 0
}

preflight_all() {
    target="$1"
    repo_slug="$2"
    printf '%s\n' \
        "선검사 (preflight): 어떤 네트워크 다운로드/동기화보다 먼저 전제조건을 모두 확인합니다."
    preflight_pipx || return 1
    preflight_git || return 1
    preflight_uv || return 1
    preflight_python || return 1
    preflight_disk "$target" || return 1
    preflight_gh "$target" "$repo_slug" || return 1
    printf '%s\n' "0) 선검사 통과 — 모든 전제조건 충족 ✅"
    return 0
}
# --- PREFLIGHT BLOCK END ---------------------------------------------------

main() {
    # --help / -h: print the friendly guide and stop.
    case "${1:-}" in
        --help | -h)
            printf '%s\n' \
                "Brick Protocol 설치 스크립트" \
                "" \
                "하는 일: 선검사(pipx·git·uv·python3.11+·디스크·gh 로그인 일괄 진단, 부족분 자동 설치) -> 저장소 받기 -> uv sync -> 진입점/점검 -> 다음 안내" \
                "" \
                "설치 위치는 BRICK_HOME 환경변수로 바꿀 수 있어요 (기본값: \$HOME/BRICK)." \
                "새 org/user 포크라면 BRICK_REPO={OWNER}/BRICK 로 받을 저장소를 바꿀 수 있어요." \
                "토큰이나 비밀번호는 이 스크립트에 들어 있지 않아요. 내 gh/git 로그인을 그대로 씁니다." \
                "" \
                "그냥 실행하려면 옵션 없이 다시 실행하세요."
            return 0
            ;;
    esac

    target="${BRICK_HOME:-$HOME/BRICK}"

    # --- step 0: PREFLIGHT -- diagnose every precondition BEFORE any network
    # download or sync. On any failure the helper already printed the exact
    # one-line prescription, so stop here without touching the network.
    if ! preflight_all "$target" "$REPO_SLUG"; then
        return 1
    fi

    # --- step 3: clone via the user's OWN auth (idempotent) ----------------
    # No token lives here. Preflight already confirmed gh login / repo slug for
    # a fresh clone; if the checkout already exists, fast-forward pull instead
    # of cloning so re-running is safe.
    if [ -d "$target/.git" ]; then
        printf '%s\n' "3) 이미 받아둔 저장소가 있어서 최신으로 갱신할게요 (fast-forward)..."
        git -C "$target" pull --ff-only
    else
        printf '%s\n' "3) 저장소를 받을게요 (내 gh 로그인 사용: $REPO_SLUG)..."
        gh repo clone "$REPO_SLUG" "$target"
    fi
    printf '%s\n' "3) 저장소 준비 완료 ✅ ($target)"

    # --- step 4: uv sync ---------------------------------------------------
    printf '%s\n' "4) 의존성을 설치할게요 (uv sync)..."
    ( cd "$target" && uv sync )
    printf '%s\n' "4) 의존성 설치 완료 ✅"

    # --- entrypoint: install through pipx -------------------------------------
    printf '%s\n' "brick 진입점을 pipx로 설치할게요 (editable checkout)..."
    pipx install --force --editable "$target"
    pipx_bin_dir="$(pipx environment --value PIPX_BIN_DIR 2>/dev/null || true)"
    if [ -z "$pipx_bin_dir" ]; then
        pipx_bin_dir="$HOME/.local/bin"
    fi
    brick_entry="$pipx_bin_dir/brick"
    if [ ! -x "$brick_entry" ]; then
        brick_entry="$(command -v brick || true)"
    fi
    case "$brick_entry" in
        /*) ;;
        *)
            printf '%s\n' \
                "pipx 설치는 끝났지만 brick 실행 파일의 절대경로를 찾지 못했어요." \
                "  - 'pipx ensurepath' 후 터미널을 새로 열고 다시 실행해 주세요." >&2
            return 1
            ;;
    esac
    if [ ! -x "$brick_entry" ]; then
        printf '%s\n' \
            "brick 실행 파일을 찾았지만 실행할 수 없어요: $brick_entry" \
            "  - 'pipx reinstall brick-protocol' 후 다시 실행해 주세요." >&2
        return 1
    fi
    printf '%s\n' "brick 진입점 설치 완료 ✅ ($brick_entry)"

    # --- init: run first-use init by ABSOLUTE path ----------------------------
    # Do not rely on this shell's PATH refresh for first success. The executable
    # path resolved above is used directly.
    printf '%s\n' "" "brick init 을 바로 실행할게요 (절대경로 사용)..."
    "$brick_entry" init --non-interactive --repo "$target"
    printf '%s\n' "brick init 완료 ✅"

    # --- install check: verify the installed checkout through the existing path
    printf '%s\n' "" "설치 점검을 실행할게요 (brick verify)..."
    if ! ( cd "$target" && "$brick_entry" verify ); then
        printf '%s\n' \
            "5) 설치 점검 실패" \
            "  - 위의 verify 출력에서 첫 거절 문장을 확인한 뒤 다시 실행해 주세요." >&2
        return 1
    fi
    printf '%s\n' "5) 설치 점검 완료"
    print_install_splash "$target"

    # --- step 6: next-step pointer (plain Korean) ---------------------------
    printf '%s\n' \
        "" \
        "받은 게 멀쩡한지 확인하려면 (verify your download):" \
        "  $brick_entry verify" \
        "  (초록불 = exit 0 이면 정상이에요.)" \
        "" \
        "준비 상태 진단을 보려면:" \
        "  $brick_entry doctor" \
        "" \
        "끝! 다음 한 줄부터 쓰면 돼요:" \
        "  brick status" \
        "" \
        "옛 온보딩 seam 확인이 필요하면:" \
        "  cd $target && $ONBOARD_ENTRY" \
        "" \
        "막히면 그냥 한국어로 에이전트한테 물어보면 돼요. 천천히 하셔도 괜찮아요 🙂"

    return 0
}

main "$@"
