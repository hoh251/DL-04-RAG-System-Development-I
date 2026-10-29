"""Live tests of every available local component. No cloud provider requests."""
import json
import os
from pathlib import Path
import re
import time
from datetime import datetime, timezone
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("PYTHONUTF8", "1")
os.environ["RAG_LLM_PROVIDER"] = "ollama"
os.environ["RAG_LLM_MODEL"] = "qwen2.5:3b"
import config
from src.generator import Generator, LLM
from src.query_transform import QueryTransformer
from src.rag_pipeline import RAGPipeline
from src.rerankers import Reranker


def main():
    os.chdir(ROOT)
    evidence = ROOT / "evidence/full"
    evidence.mkdir(parents=True, exist_ok=True)
    output = {"executed_at_utc": datetime.now(timezone.utc).isoformat(),
              "provider": "ollama_local", "cloud_api_called": False, "checks": []}

    def check(name, callback):
        started = time.perf_counter()
        try:
            details = callback()
            row = {"name": name, "passed": True, "seconds": round(time.perf_counter()-started, 3), "details": details}
        except Exception as error:
            row = {"name": name, "passed": False, "error_type": type(error).__name__, "error": str(error)}
        output["checks"].append(row)
        (evidence / "live_checks.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(name, "PASS" if row["passed"] else "FAIL", flush=True)
        if not row["passed"]:
            raise RuntimeError(f"{name} failed; see evidence/full/live_checks.json")
        return row["details"]

    tags = check("ollama_models", lambda: json.load(urlopen("http://127.0.0.1:11434/api/tags", timeout=5)))
    assert any(m["name"] == config.LLM_MODEL for m in tags["models"])
    config.USE_LLM = True
    config.USE_QUERY_TRANSFORM = False
    config.USE_RERANK = False
    llm = LLM()

    def smoke():
        answer = llm.chat([{"role": "user", "content": "Reply with only LOCAL_OK"}])
        assert "LOCAL_OK" in answer
        return {"model": llm.model, "answer": answer}
    check("real_llm_request", smoke)

    def missing_model():
        from openai import NotFoundError
        original = llm.model
        llm.model = "course-test-model-that-does-not-exist"
        try:
            llm.chat([{"role": "user", "content": "test"}])
        except NotFoundError:
            return {"http_status": 404, "missing_model_detected": True}
        finally:
            llm.model = original
        raise AssertionError("Missing model unexpectedly succeeded")
    check("real_missing_model_error", missing_model)

    def unavailable_server():
        from openai import OpenAI, APIConnectionError
        client = OpenAI(base_url="http://127.0.0.1:1/v1", api_key="ollama", timeout=2, max_retries=0)
        try:
            client.chat.completions.create(model=config.LLM_MODEL, messages=[{"role": "user", "content": "test"}])
        except APIConnectionError:
            return {"connection_failure_detected": True}
        raise AssertionError("Unavailable server unexpectedly succeeded")
    check("real_unavailable_server_error", unavailable_server)
    rag = RAGPipeline()
    rag.generator = Generator(llm)
    rag.transformer = QueryTransformer(llm)

    def generate():
        results = []
        for query in ["PrEP คืออะไร", "ความยินยอมในเรื่องเพศคืออะไร"]:
            rag.reset()
            result = rag.ask(query)
            assert result["answer_mode"] == "llm" and result["sources"]
            citations = [int(n) for n in re.findall(r"\[(\d+)\]", result["answer"])]
            assert citations and all(1 <= n <= len(result["sources"]) for n in citations)
            results.append({"query": query, "result": result})
        return results
    check("grounded_llm_generation_and_citations", generate)

    def out_of_scope():
        rag.reset()
        result = rag.ask("พยากรณ์ราคาบิตคอยน์พรุ่งนี้เป็นดอลลาร์ให้หน่อย")
        assert result["answer_mode"] == "llm"
        assert any(s in result["answer"] for s in ["ไม่พบข้อมูล", "ไม่มีข้อมูล", "ไม่สามารถ", "ข้อมูลไม่เพียงพอ"])
        return result
    check("out_of_scope_llm_refusal", out_of_scope)

    def transform(mode):
        config.USE_QUERY_TRANSFORM = True
        config.QUERY_TRANSFORM_MODE = mode
        queries = rag.transformer.transform("PrEP กับ PEP ต่างกันยังไง")
        assert queries and all(q.strip() for q in queries)
        assert len(queries) > 1 if mode in ("multi_query", "hyde") else len(queries) == 1
        chunks = rag.retriever.retrieve(queries[0], top_k=3, extra_queries=queries[1:])
        assert len(chunks) == 3
        return {"queries": queries, "chunk_ids": [c["chunk_id"] for c in chunks]}
    for mode in ["rewrite", "multi_query", "hyde"]:
        check(f"query_transform_{mode}", lambda mode=mode: transform(mode))

    def memory():
        config.QUERY_TRANSFORM_MODE = "rewrite"
        rag.reset()
        first = rag.ask("PrEP คืออะไร")
        second = rag.ask("แล้วมันต่างจาก PEP อย่างไร")
        assert first["answer_mode"] == second["answer_mode"] == "llm"
        assert rag.memory.get_context() and len(rag.memory.messages) == 4
        assert "PrEP" in second["queries_used"][0] or "เพร็พ" in second["queries_used"][0]
        result = {"first": first, "followup": second, "history": rag.memory.get_context()}
        rag.reset()
        assert not rag.memory.get_context()
        return result
    check("real_multi_turn_memory_and_rewrite", memory)
    config.USE_QUERY_TRANSFORM = False

    def no_context():
        result = rag.generator.generate("คำถามที่ไม่มีหลักฐาน", [])
        assert result["no_context"] and not result["sources"]
        return result
    check("empty_context_refusal", no_context)

    reranker = Reranker()
    def rerank():
        rows = []
        for query in ["ถุงยางอนามัยแตกต้องทำยังไง", "PrEP กับ PEP ต่างกันยังไง"]:
            candidates = rag.retriever.retrieve(query, top_k=10)
            result = reranker.rerank(query, candidates, top_k=3)
            assert len(result) == 3 and all("retrieval_score" in c for c in result)
            assert all(result[i]["score"] >= result[i+1]["score"] for i in range(len(result)-1))
            rows.append({"query": query, "before": candidates, "after": result})
        return rows
    check("actual_cross_encoder_reranking", rerank)

    def realistic_queries():
        cases = [
            ("ถุงยางขาดระหว่างใช้งาน ต้องทำอะไรต่อ", ["ถุงยางอนามัยแตกหรือหลุด", "ใส่ถุงแล้วแต่แตก", "ถุงแตกคาใน"]),
            ("ยาเพร็พใช้ทำอะไร ใครควรกิน", ["PrEP คืออะไร"]),
            ("PEP กับ PrEP ไม่เหมือนกันตรงไหน", ["PEP คืออะไร"]),
            ("consent ในความสัมพันธ์หมายความว่าอะไร", ["ความยินยอม (consent)"]),
            ("ถ้าเขาเงียบเฉยไม่ได้ขัดขืน แปลว่าตกลงไหม", ["การนิ่งเงียบหรือไม่ขัดขืน"]),
            ("เริ่มไปแล้วแต่เปลี่ยนใจขอหยุดได้ไหม", ["ความยินยอมถอนคืน"]),
            ("ยาคุมแบบฉุกเฉินควรใช้ตอนไหน", ["ยาคุมฉุกเฉินทำงาน"]),
            ("ต้องตรวจคัดกรองโรคทางเพศทุกกี่เดือน", ["ควรตรวจคัดกรองโรคติดต่อทางเพศสัมพันธ์บ่อยแค่ไหน"]),
        ]
        rows = []
        original_hybrid = config.USE_HYBRID
        for query, labels in cases:
            relevant = {c["chunk_id"] for c in rag.retriever.chunks if any(label in c["question"] for label in labels)}
            assert relevant
            config.USE_HYBRID = False
            dense = rag.retriever.retrieve(query, top_k=3)
            config.USE_HYBRID = True
            candidates = rag.retriever.retrieve(query, top_k=10)
            ranked = reranker.rerank(query, candidates, top_k=3)
            row = {"query": query, "relevant_chunk_ids": sorted(relevant)}
            for name, chunks in [("dense", dense), ("hybrid", candidates[:3]), ("hybrid_rerank", ranked)]:
                row[name] = {"hit_at_1": chunks[0]["chunk_id"] in relevant,
                             "hit_at_3": bool({c["chunk_id"] for c in chunks[:3]} & relevant),
                             "questions": [c["question"] for c in chunks[:3]]}
            rows.append(row)
        config.USE_HYBRID = original_hybrid
        return {"n_queries": len(rows), "labels_authored_by": "AI; not an independent human-reviewed benchmark",
                "results": rows,
                "summary": {name: {metric: sum(row[name][metric] for row in rows)/len(rows)
                                    for metric in ["hit_at_1", "hit_at_3"]}
                            for name in ["dense", "hybrid", "hybrid_rerank"]}}
    check("realistic_query_quality_comparison", realistic_queries)
    rag.retriever.reranker = reranker

    def combined():
        config.USE_QUERY_TRANSFORM = True
        config.QUERY_TRANSFORM_MODE = "rewrite"
        rag.reset()
        result = rag.ask("PrEP คืออะไร")
        assert result["answer_mode"] == "llm" and result["sources"]
        assert all("retrieval_score" in c for c in result["retrieved"])
        return result
    check("combined_rewrite_hybrid_rerank_llm_memory", combined)
    output["all_passed"] = all(row["passed"] for row in output["checks"])
    (evidence / "live_checks.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print("ALL LIVE CHECKS PASSED", flush=True)


if __name__ == "__main__":
    main()
