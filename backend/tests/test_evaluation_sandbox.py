"""Sandbox grader tests. These exercise the REAL isolation (no mocking of
subprocess/unshare) - the isolation itself is what's under test, per the
module's own docstring about what's kernel-enforced vs. best-effort.
Skipped cleanly wherever unshare/namespace creation isn't available
(is_sandbox_available checks this directly) rather than failing
confusingly in a more restricted environment.
"""

import pytest

from app.evaluation.sandbox import (
    TIMEOUT_SECONDS,
    extract_python_code,
    grade_response,
    is_sandbox_available,
    run_test_case,
)

pytestmark = pytest.mark.skipif(
    not is_sandbox_available(), reason="unshare namespace isolation not available in this environment"
)


def test_correct_code_passes_all_test_cases():
    code = "def add(a, b):\n    return a + b\n"
    result = grade_response(
        f"Here's the function:\n```python\n{code}```",
        "add",
        [{"input": [2, 3], "expected": 5}, {"input": [-1, 1], "expected": 0}],
    )
    assert result.code_extracted is True
    assert result.all_passed is True
    assert all(r.passed for r in result.test_case_results)


def test_wrong_code_fails():
    code = "def add(a, b):\n    return a - b\n"  # deliberately wrong
    result = grade_response(
        f"```python\n{code}```",
        "add",
        [{"input": [2, 3], "expected": 5}],
    )
    assert result.code_extracted is True
    assert result.all_passed is False
    assert result.test_case_results[0].passed is False
    assert result.test_case_results[0].actual == -1


def test_no_fenced_code_block_is_reported_distinctly_from_a_failure():
    result = grade_response(
        "I would implement it by adding the two numbers together.",
        "add",
        [{"input": [2, 3], "expected": 5}],
    )
    assert result.code_extracted is False
    assert result.all_passed is False
    assert result.test_case_results == []


def test_picks_the_block_that_defines_the_function_over_an_earlier_example_block():
    response = (
        "Example usage:\n```python\nprint(add(1, 2))\n```\n"
        "Here's the implementation:\n```python\ndef add(a, b):\n    return a + b\n```"
    )
    result = grade_response(response, "add", [{"input": [2, 3], "expected": 5}])
    assert result.code_extracted is True
    assert result.all_passed is True


def test_order_insensitive_comparison_for_group_style_results():
    code = "def group_pairs(items):\n    return [[items[1], items[0]]]\n"
    result = grade_response(
        f"```python\n{code}```",
        "group_pairs",
        [
            {
                "input": [["a", "b"]],
                "expected": [["b", "a"]],
                "note": "order-insensitive: compare as a set of frozensets",
            }
        ],
    )
    assert result.all_passed is True


def test_network_access_is_actually_blocked():
    code = (
        "def try_connect():\n"
        "    import socket\n"
        "    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
        "    s.settimeout(2)\n"
        "    s.connect(('8.8.8.8', 53))\n"
        "    return 'reached'\n"
    )
    result = run_test_case(code, "try_connect", [], "reached")
    assert result.passed is False
    assert result.error is not None
    assert "unreachable" in result.error.lower() or "network" in result.error.lower()


def test_filesystem_write_outside_temp_dir_is_actually_blocked():
    code = (
        "def try_write():\n"
        "    with open('/tmp/switchyard-sandbox-escape-test.txt', 'w') as f:\n"
        "        f.write('escaped')\n"
        "    return 'wrote'\n"
    )
    result = run_test_case(code, "try_write", [], "wrote")
    assert result.passed is False
    assert result.error is not None
    assert "read-only" in result.error.lower()


def test_infinite_loop_hits_the_timeout():
    code = "def loop_forever():\n    while True:\n        pass\n"
    result = run_test_case(code, "loop_forever", [], None, timeout=2)
    assert result.passed is False
    assert result.timed_out is True or result.error is not None


def test_extract_python_code_returns_none_without_a_fence():
    assert extract_python_code("just prose, no code here", "add") is None


def test_extract_python_code_finds_the_matching_function():
    response = "```python\ndef subtract(a, b):\n    return a - b\n```"
    code = extract_python_code(response, "subtract")
    assert code is not None
    assert "def subtract(" in code
