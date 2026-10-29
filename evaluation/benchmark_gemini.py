"""Compare three retrieval settings and real Gemini answers on one frozen golden set."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time

os.environ["RAG_LLM_PROVIDER"] = "gemini"
os.environ["RAG_LLM_MODEL"] = os.getenv("RAG_GEMINI_MODEL", "gemini-3.5-flash-lite")
os.environ["RAG_USE_LLM"] = "1"
import config
from evaluation.metrics import evaluate_one, average
from evaluation.eval_generation import word_overlap, is_refusal
from src.prompt_templates import format_context
from src.citations import citation_status

ROOT = Path(__file__).resolve().parents[1]
METHODS = ("dense_only", "hybrid", "hybrid_rerank")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def status_code(error):
    while error:
        if isinstance(getattr(error, "status_code", None), int):
            return error.status_code
        error = error.__cause__
    return None


def answer_metrics(answer, chunks, reference):
    text = answer.replace(config.DISCLAIMER, "").strip()
    citations = citation_status(text, len(chunks))
    clean_text = re.sub(r"\[[\d,;\s–-]+\]", "", text)
    clean_context = re.sub(r"\[[\d,;\s–-]+\]", "", format_context(chunks))
    return {"refused": is_refusal(text), "has_citation": citations["has_citation"],
            "citations_valid": citations["citations_valid"],
            "answer_context_token_overlap": round(word_overlap(clean_text, clean_context), 4),
            "answer_reference_token_precision": round(word_overlap(clean_text, reference), 4),
            "answer_reference_token_recall": round(word_overlap(reference, clean_text), 4)}


def build_report(folder, manifest, rows):
    summary = {"model": manifest["settings"]["llm_model"], "n_items": manifest["n_items"],
               "expected_trials": manifest["expected_trials"], "completed_trials": len(rows),
               "successful_answers": sum(r["status"] == "ok" for r in rows),
               "all_complete": len(rows) == manifest["expected_trials"] and all(r["status"] == "ok" for r in rows),
               "methods": {}, "golden_sha256": manifest["settings"]["golden_sha256"],
               "metrics_note": "Token-overlap measures are lexical proxies, not factual correctness or human validation.",
               "scoring_version": "grouped-citations-v2"}
    for method in METHODS:
        trials = [r for r in rows if r["method"] == method]
        successful = [r for r in trials if r["status"] == "ok"]
        summary["methods"][method] = {
            "n_trials": len(trials), "n_successful_answers": len(successful),
            "retrieval": average([r["retrieval_metrics"] for r in trials]),
            "answer_metrics": {key: round(sum(r["answer_metrics"][key] for r in successful)/len(successful), 4)
                               for key in successful[0]["answer_metrics"]} if successful else {},
            "mean_retrieval_seconds": round(sum(r["retrieval_seconds"] for r in trials)/len(trials), 3) if trials else None,
            "mean_generation_seconds": round(sum(r["generation_seconds"] for r in successful)/len(successful), 3) if successful else None}
    (folder / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    retrieval = ["| วิธี | คำถาม | Hit@1 | Hit@3 | Hit@10 | MRR | nDCG@3 | ค้นหาเฉลี่ย (s) |",
                 "|---|---:|---:|---:|---:|---:|---:|---:|"]
    generation = ["| วิธี | Gemini ตอบสำเร็จ | citation valid | context token overlap | reference token precision | reference token recall | Gemini เฉลี่ย (s) |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
    for method, data in summary["methods"].items():
        if not data["n_trials"]:
            continue
        scores = data["retrieval"]
        retrieval.append(f"| {method} | {data['n_trials']} | {scores['hit@1']:.4f} | {scores['hit@3']:.4f} | {scores['hit@10']:.4f} | {scores['mrr']:.4f} | {scores['ndcg@3']:.4f} | {data['mean_retrieval_seconds']} |")
        if data["n_successful_answers"]:
            score = data["answer_metrics"]
            generation.append(f"| {method} | {data['n_successful_answers']} | {score['citations_valid']:.4f} | {score['answer_context_token_overlap']:.4f} | {score['answer_reference_token_precision']:.4f} | {score['answer_reference_token_recall']:.4f} | {data['mean_generation_seconds']} |")
    completed_methods = [name for name, data in summary["methods"].items() if data["n_trials"] == manifest["n_items"]]
    best_mrr = max(completed_methods, key=lambda name: summary["methods"][name]["retrieval"]["mrr"]) if len(completed_methods) == len(METHODS) else None
    discussion = (f"วิธีที่มี MRR สูงสุดในการทดลองนี้คือ {best_mrr} ผลนี้อิงเฉลยแบบ chunk ID ของชุดนี้ ไม่ใช่การยืนยันว่าเหนือกว่าทุกประเภทคำถาม"
                  if best_mrr else "การทดลองยังไม่ครบทุกวิธี จึงยังไม่สรุปว่าวิธีใดดีที่สุด")
    report = f"""# งาน 4: เปรียบเทียบ retrieval และคำตอบ Gemini บนคำถามชุดเดียวกัน

