"""Live Gemini tests. Runs only when a real key and an accessible model are present."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import time
import subprocess

os.environ["RAG_LLM_PROVIDER"] = "gemini"
os.environ["RAG_LLM_MODEL"] = os.getenv("RAG_GEMINI_MODEL", "gemini-3.5-flash-lite")
os.environ["RAG_USE_LLM"] = "1"
import config
from gemini_preflight import check_gemini, save_result

ROOT = Path(__file__).resolve().parent


def main():
    folder = ROOT / "evidence/gemini"
    folder.mkdir(parents=True, exist_ok=True)
    preflight = check_gemini()
    save_result(preflight)
    output = {"started_at_utc": datetime.now(timezone.utc).isoformat(),
              "provider": "gemini", "model": config.LLM_MODEL, "checks": [],
              "preflight_status": preflight["status"], "all_passed": False,
              "cloud_inference_tested": False, "key_value_saved": False}

    def save():
        (folder / "live_checks.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    if preflight["status"] != "ready":
        output["status"] = "blocked_" + preflight["status"]
        save()
        print(preflight["message"])
        return 2
    from src.generator import LLM, Generator
    from src.query_transform import QueryTransformer
    from src.rag_pipeline import RAGPipeline

    def check(name, callback):
        started = time.perf_counter()
        try:
            details = callback()
            row = {"name": name, "passed": True, "seconds": round(time.perf_counter()-started, 3), "details": details}
        except Exception as error:
            # Do not persist provider exception bodies, headers, request URLs or credentials.
            row = {"name": name, "passed": False, "error_type": type(error).__name__,
                   "message": "Gemini request/check failed. Check model access, key, quota and internet connectivity."}
        output["checks"].append(row)
        save()
        print(name, "PASS" if row["passed"] else "FAIL", flush=True)
        if not row["passed"]:
            raise RuntimeError("Gemini check failed; see evidence/gemini/live_checks.json")

    llm = LLM()

    def smoke():
        answer = llm.chat([{"role": "user", "content": "Reply only GEMINI_OK"}])
        assert "GEMINI_OK" in answer
        output["cloud_inference_tested"] = True
        return {"answer": answer}
    check("real_gemini_request", smoke)
    rag = RAGPipeline()
    rag.generator = Generator(llm)
    rag.transformer = QueryTransformer(llm)

    def generation():
        rag.reset()
        result = rag.ask("PrEP คืออะไร")
        assert result["answer_mode"] == "llm" and result["sources"]
        citations = [int(n) for n in re.findall(r"\[(\d+)\]", result["answer"])]
        assert citations and all(1 <= n <= len(result["sources"]) for n in citations)
        return result
    check("gemini_rag_and_citations", generation)

    def out_of_scope():
        rag.reset()
        result = rag.ask("พยากรณ์ราคาบิตคอยน์พรุ่งนี้เป็นดอลลาร์ให้หน่อย")
        assert result["answer_mode"] == "llm"
        assert any(term in result["answer"] for term in ["ไม่พบข้อมูล", "ไม่มีข้อมูล", "ไม่สามารถ", "ข้อมูลไม่เพียงพอ"])
        return result
    check("gemini_out_of_scope_refusal", out_of_scope)

    for mode in ["rewrite", "multi_query", "hyde"]:
        def transform(mode=mode):
            config.USE_QUERY_TRANSFORM = True
            config.QUERY_TRANSFORM_MODE = mode
            queries = rag.transformer.transform("PrEP กับ PEP ต่างกันยังไง")
            assert queries and all(q.strip() for q in queries)
            if mode in ("multi_query", "hyde"):
                assert len(queries) > 1
            chunks = rag.retriever.retrieve(queries[0], top_k=3, extra_queries=queries[1:])
            assert len(chunks) == 3
            return {"queries": queries, "chunk_ids": [c["chunk_id"] for c in chunks]}
        check("gemini_transform_" + mode, transform)

    def memory():
        config.QUERY_TRANSFORM_MODE = "rewrite"
        rag.reset()
        first = rag.ask("PrEP คืออะไร")
        followup = rag.ask("แล้วมันต่างจาก PEP อย่างไร")
        assert first["answer_mode"] == followup["answer_mode"] == "llm"
        assert len(rag.memory.messages) == 4
        result = {"first": first, "followup": followup}
        rag.reset()
        assert not rag.memory.get_context()
        return result
    check("gemini_memory", memory)

    def launcher():
        run = subprocess.run(["cmd.exe", "/d", "/c", str(ROOT / "RUN-AI.cmd")],
                             input="PrEP คืออะไร\nq\n\n", capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=360)
        (folder / "launcher.txt").write_text(run.stdout + "\n" + run.stderr, encoding="utf-8")
        assert run.returncode == 0 and "Answer mode: llm" in run.stdout and "Sources:" in run.stdout
        return {"exit_code": run.returncode, "real_llm_answer": True, "sources_displayed": True}
    check("gemini_run_ai_cmd", launcher)

    from src.rerankers import Reranker
    reranker = Reranker()
    config.USE_QUERY_TRANSFORM = False
    def rerank():
        candidates = rag.retriever.retrieve("ถุงยางอนามัยแตกต้องทำยังไง", top_k=10)
        ranked = reranker.rerank("ถุงยางอนามัยแตกต้องทำยังไง", candidates, top_k=3)
        assert len(ranked) == 3 and all("retrieval_score" in chunk for chunk in ranked)
        assert all(ranked[i]["score"] >= ranked[i+1]["score"] for i in range(len(ranked)-1))
        return {"candidates": len(candidates), "ranked": ranked}
    check("local_cross_encoder_with_gemini_project", rerank)

    def combined():
        config.USE_QUERY_TRANSFORM = True
        config.QUERY_TRANSFORM_MODE = "rewrite"
        rag.retriever.reranker = reranker
        rag.reset()
        result = rag.ask("PrEP คืออะไร")
        assert result["answer_mode"] == "llm" and result["sources"]
        assert all("retrieval_score" in chunk for chunk in result["retrieved"])
        citations = [int(n) for n in re.findall(r"\[(\d+)\]", result["answer"])]
        assert citations and all(1 <= n <= len(result["sources"]) for n in citations)
        return result
    check("gemini_rewrite_hybrid_local_rerank_generation_memory", combined)
    output["status"] = "passed"
    output["all_passed"] = True
    save()
    print("All Gemini live checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
