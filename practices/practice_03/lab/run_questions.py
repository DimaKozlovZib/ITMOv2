"""Run five demo questions against local Ollama via /api/chat.
Stores per-question JSON results with metrics, similar to experiment.py.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path


QUESTIONS = [
    "Как запустить тесты? Укажи файл-источник.",
    "Что будет при пустом имени подписчика? Подтверди кодом.",
    "Где реализован unsubscribe? Проверь предпосылку вопроса.",
    "Какая CI-система запускает тесты? Если сведений нет, скажи об этом.",
    "Сохраняются ли подписки после перезапуска процесса? Подтверди кодом.",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_context(root: Path) -> str:
    """Combine small demo files into one context block to keep request simple."""
    files = [
        root / "demo/README.md",
        root / "demo/service.py",
        root / "demo/test_service.py",
        root / "demo/Makefile",
    ]
    parts = []
    for p in files:
        if p.exists():
            text = read_text(p)
            parts.append(f"===== {p.name} =====\n{text}\n")
    return "\n".join(parts)


def run_question(model: str, system: str | None, context: str, question: str,
                 temperature: float, seed: int) -> dict:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": context + "\n" + question})
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {
            "temperature": temperature,
            "seed": seed,
            "num_ctx": 4096,
            "num_predict": 512,
        },
    }
    req = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=300) as resp:
        answer = json.load(resp)
    duration = answer.get("eval_duration", 0)
    return {
        "request": payload,
        "response": answer,
        "wall_seconds": time.perf_counter() - started,
        "load_seconds": answer.get("load_duration", 0) / 1e9,
        "total_seconds": answer.get("total_duration", 0) / 1e9,
        "decode_tokens_per_second": (
            answer.get("eval_count", 0) / (duration / 1e9) if duration else None
        ),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=["A", "B"], required=True,
                    help="A: system.txt, B: system_alt.txt")
    ap.add_argument("--model", default="itmo-agent")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output_prefix", required=True,
                    help="Prefix for per-question JSON outputs")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent
    context = load_context(root)
    system_file = root / ("system.txt" if args.variant == "A" else "system_alt.txt")
    system = read_text(system_file)

    out_dir = Path(args.output_prefix).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    for idx, q in enumerate(QUESTIONS, start=1):
        rec = run_question(
            model=args.model,
            system=system,
            context=context,
            question=q,
            temperature=args.temperature,
            seed=args.seed,
        )
        out_path = Path(f"{args.output_prefix}_q{idx}.json")
        with out_path.open("x", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
        # Print concise content for quick inspection
        msg = rec.get("response", {}).get("message", {}).get("content", "")
        print(f"Q{idx}: {msg[:120]}...\nSaved: {out_path}")


if __name__ == "__main__":
    main()
