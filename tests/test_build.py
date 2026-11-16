from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "app"))

import build_cases  # noqa: E402
import scenario  # noqa: E402


def test_cases_carry_no_answers():
    for case in json.loads((HERE / "gold.cases.json").read_text())["cases"]:
        build_cases.validate_case(case)
        assert set(case) == {"id", "seed", "variant"}


@pytest.mark.parametrize(
    "case",
    [{"id": "case_09", "seed": 1}, {"id": "case_09", "seed": "1", "variant": "plain"},
     {"id": "case_09", "seed": 1, "variant": "nope"}, {"id": "case_09", "seed": 1, "variant": "plain", "total": 5}],
)
def test_bad_cases_are_refused(case):
    with pytest.raises(ValueError):
        build_cases.validate_case(case)


def test_expected_answer_matches_what_the_server_will_serve():
    for case in json.loads((HERE / "gold.cases.json").read_text())["cases"]:
        sc = scenario.make(case["seed"], case["variant"])
        answer = json.loads((HERE / "expected" / case["id"] / "answer.json").read_text())
        assert answer["total"] == sc["total"] == sum(i["price"] * i["qty"] for i in sc["items"])
        assert answer["preferred_label"] in {a["label"] for a in sc["addresses"]}


def test_shipped_scenario_file_names_only_seed_and_variant():
    for d in (HERE / "inputs").iterdir():
        assert set(json.loads((d / "scenario.json").read_text())) == {"seed", "variant"}


def test_the_wanted_address_is_not_printed_on_any_page():
    """The assistant can only learn which address is wanted by asking."""
    import threading
    import urllib.request

    sys.path.insert(0, str(HERE / "app"))
    import server

    sc = scenario.make(101, "plain")
    httpd, _ = server.serve(sc, 0, "127.0.0.1")
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{httpd.server_address[1]}"
        pages = [urllib.request.urlopen(base + p).read().decode() for p in ("/", "/cart", "/checkout")]
    finally:
        httpd.shutdown()
        httpd.server_close()
    for a in sc["addresses"]:
        assert pages[2].count(a["label"] + "：") == 1  # both listed, neither marked
    assert "✓" not in pages[2] and "已选：" not in pages[2]
