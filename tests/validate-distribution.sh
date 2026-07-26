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

required_files=(
  ".agents/plugins/marketplace.json"
  "plugins/zero-to-one-product/.codex-plugin/plugin.json"
  "plugins/zero-to-one-product/skills/zero-to-one-product/SKILL.md"
  "plugins/zero-to-one-product/skills/zero-to-one-product/agents/openai.yaml"
  "plugins/zero-to-one-product/skills/zero-to-one-product/references/dependencies.md"
  "plugins/zero-to-one-product/skills/zero-to-one-product/references/matt-bridges.md"
  "plugins/zero-to-one-product/skills/zero-to-one-product/references/bounded-execution.md"
  "plugins/zero-to-one-product/skills/zero-to-one-product/templates/state.md"
  "README.md"
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

if worktree_issues="$(python3 - "${MARKETPLACE_ROOT}" <<'PY'
import os
import pathlib
import re
import stat
import sys

root = pathlib.Path(sys.argv[1])
allowed_files = {
    ".agents/plugins/marketplace.json",
    "plugins/zero-to-one-product/.codex-plugin/plugin.json",
    "plugins/zero-to-one-product/skills/zero-to-one-product/SKILL.md",
    "plugins/zero-to-one-product/skills/zero-to-one-product/agents/openai.yaml",
    "plugins/zero-to-one-product/skills/zero-to-one-product/references/dependencies.md",
    "plugins/zero-to-one-product/skills/zero-to-one-product/references/matt-bridges.md",
    "plugins/zero-to-one-product/skills/zero-to-one-product/references/bounded-execution.md",
    "plugins/zero-to-one-product/skills/zero-to-one-product/templates/state.md",
    "tests/validate-distribution.sh",
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "checksums.sha256",
}
executable_file = "tests/validate-distribution.sh"
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
            if stat.S_ISDIR(entry_stat.st_mode) and not stat.S_ISLNK(entry_stat.st_mode):
                directory_names.remove(directory_name)
                continue
            issues.append(f"root .git metadata must be a non-symlink directory: {relative}")
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
elif checksum_issues="$(python3 - "${MARKETPLACE_ROOT}" <<'PY'
import hashlib
import os
import pathlib
import re
import stat
import sys

root = pathlib.Path(sys.argv[1])
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
        if stat.S_ISDIR(root_git_stat.st_mode) and not stat.S_ISLNK(root_git_stat.st_mode):
            directory_names.remove(".git")
    for file_name in file_names:
        entry = current_path / file_name
        entry_stat = entry.lstat()
        if not stat.S_ISREG(entry_stat.st_mode) or stat.S_ISLNK(entry_stat.st_mode):
            continue
        relative = entry.relative_to(root).as_posix()
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
