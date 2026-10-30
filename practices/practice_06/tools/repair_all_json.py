import json
from pathlib import Path


def try_repair(text: str) -> str:
    if not isinstance(text, str):
        return text
    # If looks fine (contains Cyrillic and no typical mojibake glyphs), keep
    bad_glyphs = ("\u2551", "\u2561", "\ufffd", "╨", "тА")
    if not any(g in text for g in bad_glyphs):
        return text
    candidates = []
    encodings = ["cp1251", "cp866", "latin1"]
    for enc in encodings:
        try:
            repaired = text.encode(enc, errors="strict").decode("utf-8", errors="strict")
            candidates.append((enc, repaired))
        except Exception:
            continue
    if not candidates:
        return text
    def score(s: str) -> tuple[int, int]:
        cyr = sum(1 for ch in s if "\u0400" <= ch <= "\u04FF")
        bad = sum(s.count(g) for g in bad_glyphs)
        return (cyr, -bad)
    best = max(candidates, key=lambda x: score(x[1]))
    return best[1]


def repair_json_file(path: Path) -> bool:
    # Try normal JSON first
    content = path.read_text(encoding="utf-8-sig")
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Treat as JSON Lines (event stream)
        changed = False
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                new_lines.append(line)
                continue
            try:
                obj = json.loads(line_stripped)
            except json.JSONDecodeError:
                new_lines.append(line)
                continue
            if obj.get("type") == "text":
                part = obj.get("part") or {}
                txt = part.get("text")
                if isinstance(txt, str) and txt.startswith("{") and txt.endswith("}"):
                    try:
                        inner = json.loads(txt)
                        reason = inner.get("arguments", {}).get("reason")
                        repaired = try_repair(reason)
                        if repaired != reason:
                            inner["arguments"]["reason"] = repaired
                            obj["part"]["text"] = json.dumps(inner, ensure_ascii=False)
                            changed = True
                    except Exception:
                        pass
            new_lines.append(json.dumps(obj, ensure_ascii=False))
        if changed:
            path.write_text("\n".join(new_lines) + ("\n" if content.endswith("\n") else ""), encoding="utf-8")
        return changed
    # Plain JSON object
    changed = False
    if isinstance(data, dict):
        try:
            args = data.get("arguments")
            if isinstance(args, dict):
                reason = args.get("reason")
                repaired = try_repair(reason)
                if repaired != reason:
                    data["arguments"]["reason"] = repaired
                    changed = True
        except Exception:
            pass
    if changed:
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return changed


def main():
    base = Path(__file__).resolve().parents[1] / "evidence"
    json_files = list(base.rglob("*.json"))
    total = 0
    fixed = 0
    for jf in json_files:
        total += 1
        try:
            if repair_json_file(jf):
                print(f"Fixed: {jf}")
                fixed += 1
        except Exception as exc:
            print(f"Error: {jf}: {exc}")
    print(f"Done: scanned={total}, fixed={fixed}")


if __name__ == "__main__":
    main()
