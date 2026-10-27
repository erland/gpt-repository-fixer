"""Keep a traceable migration gate for uniquely valuable legacy assertions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_safeguards_remain_traceable_until_replaced():
    manifest = json.loads((ROOT / "docs/migration-legacy-regression-inventory.json").read_text(encoding="utf-8"))
    assert manifest["version"] == 1
    checks = manifest["checks"]
    assert len(checks) >= 10
    assert len({item["id"] for item in checks}) == len(checks)
    for item in checks:
        assert item["replacement"] in {"pending", "verified"}
        assert item["requirement"].strip()
        source = ROOT / item["source"]
        assert source.is_file(), (item["id"], item["source"])
        assert item["needle"] in source.read_text(encoding="utf-8"), item["id"]
        # A guard may only be marked verified once a concrete canonical test is named.
        if item["replacement"] == "verified":
            assert item.get("canonical_test")
            assert (ROOT / item["canonical_test"]).is_file()
