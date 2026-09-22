# Manual grading — gemini-3.6-flash

**DO NOT GRADE THIS BATCH AS-IS.** Generated 2026-09-21 with a
512-token output cap that turned out too low for this model: `gemini-3.6-flash`
is a reasoning ("thinking") model, and invisible thinking tokens count
against the same cap as the visible answer. Most responses here got only
~16-20 tokens of real answer before hitting the cap and cutting off
mid-sentence (e.g. `coding-001` ends mid-word: "...non-integers. *
Option"). The cap is now fixed (raised to 2048,
`backend/app/providers/gemini_provider.py`) but this batch predates the
fix and needs regenerating. Also incomplete: `reasoning-004` and
`summarization-001` never got a response at all (hit Gemini's free-tier
daily quota of 20 requests/model). See
`docs/case-study/FAILURES_AND_LESSONS.md` (2026-09-21) for the full story.
Kept here as the raw record of what happened, not as gradeable data.

---

One entry per task: prompt, grading rubric (from the benchmark task's
`metadata.notes`), and the real Gemini response. Grade each against its
rubric — no automated evaluator scores these (`evaluation_type: manual`).

## coding-001 (coding, medium)

**Prompt:**

```
Write a Python function `factorial(n)` that returns the factorial of a non-negative integer n.
```

**Rubric:** No sandboxed code execution in V0; graded manually.

**Response:**

```
Include input validation for negative numbers and non-integers.
    *   Option
```

**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_

---

## coding-002 (coding, easy)

**Prompt:**

```
Write a Python function `is_even(n)` that returns True if n is even, False otherwise.
```

**Rubric:** Correct: returns `n % 2 == 0` (or equivalent). No sandboxed execution; graded manually.

**Response:**

```
Here is the Python function:

```python
def is_even(n):
    """Returns True if n is even, False otherwise."""
    return n % 2 == 0
```

### How it works:
The `%` operator calculates the remainder of dividing `n` by `2`. If the remainder is `0`, the number is even, so `n % 2 == 0` evaluates to `True`. Otherwise, it evaluates to `False`.

### Example usage:
```python
print(is_even(4))   # Output: True
print(is_even(7))   # Output: False
print(is_even(0))   # Output: True
print(is_even(-2))  # Output: True
```
```

**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_

---

## coding-003 (coding, medium)

**Prompt:**

```
Write a Python function `reverse_string(s)` that returns the reverse of the input string without using slicing.
```