สถานะ: {'รันครบ' if summary['all_complete'] else 'กำลังรันหรือยังมีรายการไม่สำเร็จ'}
คำถาม {manifest['n_items']} ข้อ × 3 วิธี = {manifest['expected_trials']} trials
บันทึกแล้ว {len(rows)} trials; Gemini ตอบจริงสำเร็จ {summary['successful_answers']} รายการ
เริ่มเมื่อ UTC {manifest['started_at_utc']}; model = {summary['model']}

## การออกแบบการทดลอง

ตรึง data/golden_set.json เดิมเป็น golden_set_frozen.json และบันทึก SHA-256
ใช้ variant natural ของคำถามทุกข้อ ไม่เลือกเฉพาะข้อที่ผลดี
ทั้งสามวิธีใช้ corpus/index เดียวกัน embedding model เดียวกัน และส่ง Top-3 ให้ Gemini ด้วย prompt เดียวกัน
ค้น candidates 20 รายการ และเก็บ Top-10 สำหรับ metrics; Hybrid รวม BM25 + dense ด้วย RRF
hybrid_rerank เพิ่ม BAAI/bge-reranker-v2-m3 บน CPU โดยไม่เปลี่ยน LLM หรือคำถาม
ปิด memory และ LLM query transformation ใน benchmark เพื่อแยกผลของวิธีค้นหา
ส่วน rewrite/multi-query/HyDE และ memory มี functional live tests แยกใน evidence/gemini/

## ผล retrieval

{chr(10).join(retrieval)}

{discussion}

## ผลคำตอบ Gemini จริง

{chr(10).join(generation)}

ค่า citation valid ตรวจว่ามี [n] และเลขอยู่ในช่วง source ที่ส่งเข้า Gemini ไม่ได้ยืนยันว่าประโยคอ้างถูกข้อเท็จจริง
รองรับอ้างอิงเดี่ยว กลุ่ม [1, 2] และช่วง [1-3]; ตัดเลขอ้างอิงออกก่อนคำนวณ token overlap
context token overlap คือสัดส่วน token ในคำตอบที่พบใน context
reference token precision/recall วัดคำซ้ำเทียบคำตอบอ้างอิง ไม่ใช่คะแนน factual correctness
การเรียบเรียงใหม่และคำพ้องอาจทำให้คะแนนต่ำแม้ตอบถูก จึงต้องอ่านคำตอบจริงประกอบ

## ข้อจำกัด

- Golden set สร้างอัตโนมัติจาก corpus เดียวกับ index ไม่ใช่ benchmark ที่มนุษย์ตรวจอิสระ
- relevant_chunk_ids ผูกกับ Q&A เดิม บางคำตอบเทียบเท่าในระดับภาษาอื่นอาจไม่ถูกนับว่าถูก
- การทดลอง LLM เป็นหนึ่งคำตอบต่อ query/method ไม่มีการอ้างนัยสำคัญทางสถิติ
- ไม่ได้อ้างว่ามีคนตรวจข้อเท็จจริงของคำตอบทั้งหมด หรือใช้ผลนี้แทนคำแนะนำทางการแพทย์ได้
- เวลาเฉลี่ยไม่รวมการโหลดโมเดลครั้งแรก เวลาจำกัดอัตรา request และ backoff ก่อน retry

