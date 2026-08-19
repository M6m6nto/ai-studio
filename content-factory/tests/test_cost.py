from engines.common.registry import Registry
from tools.cost import record_cost, summarize


def test_record_cost_accumulates(tmp_path):
    r = Registry(tmp_path / "registry")
    item = r.new_item("Тема", source="instagram", codeword="СЛОВО")
    record_cost(r, item["slug"], "higgsfield_credits", 3.5)
    record_cost(r, item["slug"], "higgsfield_credits", 1.5)
    reloaded = r.load_item(item["slug"])
    assert reloaded["cost"]["higgsfield_credits"] == 5.0


def test_summarize_totals_across_items(tmp_path):
    r = Registry(tmp_path / "registry")
    a = r.new_item("Тема раз", source="instagram", codeword="РАЗ")
    b = r.new_item("Тема два", source="instagram", codeword="ДВА")
    record_cost(r, a["slug"], "rapidapi_calls", 2)
    record_cost(r, b["slug"], "rapidapi_calls", 3)
    result = summarize(r)
    assert result["totals"]["rapidapi_calls"] == 5
    assert result["per_item"][a["slug"]]["rapidapi_calls"] == 2
    assert result["per_item"][b["slug"]]["rapidapi_calls"] == 3


def test_summarize_empty_registry(tmp_path):
    r = Registry(tmp_path / "registry")
    result = summarize(r)
    assert result == {"totals": {}, "per_item": {}}
