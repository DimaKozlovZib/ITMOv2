import json
from pathlib import Path


def extract_clean_decision(event_file: Path, out_file: Path) -> None:
    # Read JSON Lines event stream as UTF-8 and extract the first text part
    if not event_file.exists():
        raise FileNotFoundError(str(event_file))
    text_payload = None
    with event_file.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get('type') == 'text':
                part = obj.get('part') or {}
                text = part.get('text')
                if isinstance(text, str):
                    text_payload = text
                    break
    if text_payload is None:
        raise ValueError(f"No text event found in {event_file}")
    # The text itself is a JSON string with {tool, arguments}
    try:
        clean_obj = json.loads(text_payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Text payload is not valid JSON in {event_file}: {exc}")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(clean_obj, ensure_ascii=False), encoding='utf-8')


def main():
    base = Path(__file__).resolve().parents[1]
    before = base / 'evidence' / 'before'
    after_ai = base / 'evidence' / 'after' / 'assistant_execute_injection'

    pairs = [
        (before / 'baseline_decision.json', before / 'baseline_decision_clean.json'),
        (base / 'evidence' / 'current_decision.json', base / 'evidence' / 'current_decision_clean.json'),
        (after_ai / 'baseline_decision.json', after_ai / 'baseline_decision_clean.json'),
        (after_ai / 'current_decision.json', after_ai / 'current_decision_clean.json'),
    ]

    for src, dst in pairs:
        try:
            extract_clean_decision(src, dst)
            print(f"OK: {src} -> {dst}")
        except Exception as exc:
            print(f"ERROR: {src}: {exc}")


if __name__ == '__main__':
    main()
