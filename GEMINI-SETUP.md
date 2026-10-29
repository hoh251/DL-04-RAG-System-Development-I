# ใช้ Gemini สำหรับทุกส่วนที่เรียก LLM

ค่าเริ่มต้นเปลี่ยนเป็น Gemini แล้ว: การตอบคำถาม, rewrite, multi-query, HyDE และคำตอบที่อาศัย memory
เลือก `gemini-3.5-flash-lite` ซึ่งอยู่ในรุ่น stable ของเอกสาร Google ที่ตรวจวันที่ 28 ตุลาคม 2026
โปรแกรมจะตรวจรายชื่อโมเดลที่ key ของคุณเข้าถึงได้ก่อนเริ่ม ไม่เปลี่ยนไปใช้รุ่นอื่นเงียบ ๆ
หากบัญชีไม่รองรับชื่อนี้ ตั้ง RAG_GEMINI_MODEL เป็นรุ่นที่บัญชีเข้าถึงได้

## เริ่มใช้

1. เปิด `DL-04-RAG System Development I/RUN-AI.cmd`
2. หากเครื่องยังไม่มี GOOGLE_API_KEY หรือ GEMINI_API_KEY โปรแกรมจะถาม key แบบซ่อนตัวอักษร
3. วาง key ในหน้าต่างนั้นแล้วกด Enter ไม่ต้องส่ง key มาในแชท
4. โปรแกรมตรวจสิทธิ์โมเดล แล้วเปิดถาม–ตอบผ่าน Gemini

key ที่กรอกใช้เฉพาะ session นั้น ไม่บันทึกลงไฟล์หรือ User Environment และไม่แสดงค่าใน log
ถ้าคุณตั้ง GOOGLE_API_KEY หรือ GEMINI_API_KEY ไว้แล้ว โปรแกรมใช้ค่านั้นได้
หากมีทั้งสองชื่อ จะใช้ GOOGLE_API_KEY ก่อน
สร้าง/จัดการ key ได้ใน [Google AI Studio](https://aistudio.google.com/api-keys)

ใช้ `DL-04-RAG System Development I/TEST-ALL.cmd` เพื่อทดสอบ Gemini จริง: คำตอบพร้อมอ้างอิง, rewrite/multi-query/HyDE และ memory
ชุดทดสอบนี้ตรวจการเปิด RUN-AI.cmd และการทำงานร่วมกับ local cross-encoder reranker ด้วย
หากต้องการทดสอบใหม่ทั้งสามใบงานและ Gemini ในครั้งเดียว ให้เปิด TEST-ALL-ASSIGNMENTS.cmd ที่โฟลเดอร์รวม
สำหรับการประเมินคำตอบทั้งชุด ให้เปิด DL-04-RAG System Development I/RUN-EVALUATION.cmd: ใช้ 54 คำถามเดียวกันใน 3 วิธี รวม 162 trials
ผลนี้แยกจาก functional tests; ดู DL-04-RAG System Development I/GEMINI-EVALUATION-REPORT.md และ outputs/benchmark/
คำสั่งนี้มีการเรียก API จริงและใช้โควตาตามบัญชี ผลอยู่ใน `DL-04-RAG System Development I/evidence/gemini/`
กรณี key ไม่ถูกต้อง โมเดลเข้าไม่ได้ โควตาหมด หรืออินเทอร์เน็ตมีปัญหา โปรแกรมจะแจ้ง failure
ไม่มีการกลับไปเรียก Ollama หรือ OpenAI อัตโนมัติ

## ส่วนที่ใช้ในแต่ละงาน

| งาน/ส่วน | ตัวที่ใช้ |
|---|---|
| งาน 3: การทำ embeddings และค้นหา FAISS | Sentence Transformers + FAISS ตามโครงใบงาน |
| งาน 4: ตอบคำถามและแปลงคำถามทุกแบบ | Gemini API ใช้ key เดียว |
| งาน 4: memory | เก็บประวัติในเครื่อง ส่งบริบทเข้า Gemini เมื่อตอบ/แปลงคำถาม |
| งาน 4: reranking | BAAI cross-encoder ในเครื่องตามต้นฉบับ |
| งาน 5: simulation 1–9 | Python ไม่มี LLM call |

ตอนนี้ย้ายทุก LLM call ไป Gemini ส่วน embedding/reranking ยังคงโครงรายวิชาไว้
งาน 3 และ 5 ไม่ได้มี Ollama call จึงไม่มีการเพิ่มการเรียก API โดยไม่จำเป็น

## สถานะการทดสอบ

ดู FULL-TEST-REPORT.md สำหรับสถานะ Gemini ล่าสุด
ผล Ollama ที่ทดสอบผ่านก่อนหน้านี้เก็บแยกใน LOCAL-TEST-REPORT.md และ evidence/full/
ผลเก่าเหล่านั้นไม่ใช่หลักฐานว่า Gemini API ผ่านแล้ว

## แหล่งข้อมูลทางการ

- [Gemini models](https://ai.google.dev/gemini-api/docs/models)
- [Model lifecycle](https://ai.google.dev/gemini-api/docs/deprecations)
- [OpenAI-compatible Gemini endpoint](https://ai.google.dev/gemini-api/docs/openai)
- [Gemini API key setup](https://ai.google.dev/gemini-api/docs/api-key)

ชื่อแพ็กเกจ openai เป็น client ที่ส่งคำขอไป endpoint ของ Google ไม่ได้แปลว่าใช้ OpenAI API หรือจำเป็นต้องมี OPENAI_API_KEY
