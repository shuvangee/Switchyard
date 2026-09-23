"""Sandboxed code-execution grader for coding/debugging benchmark tasks.

NOT wired into evaluate()/EvaluationType yet — deliberately standalone
until the grading approach itself has been reviewed against real
results. See scripts/grade_code_responses.py for the report-only entry
point that uses this module.

Isolation model — what's real (kernel-enforced) vs. best-effort:

- Network: REAL. Every run happens inside a fresh network namespace
  (`unshare --net`) with no interfaces configured. Verified directly (not
  assumed): a socket connect attempt inside the namespace raises
  "Network is unreachable" (OSError, errno 101), the kernel refusing the
  connection before any packet could leave the host — not a Python-level
  policy that determined code could bypass.
- Filesystem: REAL. Every run happens inside a fresh mount namespace with
  the entire root filesystem remounted read-only, and only that run's own
  temp directory bind-mounted read-write on top. Verified directly: a
  write outside the temp dir raises "Read-only file system" (OSError,
  errno 30, from the kernel's VFS layer), a write inside it succeeds.
- CPU/memory/process count: best-effort, via `resource.setrlimit` set
  inside the sandboxed process itself (RLIMIT_CPU, RLIMIT_AS,
  RLIMIT_NPROC=0, RLIMIT_FSIZE), backed up by a wall-clock subprocess
  timeout in the parent as the hard stop.
- The candidate code is only ever exec()'d inside this isolated child
  process. The process that imports this module never calls eval() or
  exec() on it directly.

Requires the `unshare` binary (util-linux) and the ability to create new
mount/net namespaces (this process runs as root in its own container in
the environments this was built and tested in, which is sufficient;
`is_sandbox_available()` checks this at runtime rather than assuming it).
"""

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TIMEOUT_SECONDS = 5
_MEMORY_LIMIT_BYTES = 256 * 1024 * 1024  # 256 MB
_MAX_OUTPUT_BYTES = 10_000_000  # 10 MB written-file cap inside the sandbox

_CODE_FENCE_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)

# {code} is embedded via compile(..., "<candidate>", "exec") on a Python
# string, not string-interpolated into source — repr() gives us a safe,
# unambiguous escape of arbitrary candidate code (including one containing
# triple-quotes or braces) with no injection risk into the runner's own
# syntax.
_RUNNER_TEMPLATE = """\
import json, resource

resource.setrlimit(resource.RLIMIT_CPU, ({timeout}, {timeout}))
resource.setrlimit(resource.RLIMIT_AS, ({mem_limit}, {mem_limit}))
resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
resource.setrlimit(resource.RLIMIT_FSIZE, ({max_output}, {max_output}))

namespace = {{}}
try:
    exec(compile({code!r}, "<candidate>", "exec"), namespace)
    fn = namespace[{function_name!r}]
    args = json.loads({args_json!r})
    result = fn(*args)
    print(json.dumps({{"ok": True, "result": result}}))
except Exception as exc:
    print(json.dumps({{"ok": False, "error": f"{{type(exc).__name__}}: {{exc}}"}}))
"""

_SANDBOX_SHELL = (
    "mount --make-rprivate / && "
    "mount -o bind {tmpdir} {tmpdir} && "
    "mount -o remount,bind,rw {tmpdir} && "
    "mount -o remount,bind,ro / && "
    "python3 {runner_path}"
)


@dataclass(frozen=True)
class TestCaseResult:
    passed: bool
    actual: Any = None
    error: str | None = None
    timed_out: bool = False


@dataclass(frozen=True)
class TaskGradeResult:
    code_extracted: bool
    all_passed: bool
    test_case_results: list[TestCaseResult] = field(default_factory=list)


