from engines.pipeline.advisor import AUTO, BLOCKED, DONE, plan_next_actions


def make_item(**step_overrides):
    steps = {"trend": "done", "ref": "todo", "carousel": "todo", "guide": "todo",
             "reel": "todo", "funnel": "todo", "deliver": "todo"}
    steps.update(step_overrides)
    return {
        "steps": steps,
        "topic": {"ref_url": "https://example.com/post"},
        "script": {},
        "artifacts": {},
    }


def kinds(item, **kw):
    return {a.step: a.kind for a in plan_next_actions(item, **kw)}


def test_fresh_item_ref_is_auto_when_key_present():
    item = make_item()
    result = kinds(item, has_rapidapi_key=True, has_telegram_creds=False)
    assert result["ref"] == AUTO


def test_fresh_item_ref_is_blocked_without_key():
    item = make_item()
    result = kinds(item, has_rapidapi_key=False, has_telegram_creds=False)
    assert result["ref"] == BLOCKED


def test_ref_without_url_is_blocked_even_with_key():
    item = make_item()
    item["topic"] = {}
    result = kinds(item, has_rapidapi_key=True, has_telegram_creds=False)
    assert result["ref"] == BLOCKED


def test_carousel_blocked_without_script():
    item = make_item(ref="done")
    result = kinds(item, has_rapidapi_key=True, has_telegram_creds=False)
    assert result["carousel"] == BLOCKED


def test_carousel_auto_with_script():
    item = make_item(ref="done")
    item["script"] = {"body": "Текст."}
    result = kinds(item, has_rapidapi_key=True, has_telegram_creds=False)
    assert result["carousel"] == AUTO


def test_carousel_review_is_blocked_pending_human_acceptance():
    item = make_item(carousel="review")
    item["script"] = {"body": "Текст."}
    result = kinds(item, has_rapidapi_key=True, has_telegram_creds=False)
    assert result["carousel"] == BLOCKED


def test_funnel_blocked_until_guide_done():
    item = make_item(guide="review")
    result = kinds(item, has_rapidapi_key=True, has_telegram_creds=False)
    assert result["funnel"] == BLOCKED


def test_funnel_auto_once_guide_done():
    item = make_item(guide="done")
    result = kinds(item, has_rapidapi_key=True, has_telegram_creds=False)
    assert result["funnel"] == AUTO


def test_funnel_review_waits_for_chatplace_confirmation():
    item = make_item(guide="done", funnel="review")
    result = kinds(item, has_rapidapi_key=True, has_telegram_creds=False)
    assert result["funnel"] == BLOCKED


def test_reel_todo_needs_human_recording():
    item = make_item()
    result = kinds(item, has_rapidapi_key=True, has_telegram_creds=False)
    assert result["reel"] == BLOCKED


def test_reel_review_without_draft_waits_for_scenes():
    item = make_item(reel="review")
    result = plan_next_actions(item, has_rapidapi_key=True, has_telegram_creds=False)
    reel = next(a for a in result if a.step == "reel")
    assert reel.kind == BLOCKED
    assert "Higgsfield" in reel.message


def test_reel_review_with_draft_waits_for_acceptance():
    item = make_item(reel="review")
    item["artifacts"]["reel_draft_mp4"] = "reel_draft.mp4"
    result = plan_next_actions(item, has_rapidapi_key=True, has_telegram_creds=False)
    reel = next(a for a in result if a.step == "reel")
    assert reel.kind == BLOCKED
    assert "--accept" in reel.message


def test_deliver_requires_carousel_and_reel_done():
    item = make_item(carousel="done", reel="todo")
    result = kinds(item, has_rapidapi_key=True, has_telegram_creds=True)
    assert result["deliver"] == BLOCKED


def test_deliver_auto_when_ready_and_creds_present():
    item = make_item(carousel="done", reel="done")
    result = kinds(item, has_rapidapi_key=True, has_telegram_creds=True)
    assert result["deliver"] == AUTO


def test_deliver_blocked_without_telegram_creds():
    item = make_item(carousel="done", reel="done")
    result = kinds(item, has_rapidapi_key=True, has_telegram_creds=False)
    assert result["deliver"] == BLOCKED


def test_fully_done_item_reports_done_everywhere():
    item = make_item(ref="done", carousel="done", guide="done", reel="done",
                      funnel="done", deliver="done")
    result = kinds(item, has_rapidapi_key=True, has_telegram_creds=True)
    assert all(v == DONE for v in result.values())
