import json
from pathlib import Path


def try_repair(text: str) -> str:
    """Attempt to repair mojibake by re-encoding with likely Windows codepages and decoding as UTF-8."""
    if not isinstance(text, str):
        return text
    candidates = []
    encodings = ["cp1251", "cp866", "cp437", "latin1"]
    for enc in encodings:
        try:
            repaired = text.encode(enc, errors="strict").decode("utf-8", errors="strict")
            candidates.append((enc, repaired))
        except Exception:
            continue
    if not candidates:
        return text
    # Heuristic: prefer candidate with most Cyrillic letters and fewest box-drawing chars
    def score(s: str) -> tuple[int, int]:
        cyr = sum(1 for ch in s if "\u0400" <= ch <= "\u04FF")
        bad = s.count("╨") + s.count("тА") + s.count("�")
        return (cyr, -bad)
    best = max(candidates, key=lambda x: score(x[1]))
    return best[1]


def fix_file(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Skip (read error): {path}: {exc}")
        return False
    changed = False
    try:
        reason = data.get("arguments", {}).get("reason")
        if isinstance(reason, str):
            repaired = try_repair(reason)
            if repaired != reason:
                data["arguments"]["reason"] = repaired
                changed = True
    except Exception:
        pass
    if changed:
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        print(f"Fixed: {path}")
    else:
        print(f"No change: {path}")
    return changed


def main():
    base = Path(__file__).resolve().parents[1]
    targets = [
        base / "evidence" / "before" / "baseline_decision_clean.json",
        base / "evidence" / "current_decision_clean.json",
        base / "evidence" / "after" / "assistant_execute_injection" / "baseline_decision_clean.json",
        base / "evidence" / "after" / "assistant_execute_injection" / "current_decision_clean.json",
    ]
    for t in targets:
        if t.exists():
            fix_file(t)
        else:
            print(f"Missing: {t}")


if __name__ == "__main__":
    main()
