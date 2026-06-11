#!/usr/bin/env sh
# Brick Protocol installer (rustup / uv style steps, clone-first).
#
# Usage (on a fresh machine) -- there is NO hosted installer URL; get the
# script from the repository first, with your own gh/git login:
#   gh repo clone insightwavesmith/BRICK ~/BRICK
#   sh ~/BRICK/support/onboarding/install.sh
# (or: git clone https://github.com/insightwavesmith/BRICK.git
#  then run support/onboarding/install.sh from the checkout)
# Cloned somewhere other than $HOME/BRICK? Set BRICK_HOME to that path
# first (e.g. BRICK_HOME=/path/to/your/clone sh install.sh) -- the default
# target is $HOME/BRICK.
#
# WHAT IT DOES (each step is plain and idempotent):
#   1. checks python3 (>= 3.11) is present
#   2. ensures `uv` is present (installs it via the official astral.sh script)
#   3. clones the private repo using YOUR OWN gh/git login (no token in here)
#   4. runs `uv sync` in the checkout
#   5. prints the next step: the onboard wizard
#
# SAFETY / LIMITS (read this honestly):
#   - This script is HTTPS-only and carries NO secret / token. It relies on the
#     teammate's OWN `gh auth login` (or git credential) as the access grant to
#     the private repo. There is nothing embedded here that grants access.
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

REPO_SLUG="insightwavesmith/BRICK"
# uv run resolves the synced .venv (where brick-protocol + PyYAML live); a
# bare python3 outside the venv raises ModuleNotFoundError.
ONBOARD_ENTRY="uv run python3 -m brick_protocol.support.operator.onboard codex"
CHECKER_ENTRY="PYTHONPATH=support/import_identity uv run python3 support/checkers/check_profile.py --all"

main() {
    # --help / -h: print the friendly guide and stop.
    case "${1:-}" in
        --help | -h)
            printf '%s\n' \
                "Brick Protocol 설치 스크립트" \
                "" \
                "하는 일: python3 확인 -> uv 준비 -> 내 gh/git 로그인으로 저장소 받기 -> uv sync -> 다음 안내" \
                "" \
                "설치 위치는 BRICK_HOME 환경변수로 바꿀 수 있어요 (기본값: \$HOME/BRICK)." \
                "토큰이나 비밀번호는 이 스크립트에 들어 있지 않아요. 내 gh/git 로그인을 그대로 씁니다." \
                "" \
                "그냥 실행하려면 옵션 없이 다시 실행하세요."
            return 0
            ;;
    esac

    target="${BRICK_HOME:-$HOME/BRICK}"

    # --- step 1: python3 present and >= 3.11 -------------------------------
    if ! command -v python3 >/dev/null 2>&1; then
        printf '%s\n' \
            "python3 가 없어요. 먼저 Python 3.11 이상을 설치한 뒤 다시 실행해 주세요." \
            "  - macOS: https://www.python.org/downloads/ 또는 'brew install python'" \
            "  - 설치 후 'python3 --version' 이 3.11 이상이면 됩니다." >&2
        return 1
    fi
    if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 11) else 1)' >/dev/null 2>&1; then
        printf '%s\n' \
            "python3 버전이 너무 낮아요. 3.11 이상이 필요합니다." \
            "  - 'python3 --version' 으로 확인하고, 3.11 이상으로 올린 뒤 다시 실행해 주세요." >&2
        return 1
    fi
    printf '%s\n' "1) python3 확인 완료 ✅"

    # --- step 2: ensure uv -------------------------------------------------
    if ! command -v uv >/dev/null 2>&1; then
        printf '%s\n' "2) uv 가 없어서 설치할게요 (astral.sh 공식 스크립트)..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # The uv installer puts uv under ~/.local/bin (or ~/.cargo/bin); add the
        # common locations to PATH for the rest of THIS run so the next steps
        # can find it without a new shell.
        PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
        export PATH
    fi
    if ! command -v uv >/dev/null 2>&1; then
        printf '%s\n' \
            "uv 설치를 끝냈지만 이번 셸에서 바로 찾지 못했어요." \
            "  - 터미널을 새로 열거나 'source ~/.local/bin/env' 후 다시 실행해 주세요." >&2
        return 1
    fi
    printf '%s\n' "2) uv 준비 완료 ✅"

    # --- step 3: clone via the user's OWN auth (idempotent) ----------------
    # No token lives here. If the checkout already exists, fast-forward pull
    # instead of cloning, so re-running is safe.
    if [ -d "$target/.git" ]; then
        printf '%s\n' "3) 이미 받아둔 저장소가 있어서 최신으로 갱신할게요 (fast-forward)..."
        git -C "$target" pull --ff-only
    else
        printf '%s\n' "3) 저장소를 받을게요 (내 gh/git 로그인 사용)..."
        if command -v gh >/dev/null 2>&1; then
            gh repo clone "$REPO_SLUG" "$target"
        else
            git clone "https://github.com/$REPO_SLUG.git" "$target"
        fi
    fi
    printf '%s\n' "3) 저장소 준비 완료 ✅ ($target)"

    # --- step 4: uv sync ---------------------------------------------------
    printf '%s\n' "4) 의존성을 설치할게요 (uv sync)..."
    ( cd "$target" && uv sync )
    printf '%s\n' "4) 의존성 설치 완료 ✅"

    # --- step 5: next-step pointer (plain Korean) --------------------------
    printf '%s\n' \
        "" \
        "받은 게 멀쩡한지 확인하려면 (verify your download):" \
        "  cd $target && $CHECKER_ENTRY" \
        "  (초록불 = exit 0 이면 정상이에요.)" \
        "" \
        "끝! 다음 단계는 온보딩 마법사예요:" \
        "  cd $target && $ONBOARD_ENTRY" \
        "" \
        "막히면 그냥 한국어로 에이전트한테 물어보면 돼요. 천천히 하셔도 괜찮아요 🙂"

    return 0
}

main "$@"
