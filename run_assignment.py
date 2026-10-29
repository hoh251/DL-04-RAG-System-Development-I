"""Rebuild indexes, compare retrieval modes, and save reproducible evidence."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat", action="store_true")
    args = parser.parse_args()
    os.chdir(ROOT)
    if args.chat:
        subprocess.run([sys.executable, "main.py"], check=True)
        return
    os.environ["RAG_USE_LLM"] = "0"  # Baseline never consumes cloud quota through inherited settings
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    commands = [
        ("build_index", ["build_index.py"]),
        ("build_golden_set", ["-m", "evaluation.build_golden_set"]),
        ("eval_retrieval", ["-m", "evaluation.eval_retrieval"]),
        ("eval_extractive_answers", ["-m", "evaluation.eval_generation"]),
    ]
    for name, command in commands:
        run = subprocess.run([sys.executable, *command], capture_output=True,
                             text=True, encoding="utf-8", errors="replace")
        (evidence / f"{name}.txt").write_text(run.stdout + "\n" + run.stderr, encoding="utf-8")
        print(name, "PASS" if run.returncode == 0 else "FAIL", flush=True)
        if run.returncode:
            raise RuntimeError(f"See evidence/{name}.txt")
    import config
    from src.rag_pipeline import RAGPipeline
    from src.query_transform import normalize_query
    assert normalize_query("ถุงยางอนามัย") == "ถุงยางอนามัย"
    rag = RAGPipeline()
    samples = []
    for query in ["PrEP คืออะไร", "ถุงยางอนามัยแตกต้องทำยังไง", "ความยินยอมในเรื่องเพศคืออะไร"]:
        rag.reset()
        result = rag.ask(query)
        assert result["answer_mode"] == "extractive" and result["sources"]
        assert config.NO_CONTEXT_MESSAGE not in result["answer"]
        assert "[1]" in result["answer"]
        samples.append({"query": query, "result": result})
    assert rag.memory.get_context()
    rag.reset()
    assert not rag.memory.get_context()
    (evidence / "sample_answers.json").write_text(json.dumps(samples, ensure_ascii=False, indent=2), encoding="utf-8")
    evaluation = json.loads((ROOT / "outputs/eval_retrieval.json").read_text(encoding="utf-8"))
    answer_eval = json.loads((ROOT / "outputs/eval_generation.json").read_text(encoding="utf-8"))
    table = ["| วิธีค้นหา | Hit@1 | Hit@10 | MRR | nDCG@3 | ms/query |", "|---|---:|---:|---:|---:|---:|"]
    for name, item in evaluation["results"].items():
        score = item["overall"]
        table.append(f"| {name} | {score['hit@1']:.4f} | {score['hit@10']:.4f} | {score['mrr']:.4f} | {score['ndcg@3']:.4f} | {item['ms_per_query']} |")
    best = max(evaluation["results"], key=lambda name: evaluation["results"][name]["overall"]["mrr"])
    stamp = datetime.now(timezone.utc).isoformat()
    summary = {"executed_at_utc": stamp, "n_items": evaluation["n_items"],
               "retrieval_modes": list(evaluation["results"]), "best_mrr_mode": best,
               "answer_mode": "extractive", "llm_tested": False, "reranker_tested": False,
               "query_transform_llm_tested": False, "sample_answer_checks": len(samples),
               "memory_add_and_reset": "passed"}
    (evidence / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    report = f"""# ใบงาน 4: Mod RAG — บันทึกผลการทดลองจริง

แหล่งโค้ด: aproot-en/Advanced-Topic-in-Computer-Software-Course, commit c0db2ac
รันเมื่อ (UTC): {stamp}

รายงานนี้เป็นการทดลองพื้นฐานแบบ extractive เท่านั้น ผลทดสอบเพิ่มเติมของ LLM จริง,
query transformation และ reranking อยู่ใน FULL-TEST-REPORT.md และ evidence/full/live_checks.json

## การพัฒนาและการตั้งค่า

ใช้ฐานข้อมูล Q&A เดิม สร้าง embedding และ FAISS ใหม่ พร้อม BM25 index ที่ตัดคำด้วย PyThaiNLP
ระบบแยกเป็น loader, chunker, embedding, vector store, hybrid retriever, query transform,
generator และ conversation memory ปรับการทำงานได้ใน config.py

