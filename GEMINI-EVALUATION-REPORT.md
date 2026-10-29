# งาน 4: เปรียบเทียบ retrieval และคำตอบ Gemini บนคำถามชุดเดียวกัน

สถานะ: รันครบ
คำถาม 54 ข้อ × 3 วิธี = 162 trials
บันทึกแล้ว 162 trials; Gemini ตอบจริงสำเร็จ 162 รายการ
เริ่มเมื่อ UTC 2026-10-28T11:42:35.225152+00:00; model = gemini-3.5-flash-lite

## การออกแบบการทดลอง

ตรึง data/golden_set.json เดิมเป็น golden_set_frozen.json และบันทึก SHA-256
ใช้ variant natural ของคำถามทุกข้อ ไม่เลือกเฉพาะข้อที่ผลดี
ทั้งสามวิธีใช้ corpus/index เดียวกัน embedding model เดียวกัน และส่ง Top-3 ให้ Gemini ด้วย prompt เดียวกัน
ค้น candidates 20 รายการ และเก็บ Top-10 สำหรับ metrics; Hybrid รวม BM25 + dense ด้วย RRF
hybrid_rerank เพิ่ม BAAI/bge-reranker-v2-m3 บน CPU โดยไม่เปลี่ยน LLM หรือคำถาม
ปิด memory และ LLM query transformation ใน benchmark เพื่อแยกผลของวิธีค้นหา
ส่วน rewrite/multi-query/HyDE และ memory มี functional live tests แยกใน evidence/gemini/

## ผล retrieval

| วิธี | คำถาม | Hit@1 | Hit@3 | Hit@10 | MRR | nDCG@3 | ค้นหาเฉลี่ย (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| dense_only | 54 | 0.8333 | 0.8889 | 0.9444 | 0.8684 | 0.7585 | 0.059 |
| hybrid | 54 | 0.8889 | 1.0000 | 1.0000 | 0.9383 | 0.8580 | 0.048 |
| hybrid_rerank | 54 | 0.9815 | 1.0000 | 1.0000 | 0.9907 | 0.8929 | 11.712 |

วิธีที่มี MRR สูงสุดในการทดลองนี้คือ hybrid_rerank ผลนี้อิงเฉลยแบบ chunk ID ของชุดนี้ ไม่ใช่การยืนยันว่าเหนือกว่าทุกประเภทคำถาม

## ผลคำตอบ Gemini จริง

| วิธี | Gemini ตอบสำเร็จ | citation valid | context token overlap | reference token precision | reference token recall | Gemini เฉลี่ย (s) |
|---|---:|---:|---:|---:|---:|---:|
| dense_only | 54 | 0.9630 | 0.7681 | 0.6237 | 0.7176 | 1.296 |
| hybrid | 54 | 1.0000 | 0.7908 | 0.6488 | 0.7900 | 1.286 |
| hybrid_rerank | 54 | 1.0000 | 0.7842 | 0.6258 | 0.7541 | 1.542 |

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
