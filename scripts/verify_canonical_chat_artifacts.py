"""Exercise real analysis and fix-plan generation using scripts inside canonical Chat ZIP.

Rebuilds a temporary importable package from packaged Skill script bytes.
The repository checkout's scripts/lib is deliberately not imported.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


def check_artifact(text: str, heading: str, filename: str) -> None:
    assert isinstance(text, str) and text.startswith(heading), (
        f"{filename}: missing expected heading")
    assert len(text.strip().splitlines()) >= 5, f"{filename}: unexpectedly short"


def verify(root: Path) -> dict:
    report = json.loads((root / "MIGRATION-BUILD-REPORT.json").read_text(encoding="utf-8"))
    item = next(x for x in report["distributions"] if x["target"] == "chat")
    archive = root / "dist" / item["archive"]
    with tempfile.TemporaryDirectory(prefix="canonical-chat-artifacts-") as temporary:
        tmp = Path(temporary)
        runtime = tmp / "runtime"
        package = runtime / "scripts" / "packaged_chat_modules"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        packaged = {}
        with zipfile.ZipFile(archive) as zf:
            for name in zf.namelist():
                if name.startswith("templates/") and name.endswith(".tpl"):
                    destination = runtime / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(zf.read(name))
            for name in zf.namelist():
                path = PurePosixPath(name)
                if (len(path.parts) != 5 or path.parts[:2] != ("assistant", "skills")
                        or path.parts[3] != "scripts" or path.suffix != ".py"):
                    continue
                content = zf.read(name)
                if path.name in packaged and packaged[path.name] != content:
                    raise AssertionError(f"Conflicting packaged script: {path.name}")
                packaged[path.name] = content
        assert "e2e_analysis.py" in packaged, "Chat ZIP lacks packaged e2e_analysis.py"
        for name, source in packaged.items():
            (package / name).write_bytes(source)

        repo = tmp / "sample-repository"
        repo.mkdir()
        (repo / "package.json").write_text(json.dumps({
            "name": "canonical-chat-smoke",
            "scripts": {"build": "vite build", "test": "vitest run"},
            "devDependencies": {"vite": "^7.0.0", "vitest": "^3.0.0"},
        }), encoding="utf-8")
        (repo / "README.md").write_text(
            "# Sample repository\n\nInstall with npm install.\n"
            "Build with npm run build and test with npm test.\n", encoding="utf-8")
        (repo / "pnpm-lock.yaml").write_text("lockfileVersion: 9.0\n", encoding="utf-8")
        sys.path.insert(0, str(runtime / "scripts"))
        try:
            e2e = importlib.import_module("packaged_chat_modules.e2e_analysis")
            result = e2e.analyze_repository(repo, "canonical-chat-smoke")
            artifacts = {
                "repository-analysis.md": (result["report_markdown"], "# Repository analysis"),
                "repository-fix-plan.md": (result["plan_markdown"], "# Repository fix plan"),
            }
            output = tmp / "artifacts"
            output.mkdir()
            for filename, (text, heading) in artifacts.items():
                check_artifact(text, heading, filename)
                (output / filename).write_text(text, encoding="utf-8")
                check_artifact((output / filename).read_text(encoding="utf-8"),
                               heading, filename)
            assert result["report_model"]["repository_name"] == "canonical-chat-smoke"
            assert result["plan_model"]["repository_name"] == "canonical-chat-smoke"
            assert isinstance(result["findings"], list)
            return {"status": "pass", "archive": archive.name,
                    "artifacts": sorted(artifacts), "packaged_scripts": len(packaged)}
        finally:
            sys.path.remove(str(runtime / "scripts"))
            for name in list(sys.modules):
                if name == "packaged_chat_modules" or name.startswith("packaged_chat_modules."):
                    del sys.modules[name]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.project_root)
    (args.project_root / "CHAT-ARTIFACTS-REPORT.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