ทดสอบ dense-only, BM25-only และ hybrid ที่รวมอันดับด้วย RRF บน golden set ชุดเดียวกัน
จำนวน {evaluation['n_items']} รายการ พร้อม variants ที่มีอยู่ในแต่ละข้อ
ตั้ง USE_LLM=False จึงคืนข้อความจาก chunk แรกพร้อม [1] และแสดงแหล่งข้อมูล
ไม่มีการเรียก API ที่เสียเงิน

## ผลการเปรียบเทียบ retrieval

{chr(10).join(table)}

วิธีที่มี MRR สูงสุดในชุดทดลองนี้คือ `{best}` ตัวเลขนี้เป็นผลจริง ไม่ได้กำหนดให้ hybrid ต้องดีที่สุด
Hit@k คือสัดส่วนคำถามที่มี chunk เป้าหมายใน k อันดับแรก ส่วน MRR ให้ความสำคัญกับอันดับแรกที่ถูกต้อง
nDCG@3 คำนึงถึงอันดับของเอกสารที่เกี่ยวข้องในสามอันดับแรก

## การทดสอบคำตอบและ memory

ทดสอบตัวอย่าง {len(samples)} คำถามว่ามีคำตอบแบบ extractive พร้อมแหล่งอ้างอิง และไม่ปฏิเสธเพราะ parser ผิด
ทดสอบเพิ่มและล้างประวัติสำเร็จ ผลเต็มอยู่ใน evidence/sample_answers.json
ประวัติถูกจัดเก็บจริง แต่ยังไม่ได้ประเมินการเข้าใจคำถามต่อเนื่องด้วย LLM
ผล outputs/eval_generation.json เป็นการวัดคำซ้ำของข้อความที่ดึงมาเท่านั้น
ไม่ใช่หลักฐานคุณภาพการสร้างคำตอบด้วย LLM หรือคะแนนตรวจสอบข้อเท็จจริง

## ข้อจำกัดและส่วนที่ยังต้องทดลอง

- Golden set สร้างอัตโนมัติจากฐานข้อมูลเดียวกับ index จึงเป็นการทดสอบ retrieval ภายในชุดข้อมูล
  ไม่ใช่ผลทดสอบกับคำถามอิสระที่มนุษย์ตรวจแล้ว และไม่ควรอ้างว่าสะท้อนการใช้งานจริงทั้งหมด
- การแปลงคำถามใน golden set บางกรณีเปลี่ยนความหมาย จึงต้องตรวจคู่คำถามด้วยคนก่อนอ้างผลเชิงวิจัย
- รายงาน baseline นี้ไม่รวมผล LLM; ผล functional tests ของ cross-encoder และ Gemini อยู่ใน FULL-TEST-REPORT.md
- ผลเปรียบเทียบคำตอบ Gemini บนชุดเดียวกันอยู่ใน GEMINI-EVALUATION-REPORT.md
- การเปิด query transform ผ่าน LLM ต้องเปิด USE_LLM ด้วย
- การค้นหาใกล้เคียงยังไม่ได้พิสูจน์การปฏิเสธคำถามนอกขอบเขต

## สิ่งที่แก้จากต้นฉบับ

- เพิ่ม requirements.txt และ PyThaiNLP สำหรับ BM25 ภาษาไทย
- ตั้งโหมด local แบบ extractive เป็นค่าเริ่มต้นและแสดง sources
- แก้กรณี NoLLM อ่าน prompt อังกฤษทั้งที่ prompt จริงเป็นไทย โดยคืน answer จาก chunk โดยตรง
- ระบุ answer_mode และแสดงการ fallback เมื่อเรียก LLM ไม่สำเร็จ
- ป้องกันการ normalize คำว่า ถุงยางอนามัย ให้กลายเป็น ถุงยางอนามัยอนามัย
- ป้องกันการเรียก query transform แบบ LLM ขณะปิด USE_LLM
- กำหนด PyThaiNLP data directory ให้อยู่ในพื้นที่งานเมื่อใช้ launcher แทนการเขียนลง home

## การรันซ้ำ

`python run_assignment.py` สร้าง index, golden set, ผล retrieval และผล extractive ใหม่ทั้งหมด
`python run_assignment.py --chat` เปิดถาม–ตอบแบบโต้ตอบ
ดู stdout/stderr ได้ใน evidence/*.txt และผลตัวเลขเต็มใน outputs/*.json

เอกสารนี้จัดเตรียมด้วยความช่วยเหลือของ AI ผู้เรียนควรตรวจและทดลองก่อนส่งตามเกณฑ์อาจารย์
"""
    (ROOT / "REPORT.md").write_text(report, encoding="utf-8")
    print("Saved REPORT.md and evidence/summary.json", flush=True)


if __name__ == "__main__":
    main()
