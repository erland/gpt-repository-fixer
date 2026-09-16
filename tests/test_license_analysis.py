import json
from pathlib import Path

import jsonschema

from scripts.lib.license_analysis import analyze_license, identify_license, license_decision_prompt

ROOT = Path(__file__).resolve().parents[1]
DECISION_SCHEMA = json.loads((ROOT / "schemas" / "license-decision.schema.json").read_text())

MIT = """MIT License\n\nCopyright (c) 2026 Example Owner\n\nPermission is hereby granted, free of charge, to any person obtaining a copy\nof this software and associated documentation files (the \"Software\"), to deal\nin the Software without restriction.\n\nTHE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND.\n"""

APACHE = """Apache License\nVersion 2.0, January 2004\nhttp://www.apache.org/licenses/LICENSE-2.0\n"""


def classes(findings):
    return [f["classification"] for f in findings]


def test_identifies_common_license_texts_conservatively():
    assert identify_license(MIT) == "MIT"
    assert identify_license(APACHE) == "Apache-2.0"
    assert identify_license("Custom internal terms") is None


def test_missing_license_without_declaration_is_consider_and_requires_decision():
    findings = analyze_license({"README.md": "# Demo\nA demo project."})
    assert len(findings) == 1
    f = findings[0]
    assert f["classification"] == "consider"
    assert f["decision_required"] is True
    assert "inte i sig" in f["notes"][0]


def test_readme_mit_without_license_file_is_must_fix():
    findings = analyze_license({"README.md": "# Demo\n\n## License\nMIT License\n"})
    f = findings[0]
    assert f["classification"] == "must-fix"
    assert f["decision_required"] is True
    assert "MIT" in f["summary"]


def test_readme_mit_but_apache_license_is_conflict():
    findings = analyze_license({
        "README.md": "# Demo\n\n## License\nMIT License\n",
        "LICENSE": APACHE,
    })
    f = findings[0]
    assert f["classification"] == "must-fix"
    assert "olika licens" in f["title"]
    assert f["decision_required"] is True


def test_existing_matching_license_is_passed_and_untouched():
    findings = analyze_license({
        "README.md": "# Demo\n\n## License\nMIT License\n",
        "LICENSE": MIT,
    })
    assert classes(findings) == ["passed"]
    assert findings[0]["recommended_action"] is None
    assert findings[0]["decision_required"] is False


def test_placeholder_requires_user_metadata_decision():
    text = MIT.replace("Copyright (c) 2026 Example Owner", "Copyright (c) <year> <copyright holder>")
    findings = analyze_license({"LICENSE": text})
    placeholder = next(f for f in findings if "placeholder" in f["title"].lower())
    assert placeholder["classification"] == "recommended"
    assert placeholder["decision_required"] is True


def test_unknown_license_is_not_guessed():
    findings = analyze_license({"LICENSE": "Custom license terms for this project."})
    f = findings[0]
    assert f["classification"] == "consider"
    assert f["confidence"] == "medium"
    assert f["decision_required"] is True


def test_multiple_conflicting_license_files_require_decision():
    findings = analyze_license({"LICENSE": MIT, "COPYING": APACHE})
    f = findings[0]
    assert f["classification"] == "must-fix"
    assert f["decision_required"] is True


def test_decision_prompt_is_structured_and_never_auto_selects():
    finding = analyze_license({"README.md": "# Demo"})[0]
    decision = license_decision_prompt(finding)
    jsonschema.Draft202012Validator(DECISION_SCHEMA).validate(decision)
    ids = [q["id"] for q in decision["questions"]]
    assert ids == ["license_type", "copyright_holder", "copyright_year"]
    assert "selected_license" not in decision


def test_decision_prompt_rejects_non_decision_findings():
    finding = analyze_license({"LICENSE": MIT})[0]
    assert finding["classification"] == "passed"
    try:
        license_decision_prompt(finding)
        assert False, "expected ValueError"
    except ValueError:
        pass