**Rubric:** Correct: builds the reversed string via a loop, recursion, or reversed()/join() — does not use s[::-1] (that's the one thing the prompt explicitly disallows). Graded manually.

**Response:**

```
Here is a simple and Pythonic implementation using the built-in `reversed()` function and `
```

**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_

---

## coding-004 (coding, hard)

**Prompt:**

```
Write a Python function `is_palindrome(s)` that returns True if s reads the same forwards and backwards, ignoring case and spaces.
```

**Rubric:** Correct: normalizes case and strips spaces before comparing the string to its reverse. Edge case worth checking: an empty string (after stripping) should return True. Graded manually.

**Response:**

```
Here is the Python function to check if a string is a palindrome, ignoring case
```

**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_

---

## coding-005 (coding, medium)

**Prompt:**

```
Write a Python function `unique_items(lst)` that returns a list of the unique items in lst, preserving their original order.
```

**Rubric:** Correct: preserves first-occurrence order — e.g. via a seen-set with an explicit loop, or dict.fromkeys(lst). A bare `list(set(lst))` is wrong because set order is not guaranteed to match input order. Graded manually.

**Response:**

```
 / `set` approach is universally understood and clearly demonstrates the algorithm.
    *   Let's
```

**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_

---

## debugging-001 (debugging, hard)

**Prompt:**

```
The following Python function is supposed to return the sum of all numbers in a list but returns the wrong result for some inputs. Identify the bug and explain the fix.

def total(nums):
    return sum(nums[1:])
```

**Rubric:** Bug: nums[1:] skips the first element; should be nums[:] or nums.

**Response:**

```
### The Bug

The bug is in the slice expression **`nums[1:]
```

**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_

---

## debugging-002 (debugging, medium)

**Prompt:**

```
The following Python function is supposed to return the average of a list of numbers but crashes on an empty list.

def average(nums):
    return sum(nums) / len(nums)

Identify the bug and explain the fix.
```

**Rubric:** Bug: division by zero when nums is empty. Fix should check for the empty case first (e.g. `if not nums: return 0`) before dividing. Graded manually.

**Response:**

```
### The Bug

The bug is a **`ZeroDivisionError`**. 

When an empty list (`[]`) is passed to the function:
1. `sum([])` evaluates to `0`.
2. `len([])` evaluates to `0`.
3. Python attempts to calculate `0 / 0`, which triggers a `ZeroDivisionError` and causes the program to crash.

---

### The Fix

To fix this, check if the list is empty before attempting the division. You can return a default value (such as `0` or `None`) if the list has no elements.

#### Fixed Code:

```python
def average(nums):
    if not nums:
        return 0  # Return 0 (or None) if the list is empty
    return sum(nums
```

**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_

---

## debugging-003 (debugging, easy)

**Prompt:**

```
This function should double every number in a list but returns the original list unchanged.

def double_all(nums):
    for n in nums:
        n = n * 2
    return nums

Identify the bug and explain the fix.
```

**Rubric:** Bug: reassigning the loop variable n does not mutate the list. Fix should build a new list (e.g. `[n * 2 for n in nums]`) or index-assign `nums[i] = n * 2`. Graded manually.

**Response:**

```
### The Bug

In the code `for n in nums:`, the variable `n` is assigned the **value** of each element during iteration. 

When you do `n = n * 2`, you are simply reassigning the local loop variable `n` to a new number. You are **not** updating the actual element inside the `nums` list at that position. Furthermore, integers in Python are immutable, so you cannot modify them in place; you must update the list reference itself.

---

### The Fix

There are two common ways to fix this, depending on whether you want to modify the existing list in-place or return a brand-new list.

#### Option 1: Modify the list in-place (Using Indices)
To change the elements of the original list, you need to assign the new values back to the specific index using `enumerate()` or `range()`:

```python
def double_all(nums):
    for i in range(len(nums)):
        nums[i] = nums[i] * 2
    return nums
```

#### Option 2: Return a new list (List Comprehension - *Most Pythonic*)
If you don't need to mutate the original list, using a list comprehension is cleaner and more readable:

```python
def double_all(nums):
    return [n * 2 for n in nums]
```
```

**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_

---

## debugging-004 (debugging, hard)

**Prompt:**

```
This function is supposed to remove duplicates from a list while preserving order, but sometimes returns items out of order.

def dedupe(items):
    return list(set(items))

Identify the bug and explain the fix.
```

**Rubric:** Bug: converting to a set discards insertion order (sets are unordered). Fix should use a seen-set with an explicit loop, or `dict.fromkeys(items)`. Graded manually.

**Response:**

```

            *Code:*
            ```python
            def dedupe(items
```

**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_

---

## debugging-005 (debugging, medium)

**Prompt:**

```
This function is supposed to find the maximum value in a list but returns the wrong answer for lists containing only negative numbers.

def find_max(nums):
    best = 0
    for n in nums:
        if n > best:
            best = n
    return best

Identify the bug and explain the fix.
```

**Rubric:** Bug: initializing best = 0 means nothing beats it when every number is negative, so 0 is returned instead of the true (negative) maximum. Fix should initialize best = nums[0] (or float('-inf')). Graded manually.

**Response:**

```
Draft the Response:**

    *   **The Bug:** Explain *why* it fails. The variable
```

**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_

---

## reasoning-001 (reasoning, medium)

**Prompt:**

```
Alice is taller than Bob. Bob is taller than Carol. Who is the shortest? Explain your reasoning.
```

**Rubric:** Correct answer is Carol; graded manually in V0.

**Response:**

```
**Carol** is the shortest.

**Reasoning:**
1. **Alice > Bob:** Alice is taller than Bob, which means Bob is shorter than Alice.
2. **Bob > Carol:** Bob is taller than Carol, which means Carol is shorter than Bob.

By placing them in order from tallest to shortest, we get: **Alice → Bob → Carol**. Since Carol is shorter than Bob, and Bob is shorter than Alice, Carol is the shortest of the three.
```

**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_

---

## reasoning-002 (reasoning, easy)

**Prompt:**

```
If it is raining, Sam brings an umbrella. Sam did not bring an umbrella today. Is it raining? Explain your reasoning.
```

**Rubric:** Correct answer: No. By modus tollens, since bringing an umbrella is required if it's raining, and Sam did not bring one, it cannot be raining. Graded manually.

**Response:**

```
**No, it is not raining.**

### Explanation:
This is a classic logical deduction
```

**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_

---

## reasoning-003 (reasoning, medium)

**Prompt:**

```
A train leaves the station at 2:00pm traveling at 60 mph. Another train leaves the same station at 3:00pm traveling at 90 mph in the same direction. At what time does the second train catch up to the first? Explain your reasoning.
```

**Rubric:** Correct answer: 5:00pm. At 3:00pm the first train has a 60-mile head start; the second train closes the gap at 30 mph (90-60), taking 2 hours (60/30) to catch up: 3:00pm + 2h = 5:00pm. Graded manually.

**Response:**

```
3:00 PM + 2 hours = 5:00 PM.

6
```

**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_

---

## reasoning-004 (reasoning, hard)

**Prompt:**

```
Three friends, Alex, Bailey, and Casey, each own a different pet: a cat, a dog, and a fish. Alex does not own the cat or the fish. Bailey does not own the fish. Who owns which pet? Explain your reasoning.
```

**Rubric:** Correct answer: Alex owns the dog (excluded from cat and fish, so dog is the only option left). Bailey owns the cat (excluded from fish, and dog is already taken by Alex). Casey owns the fish (the only pet remaining). Graded manually.

**FAILED:** Gemini request failed: Client error '429 Too Many Requests' for url 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429

**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_

---

## reasoning-005 (reasoning, medium)

**Prompt:**

```
A shop sells apples for $2 each and oranges for $3 each. Jordan spent $17 total and bought 6 pieces of fruit. How many apples and how many oranges did Jordan buy? Explain your reasoning.
```

**Rubric:** Correct answer: 1 apple and 5 oranges. Solving a + o = 6 and 2a + 3o = 17 gives a = 1, o = 5 (check: 2(1) + 3(5) = 17). Graded manually.

**Response:**

```
Jordan bought **1 apple** and **5 oranges**.

### Explanation of Reasoning:

You can solve
```

**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_

---

## summarization-001 (summarization, medium)

**Prompt:**

```
Summarize the following update in one sentence: The team shipped the new billing dashboard this week, fixed three long-standing sync bugs, and began migrating the notification service off the legacy queue, with full migration expected by the end of next month.
```

**Rubric:** No deterministic evaluator for summary quality in V0; requires manual review.

**FAILED:** Gemini request failed: Client error '429 Too Many Requests' for url 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429

**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_

---

## summarization-002 (summarization, easy)

**Prompt:**

```
Summarize the following update in one sentence: The support team resolved all outstanding customer tickets and closed out the sprint a day early.
```

**Rubric:** Correct: a one-sentence summary capturing both that tickets were resolved and the sprint finished early, with no fabricated details. Graded manually.

**Response:**

```
The support team completed the sprint a day early after resolving all outstanding customer tickets.
```

**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_

---

## summarization-003 (summarization, medium)

**Prompt:**

```
Summarize the following in one sentence: Q3 revenue grew 12% year over year driven by strong subscription renewals, though new customer acquisition slowed compared to Q2 due to increased competition.
```

**Rubric:** Correct: captures both the revenue growth (12% YoY, driven by renewals) and the slowdown in new customer acquisition (due to competition) — a summary that drops either half is incomplete. Graded manually.

**Response:**

```
Q3 revenue grew 12% year over year due to strong subscription renewals, despite
```

**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_

---

## summarization-004 (summarization, hard)

**Prompt:**

```
Summarize the following in two sentences: The engineering team migrated the primary database to a new provider over the weekend with zero downtime, but discovered afterward that a subset of analytics events were not being recorded correctly during the transition window, affecting roughly 4 hours of data; a backfill job has been scheduled to reconstruct the missing events from raw logs by end of week.
```

**Rubric:** Correct: two sentences covering (1) the migration succeeded with zero downtime, and (2) a ~4-hour analytics data gap was found with a backfill scheduled. Mark incomplete if it drops the backfill plan or the downtime detail. Graded manually.

**Response:**

```
Although the engineering team successfully migrated the primary database over the weekend with zero downtime, a transition issue caused
```

**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_

---

## summarization-005 (summarization, medium)

**Prompt:**

```
Summarize the following update in one sentence: The mobile app's login flow was redesigned to use biometric authentication by default, reducing average login time from 8 seconds to 2 seconds in early testing.
```

**Rubric:** Correct: mentions the biometric redesign and the login-time improvement (8s to 2s). Omitting the change entirely is incorrect; omitting only the specific numbers is a minor deduction, not a failure. Graded manually.

**Response:**

```
The mobile app's login flow now defaults to biometric authentication, reducing average login times from 8 seconds to 2 seconds in early testing.
```

**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_

---
