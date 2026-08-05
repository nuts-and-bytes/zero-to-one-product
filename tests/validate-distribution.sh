#!/usr/bin/env bash

set -uo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MARKETPLACE_ROOT="$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)"
PLUGIN_ROOT="${MARKETPLACE_ROOT}/plugins/zero-to-one-product"
SKILL_ROOT="${PLUGIN_ROOT}/skills/zero-to-one-product"

failures=0

pass() {
  printf '[PASS] %s\n' "$1"
}

fail() {
  printf '[FAIL] %s\n' "$1" >&2
  failures=$((failures + 1))
}

WORKTREE_SELF_TEST_TEMP_ROOT=""
WORKTREE_SELF_TEST_FIXTURE_ROOT=""

cleanup_worktree_self_test() {
  local temp_root="${WORKTREE_SELF_TEST_TEMP_ROOT:-}"
  local fixture_root="${WORKTREE_SELF_TEST_FIXTURE_ROOT:-}"

  if [[
    -n "${temp_root}"
    && -n "${fixture_root}"
    && "${fixture_root}" != "${temp_root}"
    && "${fixture_root%/*}" == "${temp_root}"
    && -d "${fixture_root}"
    && ! -L "${fixture_root}"
  ]]; then
    rm -rf -- "${fixture_root}"
    return $?
  fi
  return 0
}

abort_worktree_self_test_setup() {
  fail "$1"
  if ! cleanup_worktree_self_test; then
    fail "unable to clean up worktree self-test fixture directory"
  fi
  trap - EXIT
  return 1
}

run_worktree_self_test_git() {
  local variable_name
  local -a unset_git_environment=()

  while IFS='=' read -r variable_name _; do
    if [[ "${variable_name}" == GIT_* ]]; then
      unset_git_environment+=("-u" "${variable_name}")
    fi
  done < <(env)

  env \
    "${unset_git_environment[@]}" \
    GIT_CONFIG_NOSYSTEM=1 \
    GIT_CONFIG_GLOBAL=/dev/null \
    git "$@"
}

