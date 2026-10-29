





#1. สร้าง index ก่อน: python build_index.py
#2. จากนั้นรัน: python main.py


import os
import json
from pathlib import Path
from datetime import datetime, timezone

import config
from src import index_meta
from src.rag_pipeline import RAGPipeline

def print_answer(result):   # Display the answer and its source
    print()
    print(result["answer"])

    print(f"\nAnswer mode: {result.get('answer_mode', 'no_context')}")
    if config.SHOW_SOURCES and result["sources"]:
        print("\nSources:")
        for source in result["sources"]:
            print(f"  [{source['n']}] {source['question']}")
            print(f"      Line {source['line_no']} · Score {source['score']}")

    if config.SHOW_DEBUG:
        print(f"\n[Debug] Search queries: {result['queries_used']}")
        print(f"[Debug] Execution time (seconds): {result['timings']}")


def main():
    # Build the index if it doesn't exist
    if not os.path.exists(config.FAISS_INDEX_FILE):
        print("FAISS index not found.")
        print("Run: python build_index.py")
        return

    # if edit dataset and forget build 
    index_meta.warn_if_stale()

    print("--" * 30)
    print("Sexual Health Question Answering System")
    print("--" * 30)

    rag = RAGPipeline()
    rag.show_settings()

    print("\nHi Bro! 😎\nAsk me anything")

    demo_question = os.getenv("RAG_DEMO_QUERY", "").strip()
    if demo_question:
        print(f"\nQ: {demo_question}", flush=True)
        demo_result = rag.ask(demo_question)
        print_answer(demo_result)
        evidence = Path(__file__).resolve().parent / "evidence/gemini/live_window_demo.json"
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(json.dumps({
            "executed_at_utc": datetime.now(timezone.utc).isoformat(),
            "provider": config.LLM_PROVIDER, "model": config.LLM_MODEL,
            "question": demo_question, "result": demo_result,
            "ready_for_user_input": True, "key_value_saved": False,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print("\nDemo completed. Type your next question below (q to exit).", flush=True)

    while True:
        question = input("\nQ: ").strip()

        if question in ("exit", "quit", "q"):
            print("ขอบใจหลายๆ เด้อ !!!")
            break

        if not question:
            continue

        result = rag.ask(question)
        print_answer(result)


if __name__ == "__main__":
    main()
