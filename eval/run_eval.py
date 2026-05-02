"""Eval runner — scores the agent against eval/dataset.jsonl.

Usage:
    uv run python eval/run_eval.py
    uv run python eval/run_eval.py --ids 1,2,3   # run specific questions
"""

import argparse
import asyncio
import json
import time
from pathlib import Path

from langchain_core.messages import HumanMessage

from app.agents.graph import build_graph

DATASET = Path(__file__).parent / "dataset.jsonl"


def load_dataset(ids: list[int] | None = None) -> list[dict]:
    rows = [json.loads(l) for l in DATASET.read_text(encoding="utf-8").splitlines() if l.strip()]
    if ids:
        rows = [r for r in rows if r["id"] in ids]
    return rows


async def run_question(graph, row: dict) -> dict:
    start = time.monotonic()
    try:
        result = await graph.ainvoke({
            "messages": [HumanMessage(content=row["question"])],
            "intent": "",
            "tool_results": [],
        })
        latency = time.monotonic() - start
        intent = result["intent"]
        answer = result["messages"][-1].content

        intent_ok = intent == row["intent"]
        answer_lower = answer.lower()
        keyword_hits = [kw for kw in row["must_contain"] if kw.lower() in answer_lower]
        keywords_ok = len(keyword_hits) == len(row["must_contain"])

        return {
            "id": row["id"],
            "difficulty": row["difficulty"],
            "intent_expected": row["intent"],
            "intent_got": intent,
            "intent_ok": intent_ok,
            "keywords_ok": keywords_ok,
            "keywords_missing": [kw for kw in row["must_contain"] if kw.lower() not in answer_lower],
            "latency_s": round(latency, 2),
            "pass": intent_ok and keywords_ok,
        }
    except Exception as e:
        return {
            "id": row["id"],
            "difficulty": row["difficulty"],
            "intent_expected": row["intent"],
            "intent_got": "ERROR",
            "intent_ok": False,
            "keywords_ok": False,
            "keywords_missing": row["must_contain"],
            "latency_s": round(time.monotonic() - start, 2),
            "pass": False,
            "error": str(e),
        }


def print_report(results: list[dict]) -> None:
    passed = sum(1 for r in results if r["pass"])
    total = len(results)
    avg_latency = sum(r["latency_s"] for r in results) / total

    print("\n" + "=" * 70)
    print(f"  EVAL RESULTS — {passed}/{total} passed ({passed/total*100:.1f}%)")
    print(f"  Avg latency: {avg_latency:.2f}s")
    print("=" * 70)

    header = f"{'ID':>3}  {'Diff':<8}  {'Intent':>10}  {'Got':>10}  {'KW':>4}  {'Lat':>5}  {'Pass'}"
    print(header)
    print("-" * 70)

    for r in sorted(results, key=lambda x: x["id"]):
        intent_str = r["intent_got"] if r["intent_ok"] else f"!{r['intent_got']}"
        kw_str = "OK" if r["keywords_ok"] else f"!{len(r['keywords_missing'])}"
        status = "PASS" if r["pass"] else "FAIL"
        print(f"{r['id']:>3}  {r['difficulty']:<8}  {r['intent_expected']:>10}  {intent_str:>10}  {kw_str:>4}  {r['latency_s']:>4.1f}s  {status}")
        if not r["keywords_ok"]:
            print(f"     missing: {r['keywords_missing']}")

    # Breakdown by intent
    print("\n--- By intent ---")
    by_intent: dict[str, list] = {}
    for r in results:
        by_intent.setdefault(r["intent_expected"], []).append(r["pass"])
    for intent, passes in sorted(by_intent.items()):
        pct = sum(passes) / len(passes) * 100
        print(f"  {intent:<12}: {sum(passes)}/{len(passes)} ({pct:.0f}%)")

    # Breakdown by difficulty
    print("\n--- By difficulty ---")
    by_diff: dict[str, list] = {}
    for r in results:
        by_diff.setdefault(r["difficulty"], []).append(r["pass"])
    for diff, passes in sorted(by_diff.items()):
        pct = sum(passes) / len(passes) * 100
        print(f"  {diff:<8}: {sum(passes)}/{len(passes)} ({pct:.0f}%)")

    print("=" * 70)


async def main(ids: list[int] | None = None) -> None:
    dataset = load_dataset(ids)
    print(f"Running eval on {len(dataset)} questions...")
    graph = build_graph()
    results = []
    for i, row in enumerate(dataset, 1):
        print(f"[{i}/{len(dataset)}] Q{row['id']}: {row['question'][:60]}...")
        result = await run_question(graph, row)
        results.append(result)
        status = "PASS" if result["pass"] else "FAIL"
        print(f"         → {status} | intent: {result['intent_got']} | {result['latency_s']}s")

    print_report(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", type=str, help="Comma-separated question IDs to run")
    args = parser.parse_args()
    ids = [int(x) for x in args.ids.split(",")] if args.ids else None
    asyncio.run(main(ids))