run_worktree_self_test() {
  local temp_root
  if ! temp_root="$(python3 - <<'PY'
import pathlib
import tempfile

print(pathlib.Path(tempfile.gettempdir()).resolve(strict=True))
PY
)"; then
    fail "unable to resolve the system temporary directory"
    return 1
  fi
  if [[ -z "${temp_root}" || "${temp_root}" != /* || ! -d "${temp_root}" || -L "${temp_root}" ]]; then
    fail "resolved temporary directory is not a safe absolute directory"
    return 1
  fi

  local fixture_root
  if ! fixture_root="$(mktemp -d "${temp_root}/validator-worktree.XXXXXX")"; then
    fail "unable to create worktree self-test fixture directory"
    return 1
  fi
  if [[
    -z "${fixture_root}"
    || "${fixture_root}" == "${temp_root}"
    || "${fixture_root%/*}" != "${temp_root}"
    || ! -d "${fixture_root}"
    || -L "${fixture_root}"
  ]]; then
    fail "worktree self-test fixture is not a safe child of the temporary directory"
    return 1
  fi

  WORKTREE_SELF_TEST_TEMP_ROOT="${temp_root}"
  WORKTREE_SELF_TEST_FIXTURE_ROOT="${fixture_root}"
  trap cleanup_worktree_self_test EXIT

  local ordinary_root="${fixture_root}/ordinary"
  local linked_root="${fixture_root}/linked"
  local empty_git_directory_root="${fixture_root}/empty-git-directory"
  local forged_git_directory_root="${fixture_root}/forged-git-directory"
  local forged_root="${fixture_root}/forged"
  local unrelated_root="${fixture_root}/unrelated"
  local wrong_reverse_root="${fixture_root}/wrong-reverse"
  local missing_reverse_root="${fixture_root}/missing-reverse"
  local malformed_root="${fixture_root}/malformed"
  local unexpected_root="${fixture_root}/unexpected"
  local invalid_webp_root="${fixture_root}/invalid-webp"
  local trailing_webp_root="${fixture_root}/trailing-webp"
  local hostile_home="${fixture_root}/hostile-home"
  local hostile_hooks="${fixture_root}/hostile-hooks"

  if ! mkdir -p "${hostile_home}" "${hostile_hooks}"; then
    abort_worktree_self_test_setup "unable to create hostile Git configuration fixture"
    return 1
  fi
  if ! printf '%s\n' \
    '[commit]' \
    '  gpgSign = true' \
    '[gpg]' \
    '  program = /definitely/missing/gpg' \
    '[core]' \
    "  hooksPath = ${hostile_hooks}" \
    '  worktree = /definitely/missing/worktree' > "${hostile_home}/.gitconfig"; then
    abort_worktree_self_test_setup "unable to write hostile global Git configuration fixture"
    return 1
  fi
  if ! printf '%s\n' \
    '#!/usr/bin/env bash' \
    "printf 'hostile global pre-commit hook ran\\n' >&2" \
    'exit 1' > "${hostile_hooks}/pre-commit"; then
    abort_worktree_self_test_setup "unable to write hostile global Git hook fixture"
    return 1
  fi
  if ! chmod +x "${hostile_hooks}/pre-commit"; then
    abort_worktree_self_test_setup "unable to make hostile global Git hook executable"
    return 1
  fi
  HOME="${hostile_home}"
  export HOME

  local visible_global_git_config
  if ! visible_global_git_config="$(run_worktree_self_test_git config --global --list)"; then
    abort_worktree_self_test_setup "unable to probe isolated global Git configuration"
    return 1
  fi
  if [[ -n "${visible_global_git_config}" ]]; then
    abort_worktree_self_test_setup "hostile global Git configuration leaked into fixture commands"
    return 1
  fi
  pass "fixture commands ignore hostile global Git configuration"

  local copied_root
  for copied_root in \
    "${ordinary_root}" \
    "${empty_git_directory_root}" \
    "${forged_git_directory_root}" \
    "${forged_root}" \
    "${malformed_root}" \
    "${unexpected_root}" \
    "${invalid_webp_root}" \
    "${trailing_webp_root}"; do
    if ! mkdir -p "${copied_root}"; then
      abort_worktree_self_test_setup "unable to create distribution fixture directory"
      return 1
    fi
    if ! tar --exclude='.git' -C "${MARKETPLACE_ROOT}" -cf - . | tar -C "${copied_root}" -xf -; then
      abort_worktree_self_test_setup "unable to copy distribution fixture"
      return 1
    fi
  done

  if ! run_worktree_self_test_git -C "${ordinary_root}" init -q; then
    abort_worktree_self_test_setup "unable to initialize ordinary checkout fixture"
    return 1
  fi
  if ! run_worktree_self_test_git -C "${ordinary_root}" add -A; then
    abort_worktree_self_test_setup "unable to stage ordinary checkout fixture"
    return 1
  fi
  if ! run_worktree_self_test_git \
    -C "${ordinary_root}" \
    -c user.name='Validator Test' \
    -c user.email='validator@example.invalid' \
    -c commit.gpgSign=false \
    -c core.hooksPath=/dev/null \
    commit -qm fixture; then
    abort_worktree_self_test_setup "unable to commit ordinary checkout fixture"
    return 1
  fi
  pass "hostile global Git configuration does not affect fixture commands"

  if bash "${ordinary_root}/tests/validate-distribution.sh" >/dev/null; then
    pass "ordinary checkout passes the distribution validator"
  else
    fail "ordinary checkout failed the distribution validator"
  fi

  if ! mkdir -p "${empty_git_directory_root}/.git"; then
    abort_worktree_self_test_setup "unable to create empty root Git-directory fixture"
    return 1
  fi
  if bash "${empty_git_directory_root}/tests/validate-distribution.sh" >/dev/null 2>&1; then
    fail "empty root .git directory was accepted"
  else
    pass "empty root .git directory is rejected"
  fi

  if ! mkdir -p "${forged_git_directory_root}/.git"; then
    abort_worktree_self_test_setup "unable to create forged root Git-directory fixture"
    return 1
  fi
  if ! printf 'forged hidden metadata\n' > "${forged_git_directory_root}/.git/hidden.txt"; then
    abort_worktree_self_test_setup "unable to create forged hidden Git metadata fixture"
    return 1
  fi
  if bash "${forged_git_directory_root}/tests/validate-distribution.sh" >/dev/null 2>&1; then
    fail "forged root .git directory with hidden content was accepted"
  else
    pass "forged root .git directory with hidden content is rejected"
  fi

  if ! run_worktree_self_test_git -C "${ordinary_root}" worktree add -q -b validator-linked "${linked_root}"; then
    abort_worktree_self_test_setup "unable to create linked worktree fixture"
    return 1
  fi
  if bash "${linked_root}/tests/validate-distribution.sh" >/dev/null; then
    pass "linked worktree passes the distribution validator"
  else
    fail "linked worktree failed the distribution validator"
  fi

  if ! mkdir -p "${unrelated_root}"; then
    abort_worktree_self_test_setup "unable to create unrelated Git fixture directory"
    return 1
  fi
  if ! run_worktree_self_test_git -C "${unrelated_root}" init -q; then
    abort_worktree_self_test_setup "unable to initialize unrelated Git fixture"
    return 1
  fi
  if ! run_worktree_self_test_git -C "${unrelated_root}" config core.worktree "${forged_root}"; then
    abort_worktree_self_test_setup "unable to configure forged Git worktree fixture"
    return 1
  fi
  printf 'gitdir: %s\n' "${unrelated_root}/.git" > "${forged_root}/.git"
  if bash "${forged_root}/tests/validate-distribution.sh" >/dev/null 2>&1; then
    fail "root .git pointer to an unrelated Git directory was accepted"
  else
    pass "root .git pointer to an unrelated Git directory is rejected"
  fi

  if ! run_worktree_self_test_git -C "${ordinary_root}" worktree add -q -b validator-wrong-reverse "${wrong_reverse_root}"; then
    abort_worktree_self_test_setup "unable to create wrong reverse-pointer fixture"
    return 1
  fi
  local wrong_reverse_git_dir
  if ! wrong_reverse_git_dir="$(run_worktree_self_test_git -C "${wrong_reverse_root}" rev-parse --path-format=absolute --git-dir)"; then
    abort_worktree_self_test_setup "unable to resolve wrong reverse-pointer fixture gitdir"
    return 1
  fi
  if [[ "${wrong_reverse_git_dir}" != "${ordinary_root}/.git/worktrees/"* || ! -d "${wrong_reverse_git_dir}" ]]; then
    abort_worktree_self_test_setup "wrong reverse-pointer fixture gitdir is outside the expected worktrees directory"
    return 1
  fi
  printf '%s\n' "${ordinary_root}/.git" > "${wrong_reverse_git_dir}/gitdir"
  if bash "${wrong_reverse_root}/tests/validate-distribution.sh" >/dev/null 2>&1; then
    fail "linked worktree with an incorrect gitdir reverse pointer was accepted"
  else
    pass "linked worktree with an incorrect gitdir reverse pointer is rejected"
  fi

  if ! run_worktree_self_test_git -C "${ordinary_root}" worktree add -q -b validator-missing-reverse "${missing_reverse_root}"; then
    abort_worktree_self_test_setup "unable to create missing reverse-pointer fixture"
    return 1
  fi
  local missing_reverse_git_dir
  if ! missing_reverse_git_dir="$(run_worktree_self_test_git -C "${missing_reverse_root}" rev-parse --path-format=absolute --git-dir)"; then
    abort_worktree_self_test_setup "unable to resolve missing reverse-pointer fixture gitdir"
    return 1
  fi
  if [[ "${missing_reverse_git_dir}" != "${ordinary_root}/.git/worktrees/"* || ! -d "${missing_reverse_git_dir}" ]]; then
    abort_worktree_self_test_setup "missing reverse-pointer fixture gitdir is outside the expected worktrees directory"
    return 1
  fi
  if ! rm -f -- "${missing_reverse_git_dir}/gitdir"; then
    abort_worktree_self_test_setup "unable to remove linked-worktree reverse pointer fixture"
    return 1
  fi
  if bash "${missing_reverse_root}/tests/validate-distribution.sh" >/dev/null 2>&1; then
    fail "linked worktree with a missing gitdir reverse pointer was accepted"
  else
    pass "linked worktree with a missing gitdir reverse pointer is rejected"
  fi

  if GIT_DIR="${ordinary_root}/.git" GIT_WORK_TREE="${ordinary_root}" \
    bash "${linked_root}/tests/validate-distribution.sh" >/dev/null 2>&1; then
    pass "inherited Git repository variables do not override linked-worktree detection"
  else
    fail "inherited Git repository variables overrode linked-worktree detection"
  fi

  printf 'gitdir: /definitely/missing/gitdir\n' > "${malformed_root}/.git"
  if bash "${malformed_root}/tests/validate-distribution.sh" >/dev/null 2>&1; then
    fail "malformed root .git pointer was accepted"
  else
    pass "malformed root .git pointer is rejected"
  fi

  printf 'forbidden fixture\n' > "${unexpected_root}/unexpected.txt"
  if bash "${unexpected_root}/tests/validate-distribution.sh" >/dev/null 2>&1; then
    fail "unexpected distribution file was accepted"
  else
    pass "unexpected distribution file remains rejected"
  fi

  printf 'not a WebP image\n' > "${invalid_webp_root}/docs/assets/hero-route.webp"
  local invalid_webp_hash
  if ! invalid_webp_hash="$(shasum -a 256 "${invalid_webp_root}/docs/assets/hero-route.webp" | awk '{print $1}')"; then
    abort_worktree_self_test_setup "unable to hash invalid WebP fixture"
    return 1
  fi
  if ! python3 - "${invalid_webp_root}/checksums.sha256" "${invalid_webp_hash}" <<'PY'
import pathlib
import sys

manifest = pathlib.Path(sys.argv[1])
digest = sys.argv[2]
target = "docs/assets/hero-route.webp"
lines = [
    line
    for line in manifest.read_text(encoding="utf-8").splitlines()
    if not line.endswith(f"  {target}")
]
lines.append(f"{digest}  {target}")
lines.sort(key=lambda line: line.split("  ", 1)[1])
manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
  then
    abort_worktree_self_test_setup "unable to update invalid WebP fixture checksum"
    return 1
  fi
  local invalid_webp_output
  if invalid_webp_output="$(bash "${invalid_webp_root}/tests/validate-distribution.sh" 2>&1)"; then
    fail "invalid WebP fixture was accepted"
  elif grep -Fq "invalid WebP signature: docs/assets/hero-route.webp" <<< "${invalid_webp_output}" \
    && grep -Fq "[PASS] checksums.sha256 exactly covers and matches all other regular files" \
      <<< "${invalid_webp_output}"; then
    pass "invalid WebP is rejected after its checksum is updated"
  else
    fail "invalid WebP fixture was rejected without the WebP signature gate"
  fi

  if ! python3 - "${trailing_webp_root}" <<'PY'
import hashlib
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
webp = root / "docs/assets/hero-route.webp"
data = bytearray(webp.read_bytes())
data.extend(b"JUNK\x00\x00\x00\x00")
data[4:8] = (len(data) - 8).to_bytes(4, "little")
webp.write_bytes(data)

entries = []
for entry in root.rglob("*"):
    if not entry.is_file() or entry == root / "checksums.sha256":
        continue
    relative = entry.relative_to(root).as_posix()
    entries.append((relative, hashlib.sha256(entry.read_bytes()).hexdigest()))
entries.sort()
(root / "checksums.sha256").write_text(
    "".join(f"{digest}  {relative}\n" for relative, digest in entries),
    encoding="utf-8",
)
PY
  then
    abort_worktree_self_test_setup "unable to create trailing WebP fixture"
    return 1
  fi
  local trailing_webp_output
  if trailing_webp_output="$(bash "${trailing_webp_root}/tests/validate-distribution.sh" 2>&1)"; then
    fail "trailing WebP fixture was accepted"
  elif grep -Fq "unexpected trailing WebP data: docs/assets/hero-route.webp" \
    <<< "${trailing_webp_output}" \
    && grep -Fq "[PASS] checksums.sha256 exactly covers and matches all other regular files" \
      <<< "${trailing_webp_output}"; then
    pass "trailing WebP data is rejected after its checksum is updated"
  else
    fail "trailing WebP fixture was rejected without the chunk-end gate"
  fi

  if (( failures > 0 )); then
    if ! cleanup_worktree_self_test; then
      fail "unable to clean up worktree self-test fixture directory"
    fi
    trap - EXIT
    printf 'FAIL: worktree compatibility self-test has %d failure(s).\n' "${failures}" >&2
    return 1
  fi
  if ! cleanup_worktree_self_test; then
    fail "unable to clean up worktree self-test fixture directory"
    trap - EXIT
    return 1
  fi
  trap - EXIT
  printf 'PASS: worktree compatibility self-test passed.\n'
}

if [[ "${1:-}" == "--self-test-worktree" ]]; then
  run_worktree_self_test
  exit $?
fi

detect_root_git_metadata() {
  local metadata_path="${MARKETPLACE_ROOT}/.git"

  if [[ ! -e "${metadata_path}" && ! -L "${metadata_path}" ]]; then
    printf 'none\n'
    return
  fi
  if [[ -L "${metadata_path}" ]]; then
    printf 'invalid\n'
    return
  fi
  if [[ -d "${metadata_path}" ]]; then
    if python3 - "${MARKETPLACE_ROOT}" <<'PY'
import os
import pathlib
import stat
import subprocess
import sys

root = pathlib.Path(sys.argv[1]).resolve(strict=True)
metadata = root / ".git"
git_env = {
    key: value for key, value in os.environ.items() if not key.startswith("GIT_")
}
git_env.update(
    {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }
)

try:
    metadata_stat = metadata.lstat()
    resolved_metadata = metadata.resolve(strict=True)
    actual_git_dir = pathlib.Path(
        subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-dir"],
            text=True,
            stderr=subprocess.DEVNULL,
            env=git_env,
        ).strip()
    ).resolve(strict=True)
    actual_common_dir = pathlib.Path(
        subprocess.check_output(
            [
                "git",
                "-C",
                str(root),
                "rev-parse",
                "--path-format=absolute",
                "--git-common-dir",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            env=git_env,
        ).strip()
    ).resolve(strict=True)
    actual_top = pathlib.Path(
        subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
            env=git_env,
        ).strip()
    ).resolve(strict=True)
    inside_work_tree = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
        text=True,
        stderr=subprocess.DEVNULL,
        env=git_env,
    ).strip()
    bare_repository = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "--is-bare-repository"],
        text=True,
        stderr=subprocess.DEVNULL,
        env=git_env,
    ).strip()
except (OSError, subprocess.CalledProcessError, RuntimeError):
    raise SystemExit(1)

if (
    stat.S_ISLNK(metadata_stat.st_mode)
    or not stat.S_ISDIR(metadata_stat.st_mode)
    or resolved_metadata != metadata
    or actual_git_dir != metadata
    or actual_common_dir != metadata
    or actual_top != root
    or inside_work_tree != "true"
    or bare_repository != "false"
):
    raise SystemExit(1)
PY
    then
      printf 'directory\n'
    else
      printf 'invalid\n'
    fi
    return
  fi
  if [[ ! -f "${metadata_path}" ]]; then
    printf 'invalid\n'
    return
  fi

  if python3 - "${MARKETPLACE_ROOT}" <<'PY'
import os
import pathlib
import re
import stat
import subprocess
import sys

root = pathlib.Path(sys.argv[1]).resolve(strict=True)
metadata = root / ".git"

try:
    text = metadata.read_text(encoding="utf-8")
except (OSError, UnicodeError):
    raise SystemExit(1)

match = re.fullmatch(r"gitdir: ([^\r\n]+)\r?\n?", text)
if not match:
    raise SystemExit(1)

declared = pathlib.Path(match.group(1))
if not declared.is_absolute():
    declared = root / declared

git_env = {
    key: value for key, value in os.environ.items() if not key.startswith("GIT_")
}
git_env.update(
    {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }
)

try:
    declared = declared.resolve(strict=True)
    actual_git_dir = pathlib.Path(
        subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-dir"],
            text=True,
            stderr=subprocess.DEVNULL,
            env=git_env,
        ).strip()
    ).resolve(strict=True)
    actual_common_dir = pathlib.Path(
        subprocess.check_output(
            [
                "git",
                "-C",
                str(root),
                "rev-parse",
                "--path-format=absolute",
                "--git-common-dir",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            env=git_env,
        ).strip()
    ).resolve(strict=True)
    actual_top = pathlib.Path(
        subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
            env=git_env,
        ).strip()
    ).resolve(strict=True)
except (OSError, subprocess.CalledProcessError, RuntimeError):
    raise SystemExit(1)

if (
    declared != actual_git_dir
    or actual_top != root
    or not actual_git_dir.is_dir()
    or not actual_common_dir.is_dir()
    or actual_git_dir.parent != actual_common_dir / "worktrees"
):
    raise SystemExit(1)

reverse_pointer = actual_git_dir / "gitdir"
try:
    reverse_pointer_stat = reverse_pointer.lstat()
except OSError:
    raise SystemExit(1)

if stat.S_ISLNK(reverse_pointer_stat.st_mode) or not stat.S_ISREG(
    reverse_pointer_stat.st_mode
):
    raise SystemExit(1)

try:
    reverse_pointer_text = reverse_pointer.read_text(encoding="utf-8")
except (OSError, UnicodeError):
    raise SystemExit(1)

reverse_match = re.fullmatch(r"([^\r\n]+)\r?\n?", reverse_pointer_text)
if not reverse_match:
    raise SystemExit(1)

reverse_declared = pathlib.Path(reverse_match.group(1))
if not reverse_declared.is_absolute():
    reverse_declared = actual_git_dir / reverse_declared

try:
    reverse_declared = reverse_declared.resolve(strict=True)
    metadata = metadata.resolve(strict=True)
except (OSError, RuntimeError):
    raise SystemExit(1)

if reverse_declared != metadata:
    raise SystemExit(1)
PY
  then
    printf 'pointer\n'
  else
    printf 'invalid\n'
  fi
}

root_git_metadata_kind="$(detect_root_git_metadata)"

required_files=(
  ".agents/plugins/marketplace.json"
  "plugins/zero-to-one-product/.codex-plugin/plugin.json"
  "plugins/zero-to-one-product/skills/zero-to-one-product/SKILL.md"
  "plugins/zero-to-one-product/skills/zero-to-one-product/agents/openai.yaml"
  "plugins/zero-to-one-product/skills/zero-to-one-product/references/dependencies.md"
  "plugins/zero-to-one-product/skills/zero-to-one-product/references/matt-bridges.md"
  "plugins/zero-to-one-product/skills/zero-to-one-product/references/bounded-execution.md"
  "plugins/zero-to-one-product/skills/zero-to-one-product/templates/state.md"
  "docs/index.html"
  "docs/styles.css"
  "docs/app.js"
  "docs/assets/hero-route.webp"
  "docs/assets/fixed-route.webp"
  "docs/assets/role-router.webp"
  "requirements-dev.txt"
  "tests/site_test_support.py"
  "tests/test_site_ticket_3.py"
  "tests/test_site_ticket_4.py"
  "README.md"
  "README.zh-CN.md"
  "LICENSE"
  "THIRD_PARTY_NOTICES.md"
  "checksums.sha256"
)

for relative_path in "${required_files[@]}"; do
  if [[ -f "${MARKETPLACE_ROOT}/${relative_path}" && ! -L "${MARKETPLACE_ROOT}/${relative_path}" ]]; then
    pass "required file exists: ${relative_path}"
  else
    fail "required regular non-symlink file missing: ${relative_path}"
  fi
done

if worktree_issues="$(python3 - "${MARKETPLACE_ROOT}" "${root_git_metadata_kind}" <<'PY'
import os
import pathlib
import re
import stat
import sys

root = pathlib.Path(sys.argv[1])
root_git_metadata_kind = sys.argv[2]
allowed_files = {
    ".agents/plugins/marketplace.json",
    "plugins/zero-to-one-product/.codex-plugin/plugin.json",
    "plugins/zero-to-one-product/skills/zero-to-one-product/SKILL.md",
    "plugins/zero-to-one-product/skills/zero-to-one-product/agents/openai.yaml",
    "plugins/zero-to-one-product/skills/zero-to-one-product/references/dependencies.md",
    "plugins/zero-to-one-product/skills/zero-to-one-product/references/matt-bridges.md",
    "plugins/zero-to-one-product/skills/zero-to-one-product/references/bounded-execution.md",
    "plugins/zero-to-one-product/skills/zero-to-one-product/templates/state.md",
    "docs/index.html",
    "docs/styles.css",
    "docs/app.js",
    "docs/assets/hero-route.webp",
    "docs/assets/fixed-route.webp",
    "docs/assets/role-router.webp",
    "requirements-dev.txt",
    "tests/site_test_support.py",
    "tests/test_site_ticket_3.py",
    "tests/test_site_ticket_4.py",
    "tests/validate-distribution.sh",
    "README.md",
    "README.zh-CN.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "checksums.sha256",
}
executable_file = "tests/validate-distribution.sh"
approved_webp_specs = {
    "docs/assets/hero-route.webp": (1440, 811, 450000),
    "docs/assets/fixed-route.webp": (1440, 811, 450000),
    "docs/assets/role-router.webp": (1440, 811, 450000),
}
private_key = re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----")
token_patterns = (
    ("GitHub fine-grained token", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    ("GitHub classic token", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("API key", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
    (
        "JWT",
        re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    ),
)
secret_assignment = re.compile(
    r"(?i)(?<![A-Za-z0-9_-])"
    r"(?:(?:[A-Za-z][A-Za-z0-9]*(?:[_-][A-Za-z0-9]+)*[_-])?"
    r"(?:secret(?:[_-]?access[_-]?key)?|access[_-]?token|client[_-]?secret|"
    r"token|password|api[_-]?key))"
    r"(?![A-Za-z0-9_-])"
    r"\s*[:=]\s*['\"]?[A-Za-z0-9+/=_-]{16,}"
)
issues = []


def special_kind(mode):
    if stat.S_ISSOCK(mode):
        return "socket"
    if stat.S_ISFIFO(mode):
        return "FIFO"
    if stat.S_ISCHR(mode):
        return "character device"
    if stat.S_ISBLK(mode):
        return "block device"
    return "non-regular entry"


for current, directory_names, file_names in os.walk(root, topdown=True, followlinks=False):
    current_path = pathlib.Path(current)
    for directory_name in list(directory_names):
        entry = current_path / directory_name
        entry_stat = entry.lstat()
        relative = entry.relative_to(root).as_posix()
        if directory_name == ".git" and current_path == root:
            if (
                root_git_metadata_kind == "directory"
                and stat.S_ISDIR(entry_stat.st_mode)
                and not stat.S_ISLNK(entry_stat.st_mode)
            ):
                directory_names.remove(directory_name)
                continue
            issues.append(f"invalid root .git metadata: {relative}")
        elif directory_name == ".git" and stat.S_ISDIR(entry_stat.st_mode):
            issues.append(f"nested .git directory forbidden: {relative}")

        if stat.S_ISLNK(entry_stat.st_mode):
            issues.append(f"symlink forbidden: {relative}")
            directory_names.remove(directory_name)
        elif not stat.S_ISDIR(entry_stat.st_mode):
            issues.append(f"{special_kind(entry_stat.st_mode)} forbidden: {relative}")
            directory_names.remove(directory_name)

    for file_name in file_names:
        entry = current_path / file_name
        relative = entry.relative_to(root).as_posix()
        entry_stat = entry.lstat()
        if relative == ".git":
            if (
                root_git_metadata_kind == "pointer"
                and stat.S_ISREG(entry_stat.st_mode)
                and not stat.S_ISLNK(entry_stat.st_mode)
            ):
                continue
            issues.append(f"invalid root .git metadata: {relative}")
            continue
        if stat.S_ISLNK(entry_stat.st_mode):
            issues.append(f"symlink forbidden: {relative}")
            continue
        if not stat.S_ISREG(entry_stat.st_mode):
            issues.append(f"{special_kind(entry_stat.st_mode)} forbidden: {relative}")
            continue

        if relative not in allowed_files:
            issues.append(f"unexpected file forbidden: {relative}")
        if entry.name == ".env" or entry.name.startswith(".env."):
            issues.append(f"environment file forbidden: {relative}")
        if entry_stat.st_mode & 0o111 and relative != executable_file:
            issues.append(f"executable file forbidden: {relative}")

        try:
            data = entry.read_bytes()
        except OSError as error:
            issues.append(f"unable to read file: {relative}: {error}")
            continue
        approved_webp_spec = approved_webp_specs.get(relative)
        if approved_webp_spec is not None:
            expected_width, expected_height, maximum_size = approved_webp_spec
            if len(data) > maximum_size:
                issues.append(f"WebP exceeds {maximum_size}-byte limit: {relative}")
                continue
            if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
                issues.append(f"invalid WebP signature: {relative}")
                continue
            declared_length = int.from_bytes(data[4:8], "little") + 8
            if declared_length != len(data):
                issues.append(
                    f"invalid WebP RIFF length: {relative}: "
                    f"declared {declared_length}, actual {len(data)}"
                )
                continue
            if len(data) < 20 or data[12:16] != b"VP8 ":
                issues.append(f"WebP first chunk must be static lossy VP8: {relative}")
                continue
            chunk_length = int.from_bytes(data[16:20], "little")
            chunk_data_end = 20 + chunk_length
            padded_end = chunk_data_end + (chunk_length & 1)
            if chunk_length < 10 or chunk_data_end > len(data):
                issues.append(f"invalid WebP VP8 chunk length: {relative}")
                continue
            if padded_end != len(data):
                issues.append(f"unexpected trailing WebP data: {relative}")
                continue
            if chunk_length & 1 and data[chunk_data_end] != 0:
                issues.append(f"invalid WebP VP8 padding byte: {relative}")
                continue
            if data[23:26] != b"\x9d\x01\x2a":
                issues.append(f"invalid WebP VP8 start code: {relative}")
                continue
            width = int.from_bytes(data[26:28], "little") & 0x3FFF
            height = int.from_bytes(data[28:30], "little") & 0x3FFF
            if (width, height) != (expected_width, expected_height):
                issues.append(
                    f"invalid WebP dimensions: {relative}: "
                    f"expected {expected_width}x{expected_height}, found {width}x{height}"
                )
                continue
            continue
        if b"\x00" in data:
            issues.append(f"NUL byte forbidden: {relative}")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            issues.append(f"non-UTF-8 file forbidden: {relative}: {error}")
            continue

        if private_key.search(text):
            issues.append(f"private key material forbidden: {relative}")
        for label, pattern in token_patterns:
            if pattern.search(text):
                issues.append(f"{label} forbidden: {relative}")
        if secret_assignment.search(text):
            issues.append(f"high-confidence secret assignment forbidden: {relative}")

if issues:
    print("\n".join(issues))
    raise SystemExit(1)
PY
)"; then
  pass "worktree inventory, file types, encoding, executability, and secret scan are valid"
else
  printf '%s\n' "${worktree_issues}" >&2
  fail "worktree safety validation failed"
fi

checksums_file="${MARKETPLACE_ROOT}/checksums.sha256"
if [[ ! -f "${checksums_file}" || -L "${checksums_file}" ]]; then
  fail "checksums.sha256 missing; unable to verify distribution hashes"
elif checksum_issues="$(python3 - "${MARKETPLACE_ROOT}" "${root_git_metadata_kind}" <<'PY'
import hashlib
import os
import pathlib
import re
import stat
import sys

root = pathlib.Path(sys.argv[1])
root_git_metadata_kind = sys.argv[2]
manifest_path = root / "checksums.sha256"
line_pattern = re.compile(r"^([0-9A-Fa-f]{64})  (.+)$")
issues = []
listed = {}

try:
    manifest_text = manifest_path.read_text(encoding="utf-8")
except (OSError, UnicodeError) as error:
    print(f"unable to read checksums.sha256 as UTF-8: {error}")
    raise SystemExit(1)

for line_number, line in enumerate(manifest_text.splitlines(), start=1):
    match = line_pattern.fullmatch(line)
    if not match:
        issues.append(f"checksums.sha256:{line_number}: invalid checksum entry")
        continue
    expected_hash, raw_path = match.groups()
    relative = pathlib.PurePosixPath(raw_path)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or relative.as_posix() != raw_path
        or raw_path in {"", ".", "checksums.sha256"}
    ):
        issues.append(f"checksums.sha256:{line_number}: unsafe or non-canonical path: {raw_path}")
        continue
    if raw_path in listed:
        issues.append(f"checksums.sha256:{line_number}: duplicate path: {raw_path}")
        continue
    listed[raw_path] = expected_hash.lower()

actual = {}
for current, directory_names, file_names in os.walk(root, topdown=True, followlinks=False):
    current_path = pathlib.Path(current)
    if ".git" in directory_names and current_path == root:
        root_git = current_path / ".git"
        root_git_stat = root_git.lstat()
        if (
            root_git_metadata_kind == "directory"
            and stat.S_ISDIR(root_git_stat.st_mode)
            and not stat.S_ISLNK(root_git_stat.st_mode)
        ):
            directory_names.remove(".git")
    for file_name in file_names:
        entry = current_path / file_name
        entry_stat = entry.lstat()
        if not stat.S_ISREG(entry_stat.st_mode) or stat.S_ISLNK(entry_stat.st_mode):
            continue
        relative = entry.relative_to(root).as_posix()
        if relative == ".git" and root_git_metadata_kind == "pointer":
            continue
        if relative == "checksums.sha256":
            continue
        actual[relative] = hashlib.sha256(entry.read_bytes()).hexdigest()

missing = sorted(set(actual) - set(listed))
extra = sorted(set(listed) - set(actual))
if missing:
    issues.append("checksums.sha256 missing paths: " + ", ".join(missing))
if extra:
    issues.append("checksums.sha256 lists unknown paths: " + ", ".join(extra))
for relative in sorted(set(actual) & set(listed)):
    if actual[relative] != listed[relative]:
        issues.append(f"checksums.sha256 hash mismatch: {relative}")

if issues:
    print("\n".join(issues))
    raise SystemExit(1)
PY
)"; then
  pass "checksums.sha256 exactly covers and matches all other regular files"
else
  printf '%s\n' "${checksum_issues}" >&2
  fail "checksums.sha256 validation failed"
fi

parse_json() {
  local relative_path="$1"
  local absolute_path="${MARKETPLACE_ROOT}/${relative_path}"

  if [[ ! -f "${absolute_path}" || -L "${absolute_path}" ]]; then
    return
  fi

  if python3 - "${absolute_path}" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
try:
    with path.open(encoding="utf-8") as handle:
        json.load(handle)
except (OSError, UnicodeError, json.JSONDecodeError) as error:
    print(f"invalid JSON: {path}: {error}", file=sys.stderr)
    raise SystemExit(1)
PY
  then
    pass "valid JSON: ${relative_path}"
  else
    fail "could not parse JSON with python3: ${relative_path}"
  fi
}

parse_json ".agents/plugins/marketplace.json"
parse_json "plugins/zero-to-one-product/.codex-plugin/plugin.json"

find_trusted_validator() {
  local creator_name="$1"
  local script_name="$2"

  python3 - "${creator_name}" "${script_name}" <<'PY'
import os
import pathlib
import pwd
import stat
import sys

creator_name, script_name = sys.argv[1:3]
try:
    passwd_home = pathlib.Path(pwd.getpwuid(os.getuid()).pw_dir)
except (KeyError, OSError) as error:
    print(f"unable to resolve current account home from uid: {error}", file=sys.stderr)
    raise SystemExit(2)
if not passwd_home.is_absolute():
    print(f"current account home is not absolute: {passwd_home}", file=sys.stderr)
    raise SystemExit(2)
if passwd_home.is_symlink():
    print(f"passwd home must not be a symlink: {passwd_home}", file=sys.stderr)
    raise SystemExit(2)
try:
    canonical_home = passwd_home.resolve(strict=True)
except OSError as error:
    print(f"unable to strictly resolve passwd home: {passwd_home}: {error}", file=sys.stderr)
    raise SystemExit(2)
if not canonical_home.is_dir():
    print(f"strictly resolved passwd home is not a directory: {canonical_home}", file=sys.stderr)
    raise SystemExit(2)

primary_relative = pathlib.Path(".codex") / "skills" / ".system" / creator_name
fallback_relative = pathlib.Path(".agents") / "skills" / creator_name
primary_roots = [(passwd_home / primary_relative, primary_relative)]
fallback_roots = [(passwd_home / fallback_relative, fallback_relative)]


def symlink_in_home_chain(target):
    try:
        relative = target.relative_to(passwd_home)
    except ValueError:
        return target
    cursor = passwd_home
    if cursor.is_symlink():
        return cursor
    for part in relative.parts:
        cursor = cursor / part
        if os.path.lexists(cursor) and cursor.is_symlink():
            return cursor
    return None


def find_group(root_specs):
    matches = {}
    errors = []
    for root, expected_relative in root_specs:
        if not os.path.lexists(root):
            continue
        symlink_ancestor = symlink_in_home_chain(root)
        if symlink_ancestor is not None:
            errors.append(f"symlink forbidden in passwd-home validator path: {symlink_ancestor}")
            continue
        if not root.is_dir():
            errors.append(f"trusted creator root is not a directory: {root}")
            continue
        try:
            canonical_root = root.resolve(strict=True)
            root_relative = canonical_root.relative_to(canonical_home)
        except (OSError, ValueError) as error:
            errors.append(f"trusted creator root escapes passwd home or cannot resolve: {root}: {error}")
            continue
        if root_relative != expected_relative or canonical_root.name != creator_name:
            errors.append(f"trusted creator directory identity mismatch: {root}")
            continue

        candidate = root / "scripts" / script_name
        if not os.path.lexists(candidate):
            continue
        symlink_ancestor = symlink_in_home_chain(candidate)
        if symlink_ancestor is not None:
            errors.append(f"symlink forbidden in validator path: {symlink_ancestor}")
            continue
        try:
            candidate_stat = candidate.stat()
        except OSError as error:
            errors.append(f"validator cannot be inspected: {candidate}: {error}")
            continue
        if not stat.S_ISREG(candidate_stat.st_mode):
            errors.append(f"validator is not a regular file: {candidate}")
            continue

        canonical_candidate = candidate.resolve(strict=True)
        try:
            relative = canonical_candidate.relative_to(canonical_root)
        except ValueError:
            errors.append(f"validator escapes trusted creator root: {candidate}")
            continue
        if relative.as_posix() != f"scripts/{script_name}":
            errors.append(f"validator path identity mismatch: {candidate}")
            continue
        if canonical_candidate.name != script_name or canonical_candidate.parent.name != "scripts":
            errors.append(f"validator filename or directory identity mismatch: {candidate}")
            continue
        matches[str(canonical_candidate)] = canonical_candidate

    if errors:
        print("; ".join(errors), file=sys.stderr)
        raise SystemExit(2)
    if len(matches) > 1:
        print(
            "multiple trusted validator matches: " + ", ".join(sorted(matches)),
            file=sys.stderr,
        )
        raise SystemExit(2)
    if matches:
        print(next(iter(matches.values())))
        return True
    return False


if find_group(primary_roots):
    raise SystemExit(0)
if find_group(fallback_roots):
    raise SystemExit(0)
print(f"no trusted validator found for {creator_name}/{script_name}", file=sys.stderr)
raise SystemExit(1)
PY
}

if skill_validator="$(find_trusted_validator "skill-creator" "quick_validate.py")"; then
  if python3 "${skill_validator}" "${SKILL_ROOT}"; then
    pass "skill validator accepted skills/zero-to-one-product"
  else
    fail "skill validator rejected skills/zero-to-one-product"
  fi
else
  fail "trusted skill validator discovery failed"
fi

if plugin_validator="$(find_trusted_validator "plugin-creator" "validate_plugin.py")"; then
  if python3 "${plugin_validator}" "${PLUGIN_ROOT}"; then
    pass "plugin validator accepted plugins/zero-to-one-product"
  else
    fail "plugin validator rejected plugins/zero-to-one-product"
  fi
else
  fail "trusted plugin validator discovery failed"
fi

if portability_hits="$(python3 - "${MARKETPLACE_ROOT}" <<'PY'
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
slash = "/"
users_component = "Us" + "ers"
home_component = "ho" + "me"
legacy_eric_home = slash + users_component + slash + "eric" + "lu"
unix_name = r"[^/\s'\"`]+"
windows_name = r"[^\\/\s'\"`]+"
dependencies = (
    "grill-me",
    "grill-with-docs",
    "wayfinder",
    "research",
    "prototype",
    "to-spec",
    "to-tickets",
    "diagnosing-bugs",
    "code-review",
    "handoff",
    "using-git-worktrees",
    "writing-plans",
    "test-driven-development",
    "systematic-debugging",
    "requesting-code-review",
    "verification-before-completion",
    "finishing-a-development-branch",
)
dependency = r"(?:" + "|".join(re.escape(name) for name in dependencies) + r")(?=$|[^A-Za-z0-9._-])"
skill_tree = r"\.(?:co" + "dex|ag" + r"ents)[\\/]skills[\\/]"
unix_skill_tree = r"\.(?:co" + "dex|ag" + "ents)/skills/"
flags = re.IGNORECASE

patterns = (
    ("legacy Eric user path", re.compile(re.escape(legacy_eric_home), flags)),
    (
        "macOS or Linux fixed dependency path",
        re.compile(
            re.escape(slash)
            + r"(?:" + users_component + "|" + home_component + r")/"
            + unix_name
            + slash
            + unix_skill_tree
            + dependency,
            flags,
        ),
    ),
    (
        "Windows user fixed dependency path",
        re.compile(
            r"[A-Za-z]:[\\/]"
            + users_component
            + r"[\\/]"
            + windows_name
            + r"[\\/]"
            + skill_tree
            + dependency,
            flags,
        ),
    ),
    (
        "fixed tilde or bare dependency path",
        re.compile(
            r"(?<![A-Za-z0-9_./\\:$}-])(?:~[\\/])?" + skill_tree + dependency,
            flags,
        ),
    ),
    (
        "fixed absolute Unix skill path",
        re.compile(
            r"(?<![A-Za-z0-9_$}:./\\-])/(?:[^/\s'\"`]+/)*"
            + unix_skill_tree
            + dependency,
            flags,
        ),
    ),
    (
        "fixed absolute Windows skill path",
        re.compile(
            r"[A-Za-z]:[\\/](?:[^\\/\s'\"`]+[\\/])*"
            + skill_tree
            + dependency,
            flags,
        ),
    ),
)

for path in sorted(root.rglob("*")):
    relative = path.relative_to(root)
    if (relative.parts and relative.parts[0] == ".git") or path.is_symlink() or not path.is_file():
        continue
    try:
        data = path.read_bytes()
    except OSError as error:
        print(f"unable to scan {relative}: {error}", file=sys.stderr)
        raise SystemExit(1)
    if b"\x00" in data:
        continue
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        continue
    for line_number, line in enumerate(text.splitlines(), start=1):
        reasons = [label for label, pattern in patterns if pattern.search(line)]
        if reasons:
            print(f"{relative}:{line_number}:{','.join(reasons)}:{line.strip()}")
PY
)"; then
  if [[ -n "${portability_hits}" ]]; then
    printf '%s\n' "${portability_hits}" >&2
    fail "distribution contains machine-specific or fixed dependency paths"
  else
    pass "distribution contains no machine-specific or fixed dependency paths"
  fi
else
  fail "could not scan distribution text for machine-specific paths"
fi

dependencies_file="${SKILL_ROOT}/references/dependencies.md"
required_dependencies=(
  "grill-me"
  "grill-with-docs"
  "wayfinder"
  "research"
  "prototype"
  "to-spec"
  "to-tickets"
  "diagnosing-bugs"
  "code-review"
  "handoff"
  "using-git-worktrees"
  "writing-plans"
  "test-driven-development"
  "systematic-debugging"
  "requesting-code-review"
  "verification-before-completion"
  "finishing-a-development-branch"
)

if [[ -f "${dependencies_file}" ]]; then
  for dependency in "${required_dependencies[@]}"; do
    if grep -Eq "(^|[^[:alnum:]_-])${dependency}([^[:alnum:]_-]|$)" "${dependencies_file}"; then
      pass "dependencies.md names exact skill: ${dependency}"
    else
      fail "dependencies.md is missing exact skill name: ${dependency}"
    fi
  done
else
  fail "cannot check exact skill names because dependencies.md is missing"
fi

if ((failures > 0)); then
  printf 'FAIL: zero-to-one-product marketplace distribution has %d validation error(s).\n' "${failures}" >&2
  exit 1
fi

printf 'PASS: zero-to-one-product marketplace distribution is valid.\n'
