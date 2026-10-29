# ใบงาน 4: Mod RAG

อ่าน REPORT.md เพื่อดูผลเปรียบเทียบและข้อจำกัด
ผลตัวเลขอยู่ใน outputs/eval_retrieval.json และ log อยู่ใน evidence/

ดับเบิลคลิก RUN.cmd เพื่อสร้าง index และประเมินใหม่
ใช้ `RUN.cmd -Chat` เพื่อถาม–ตอบ; โหมดเริ่มต้นเป็น extractive พร้อม sources
ถ้าใช้ Python ที่ติดตั้ง dependencies แล้ว ให้รัน `python run_assignment.py`
หรือ `python run_assignment.py --chat`

## เปิดใช้ Gemini API

ดับเบิลคลิก RUN-AI.cmd แล้วกรอก Gemini key แบบซ่อนตัวอักษรเพื่อเริ่มถาม–ตอบ
ค่า provider เริ่มต้นคือ gemini และโมเดล gemini-3.5-flash-lite
อ่าน GEMINI-SETUP.md สำหรับวิธีตั้ง GOOGLE_API_KEY หรือ GEMINI_API_KEY
ใช้ TEST-ALL.cmd เพื่อทดสอบ Gemini จริง; ผลอยู่ใน evidence/gemini/
ผลตรวจปัจจุบันรวมอยู่ใน FULL-TEST-REPORT.md; REPORT.md เป็นผลพื้นฐานแบบ extractive
ผล Ollama เดิมอยู่ใน LOCAL-TEST-REPORT.md เป็นหลักฐานของ runtime เดิมเท่านั้น

## ประเมินคำตอบทั้งชุด

เปิด RUN-EVALUATION.cmd เพื่อเปรียบเทียบ Dense, Hybrid และ Hybrid + cross-encoder บนคำถาม Golden set เดียวกันทุกข้อ
มีการเรียก Gemini จริงทุกวิธีและใช้โควตา API; ผลคำตอบรายข้ออยู่ใน outputs/benchmark/trials.jsonl
ดู GEMINI-EVALUATION-REPORT.md สำหรับตารางผลและข้อจำกัดของคะแนน token overlap
ระบบบันทึก checkpoint และใช้ --resume เพื่อทำต่อโดยไม่เรียก API ซ้ำสำหรับรายการที่สำเร็จแล้ว
เปิด USE_QUERY_TRANSFORM=True เพื่อทดลอง rewrite, multi_query หรือ hyde
โดยเลือก QUERY_TRANSFORM_MODE ให้ตรงที่ต้องการ
เปิด USE_RERANK=True เพื่อใช้ cross-encoder; ต้องดาวน์โหลด model เพิ่มและใช้ทรัพยากรสูงกว่าเดิม
เมื่อทดสอบแล้วให้บันทึกผลเพิ่มแยกจากผล extractive ที่เตรียมไว้

source และ dataset ตั้งต้นมาจาก DL-04-RAG System Development I/04-RAG-Project
ของ repository aproot-en/Advanced-Topic-in-Computer-Software-Course ที่ commit c0db2ac
รายการแก้ไขสำเนา local อยู่ใน REPORT.md; ดู README.md สำหรับการติดตั้งใหม่
