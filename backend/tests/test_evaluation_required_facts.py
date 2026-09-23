from app.evaluation.required_facts import check_required_facts


def test_all_facts_present_passes():
    response = "The team launched a referral program offering a $10 credit, which drove a 15% signup increase."
    ok, missing = check_required_facts(response, ["referral program", "$10 credit", "15%"])
    assert ok is True
    assert missing == []


def test_missing_fact_fails_and_is_named():
    response = "The team launched a referral program."
    ok, missing = check_required_facts(response, ["referral program", "$10 credit", "15%"])
    assert ok is False
    assert "$10 credit" in missing
    assert "15%" in missing
    assert "referral program" not in missing


def test_alternatives_list_accepts_any_match():
    response = "Login time dropped from 8 seconds to 2 seconds after the biometric redesign."
    ok, missing = check_required_facts(response, [["8s", "8 seconds"], ["2s", "2 seconds"], "biometric"])
    assert ok is True
    assert missing == []


def test_alternatives_list_fails_when_none_match():
    response = "Login is now much faster thanks to the redesign."
    ok, missing = check_required_facts(response, [["8s", "8 seconds"], ["2s", "2 seconds"], "biometric"])
    assert ok is False
    assert [["8s", "8 seconds"]] == [missing[0]]


def test_case_and_whitespace_insensitive():
    response = "  The   AUDIT found   SIX   areas,   three were prioritized.  "
    ok, missing = check_required_facts(response, ["six areas", "three"])
    assert ok is True
    assert missing == []
