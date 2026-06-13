import json

from db import BranchItem
from export import export_json


def _item(chain_id: str, store_id: str, code: str, name: str | None, price: float) -> BranchItem:
    return BranchItem(
        chain_id=chain_id,
        sub_chain_id="1",
        store_id=store_id,
        item_code=code,
        item_name=name,
        manufacturer="",
        unit_qty="",
        quantity="1",
        unit_of_measure="יחידה",
        price=price,
        unit_of_measure_price=None,
        price_update_date="2026-06-10",
    )


def _exported(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return [(p["barcode"], p["name"]) for p in data["items"]]


def test_nameless_item_borrows_name_from_other_chain(tmp_path):
    # Two cheap branches sit >=MIN_DEAL_DISCOUNT below the cross-store median
    # (pulled up by the pricier chains), so both pass the deal filter. The
    # nameless branch borrows "שמפו" from the named one.
    items = [
        _item("chainA", "001", "111", "שמפו", 7.0),
        _item("chainB", "002", "111", None, 7.0),
        _item("chainC", "003", "111", "שמפו", 10.0),
        _item("chainD", "004", "111", "שמפו", 10.0),
    ]

    export_json(items, stores=[], promos=[], output_dir=tmp_path)

    assert _exported(tmp_path / "store_chainA_001.json") == [("111", "שמפו")]
    assert _exported(tmp_path / "store_chainB_002.json") == [("111", "שמפו")]


def test_index_exposes_chain_names_for_present_chains(tmp_path):
    # The index carries a chainId -> display-name map so the frontend doesn't
    # hardcode its own copy. Only chains present in the run are included.
    items = [
        _item("7290027600007", "001", "111", "שמפו", 7.0),
        _item("7290058140886", "002", "111", "שמפו", 7.0),
        _item("7290027600007", "009", "111", "שמפו", 10.0),
        _item("7290058140886", "009", "111", "שמפו", 10.0),
    ]

    export_json(items, stores=[], promos=[], output_dir=tmp_path)

    index = json.loads((tmp_path / "stores.json").read_text(encoding="utf-8"))
    assert index["chains"] == {
        "7290027600007": "Shufersal",
        "7290058140886": "Rami Levy",
    }


def test_item_unnamed_in_every_chain_is_dropped(tmp_path):
    items = [
        # Named item, a clear deal in chains A and B (median pulled up by C/D).
        _item("chainA", "001", "111", "שמפו", 7.0),
        _item("chainB", "002", "111", "שמפו", 7.0),
        _item("chainC", "003", "111", "שמפו", 10.0),
        _item("chainD", "004", "111", "שמפו", 10.0),
        # Same deal-worthy price shape, but no chain names this barcode (None
        # and empty string), so it's dropped despite being cheap.
        _item("chainA", "001", "222", None, 4.0),
        _item("chainB", "002", "222", "", 4.0),
        _item("chainC", "003", "222", None, 10.0),
        _item("chainD", "004", "222", None, 10.0),
    ]

    export_json(items, stores=[], promos=[], output_dir=tmp_path)

    assert _exported(tmp_path / "store_chainA_001.json") == [("111", "שמפו")]
    assert _exported(tmp_path / "store_chainB_002.json") == [("111", "שמפו")]
