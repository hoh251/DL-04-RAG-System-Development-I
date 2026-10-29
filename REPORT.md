# ใบงาน 4: Mod RAG — บันทึกผลการทดลองจริง

แหล่งโค้ด: aproot-en/Advanced-Topic-in-Computer-Software-Course, commit c0db2ac
รันเมื่อ (UTC): 2026-10-29T14:19:10.997405+00:00

รายงานนี้เป็นการทดลองพื้นฐานแบบ extractive เท่านั้น ผลทดสอบเพิ่มเติมของ LLM จริง,
query transformation และ reranking อยู่ใน ../FULL-TEST-REPORT.md และ evidence/full/live_checks.json

## การพัฒนาและการตั้งค่า

ใช้ฐานข้อมูล Q&A เดิม สร้าง embedding และ FAISS ใหม่ พร้อม BM25 index ที่ตัดคำด้วย PyThaiNLP
ระบบแยกเป็น loader, chunker, embedding, vector store, hybrid retriever, query transform,
generator และ conversation memory ปรับการทำงานได้ใน config.py

ทดสอบ dense-only, BM25-only และ hybrid ที่รวมอันดับด้วย RRF บน golden set ชุดเดียวกัน
จำนวน 54 รายการ พร้อม variants ที่มีอยู่ในแต่ละข้อ
ตั้ง USE_LLM=False จึงคืนข้อความจาก chunk แรกพร้อม [1] และแสดงแหล่งข้อมูล
ไม่มีการเรียก API ที่เสียเงิน

## ผลการเปรียบเทียบ retrieval

| วิธีค้นหา | Hit@1 | Hit@10 | MRR | nDCG@3 | ms/query |
|---|---:|---:|---:|---:|---:|
| dense_only | 0.7929 | 0.9286 | 0.8445 | 0.7538 | 39.3 |
| bm25_only | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 10.8 |
| hybrid | 0.8643 | 1.0000 | 0.9219 | 0.8493 | 41.0 |

วิธีที่มี MRR สูงสุดในชุดทดลองนี้คือ `bm25_only` ตัวเลขนี้เป็นผลจริง ไม่ได้กำหนดให้ hybrid ต้องดีที่สุด
Hit@k คือสัดส่วนคำถามที่มี chunk เป้าหมายใน k อันดับแรก ส่วน MRR ให้ความสำคัญกับอันดับแรกที่ถูกต้อง
nDCG@3 คำนึงถึงอันดับของเอกสารที่เกี่ยวข้องในสามอันดับแรก

## การทดสอบคำตอบและ memory

ทดสอบตัวอย่าง 3 คำถามว่ามีคำตอบแบบ extractive พร้อมแหล่งอ้างอิง และไม่ปฏิเสธเพราะ parser ผิด
ทดสอบเพิ่มและล้างประวัติสำเร็จ ผลเต็มอยู่ใน evidence/sample_answers.json
ประวัติถูกจัดเก็บจริง แต่ยังไม่ได้ประเมินการเข้าใจคำถามต่อเนื่องด้วย LLM
ผล outputs/eval_generation.json เป็นการวัดคำซ้ำของข้อความที่ดึงมาเท่านั้น
ไม่ใช่หลักฐานคุณภาพการสร้างคำตอบด้วย LLM หรือคะแนนตรวจสอบข้อเท็จจริง

## ข้อจำกัดและส่วนที่ยังต้องทดลอง

- Golden set สร้างอัตโนมัติจากฐานข้อมูลเดียวกับ index จึงเป็นการทดสอบ retrieval ภายในชุดข้อมูล
  ไม่ใช่ผลทดสอบกับคำถามอิสระที่มนุษย์ตรวจแล้ว และไม่ควรอ้างว่าสะท้อนการใช้งานจริงทั้งหมด
- การแปลงคำถามใน golden set บางกรณีเปลี่ยนความหมาย จึงต้องตรวจคู่คำถามด้วยคนก่อนอ้างผลเชิงวิจัย
- รายงาน baseline นี้ไม่รวมผล LLM; ผล functional tests ของ cross-encoder และ Gemini อยู่ใน ../FULL-TEST-REPORT.md
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