def is_sandbox_available() -> bool:
    """Checks the isolation primitives actually work in this environment,
    rather than assuming `unshare` existing on PATH is sufficient (it also
    needs permission to create new mount/net namespaces).
    """
    try:
        proc = subprocess.run(
            ["unshare", "--mount", "--net", "--", "true"],
            capture_output=True,
            timeout=5,
        )
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def extract_python_code(response_text: str, function_name: str) -> str | None:
    """Pulls the fenced code block that actually defines `function_name`
    out of a model response. Prefers a block containing the expected
    function's def over just taking the first fenced block, since a
    response may include a second block for example usage or output.
    Returns None if the response has no fenced code block at all.
    """
    blocks = _CODE_FENCE_RE.findall(response_text)
    for block in blocks:
        if f"def {function_name}(" in block:
            return block
    return blocks[0] if blocks else None


def _values_equal(actual: Any, expected: Any, note: str | None) -> bool:
    if note and ("order-insensitive" in note.lower() or "frozenset" in note.lower()):
        try:
            return {frozenset(group) for group in actual} == {frozenset(group) for group in expected}
        except TypeError:
            return False
    return actual == expected


def run_test_case(
    code: str,
    function_name: str,
    test_input: list,
    expected: Any,
    note: str | None = None,
    timeout: int = TIMEOUT_SECONDS,
) -> TestCaseResult:
    """Runs `code` (expected to define `function_name`) against one test
    case, fully isolated per the module docstring's isolation model. A
    fresh sandbox is used per test case, not reused across a task's test
    cases, so one hanging/misbehaving case can't affect the timing or
    process state of the others.
    """
    with tempfile.TemporaryDirectory(prefix="switchyard-grade-") as tmpdir:
        tmp_path = Path(tmpdir)
        runner_path = tmp_path / "runner.py"
        runner_path.write_text(
            _RUNNER_TEMPLATE.format(
                timeout=timeout,
                mem_limit=_MEMORY_LIMIT_BYTES,
                max_output=_MAX_OUTPUT_BYTES,
                code=code,
                function_name=function_name,
                args_json=json.dumps(test_input),
            )
        )
        shell_cmd = _SANDBOX_SHELL.format(tmpdir=tmp_path, runner_path=runner_path)

        try:
            proc = subprocess.run(
                ["unshare", "--mount", "--net", "--", "sh", "-c", shell_cmd],
                capture_output=True,
                text=True,
                timeout=timeout + 2,  # headroom beyond the in-sandbox CPU limit for process/mount setup
                env={"PATH": "/usr/bin:/bin"},  # minimal env - no secrets, no inherited API keys
            )
        except subprocess.TimeoutExpired:
            return TestCaseResult(passed=False, error="sandbox timed out", timed_out=True)

        if proc.returncode != 0:
            return TestCaseResult(
                passed=False,
                error=f"sandbox exited {proc.returncode}: {proc.stderr.strip()[:500]}",
            )

        try:
            last_line = proc.stdout.strip().splitlines()[-1]
            outcome = json.loads(last_line)
        except (json.JSONDecodeError, IndexError):
            return TestCaseResult(
                passed=False,
                error=f"no parseable output (stdout={proc.stdout[:500]!r}, stderr={proc.stderr[:500]!r})",
            )

        if not outcome.get("ok"):
            return TestCaseResult(passed=False, error=outcome.get("error", "unknown error"))

        actual = outcome["result"]
        return TestCaseResult(passed=_values_equal(actual, expected, note), actual=actual)


def grade_response(
    response_text: str,
    function_name: str,
    test_cases: list[dict],
    timeout: int = TIMEOUT_SECONDS,
) -> TaskGradeResult:
    """Extracts code from `response_text` and runs it against every test
    case. A task passes only if code was found AND every test case
    passed - matching every other evaluator in this project, "no ground
    truth to check" is a distinct outcome from "checked and failed", not
    silently folded into the same bucket.
    """
    code = extract_python_code(response_text, function_name)
    if code is None:
        return TaskGradeResult(code_extracted=False, all_passed=False)

    results = [
        run_test_case(
            code,
            function_name,
            tc["input"],
            tc["expected"],
            note=tc.get("note"),
            timeout=timeout,
        )
        for tc in test_cases
    ]
    return TaskGradeResult(
        code_extracted=True,
        all_passed=all(r.passed for r in results),
        test_case_results=results,
    )