## หลักฐานและการรันซ้ำ

trials.jsonl เก็บคำถาม คำตอบ Gemini จริง แหล่งอ้างอิง ข้อความที่ส่งเข้าโมเดล อันดับค้นหา และคะแนนรายข้อ
manifest.json เก็บ configuration และ hash ของชุดคำถาม corpus index และ prompt
summary.json เก็บผลเฉลี่ยตามวิธี; ใช้ --resume เพื่อทำต่อโดยไม่เรียก API ซ้ำสำหรับรายการที่สำเร็จแล้ว
scored_trials.json เก็บคะแนนที่คำนวณใหม่จากคำตอบดิบด้วยตัวตรวจอ้างอิงแบบกลุ่ม โดยไม่เปลี่ยนคำตอบหรือเรียก API เพิ่ม
ตารางและ summary.json ใช้คะแนนเวอร์ชัน grouped-citations-v2; ค่าคะแนนเบื้องต้นใน trials.jsonl เก็บไว้เป็นประวัติพร้อมคำตอบดิบ
รัน: python -m evaluation.benchmark_gemini --resume
ใช้ Gemini key ผ่าน environment หรือเปิด RUN-EVALUATION.cmd เพื่อกรอกแบบซ่อนตัวอักษร
"""
    (ROOT / "GEMINI-EVALUATION-REPORT.md").write_text(report, encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--interval", type=float, default=3.1)
    parser.add_argument("--rescore-only", action="store_true", help="Recompute scores from saved real answers without API calls")
    args = parser.parse_args()
    if args.rescore_only:
        folder = ROOT / "outputs/benchmark"
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        rows = {}
        for line in (folder / "trials.jsonl").read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row["status"] == "ok":
                row["answer_metrics"] = answer_metrics(row["answer"], row["context"], row["reference_answer"])
            rows[row["trial_id"]] = row
        (folder / "scored_trials.json").write_text(json.dumps(list(rows.values()), ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(build_report(folder, manifest, list(rows.values())), ensure_ascii=False, indent=2))
        return
    from gemini_preflight import check_gemini, save_result
    preflight = check_gemini()
    save_result(preflight)
    if preflight["status"] != "ready":
        raise RuntimeError(preflight["message"])
    config.USE_LLM = True
    config.USE_HYBRID = True
    config.USE_MEMORY = False
    config.USE_QUERY_TRANSFORM = False
    from src.hybrid_retriever import HybridRetriever
    from src.rerankers import Reranker
    from src.generator import LLM, Generator
    folder = ROOT / "outputs/benchmark"
    folder.mkdir(parents=True, exist_ok=True)
    golden_bytes = Path(config.GOLDEN_SET_FILE).read_bytes()
    golden = json.loads(golden_bytes)
    items = golden["items"]
    assert len({item["id"] for item in items}) == len(items)
    settings = {"llm_model": config.LLM_MODEL, "golden_sha256": hashlib.sha256(golden_bytes).hexdigest(),
                "chunks_sha256": sha(config.CHUNK_STORE_FILE), "index_sha256": sha(config.FAISS_INDEX_FILE),
                "prompt_sha256": sha(ROOT / "src/prompt_templates.py"),
                "embedding_model": config.EMBEDDING_MODEL_NAME, "reranker_model": config.RERANK_MODEL_NAME,
                "top_k_context": 3, "candidate_k": config.CANDIDATE_K, "variant": "natural", "methods": list(METHODS)}
    manifest_path = folder / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["settings"] != settings:
            raise ValueError("Benchmark inputs differ from saved manifest; preserve this run and use a separate output folder.")
        if not args.resume:
            raise ValueError("Benchmark already exists. Use --resume to preserve completed API responses.")
    else:
        manifest = {"started_at_utc": datetime.now(timezone.utc).isoformat(), "settings": settings,
                    "n_items": len(items), "expected_trials": len(items)*len(METHODS), "key_value_saved": False}
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        (folder / "golden_set_frozen.json").write_bytes(golden_bytes)
    history_path = folder / "trials.jsonl"
    completed = {}
    if history_path.exists():
        for line in history_path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row["status"] == "ok":
                row["answer_metrics"] = answer_metrics(row["answer"], row["context"], row["reference_answer"])
                completed[row["trial_id"]] = row
    retriever = HybridRetriever()
    reranker = Reranker()
    llm = LLM()
    generator = Generator(llm)
    last_request = 0.0
    interval = max(0, args.interval)
    rows = dict(completed)
    for item in items:
        query = item["variants"].get("natural", item["question"])
        for method in METHODS:
            trial_id = method + ":" + item["id"]
            if trial_id in completed:
                print(f"RESUME {len(completed)}/{manifest['expected_trials']} {trial_id}", flush=True)
                continue
            config.USE_HYBRID = method != "dense_only"
            retriever.reranker = reranker if method == "hybrid_rerank" else None
            start = time.perf_counter()
            chunks = retriever.retrieve(query, top_k=10)
            retrieval_seconds = time.perf_counter()-start
            ids = [chunk["chunk_id"] for chunk in chunks]
            metrics = evaluate_one(ids, item["relevant_chunk_ids"], [1, 3, 10])
            row = {"trial_id": trial_id, "item_id": item["id"], "method": method, "query": query,
                   "reference_answer": item["reference_answer"], "expected_chunk_ids": item["relevant_chunk_ids"],
                   "retrieval_metrics": metrics, "retrieval_seconds": round(retrieval_seconds, 4),
                   "retrieved_top10_ids": ids, "context": chunks[:3]}
            result = None
            for attempt in range(1, 6):
                delay = interval - (time.monotonic()-last_request)
                if delay > 0:
                    time.sleep(delay)
                last_request = time.monotonic()
                started = time.perf_counter()
                try:
                    result = generator.generate(query, chunks[:3], history="")
                    assert result["answer_mode"] == "llm" and result["answer"].strip()
                    row.update({"generation_seconds": round(time.perf_counter()-started, 4), "attempts": attempt,
                                "status": "ok", "answer_mode": result["answer_mode"], "answer": result["answer"],
                                "sources": result["sources"],
                                "answer_metrics": answer_metrics(result["answer"], chunks[:3], item["reference_answer"])})
                    break
                except Exception as error:
                    code = status_code(error)
                    if attempt < 5 and (code in (429, 500, 502, 503, 504) or code is None):
                        wait = min(60, 15*attempt)
                        if code == 429:
                            interval = max(interval, 6.2)
                        print(f"Retry {trial_id}: {type(error).__name__}, HTTP {code}; waiting {wait}s", flush=True)
                        time.sleep(wait)
                        continue
                    row.update({"status": "error", "http_status": code, "error_type": type(error).__name__,
                                "message": "Request failed; key/provider response bodies were not logged.", "attempts": attempt})
                    break
            with history_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False)+"\n")
            rows[trial_id] = row
            summary = build_report(folder, manifest, list(rows.values()))
            print(f"[{len(rows)}/{manifest['expected_trials']}] {trial_id} {row['status'].upper()}", flush=True)
            if row["status"] != "ok" and row.get("http_status") in (401, 403, 404, 429):
                raise RuntimeError("Benchmark stopped on provider access/quota error. Completed trials are saved for --resume.")
    summary = build_report(folder, manifest, list(rows.values()))
    (folder / "scored_trials.json").write_text(json.dumps(list(rows.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if not summary["all_complete"]:
        raise RuntimeError("Some trials failed. Review results and resume; no failed trial was marked as a successful answer.")


if __name__ == "__main__":
    main()
