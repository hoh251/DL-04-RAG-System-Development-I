# ผลตรวจงาน Local และ AI ฉบับล่าสุด

ตรวจเสร็จเวลาไทย: 2026-10-28T16:31:34.788124+07:00

## ผลที่ยืนยันได้

- งาน 3 รัน Lab 01–07 สร้างเวกเตอร์ 541 × 384 และเปิดถาม–ตอบได้
- งาน 4 รัน baseline ใหม่หลังแก้โค้ด และทดสอบ LLM Local จริง รวม query transformation และ reranking
- งาน 5 รัน simulation 1–9 และเมนูโต้ตอบได้
- ชุดตรวจ configuration และ error paths ผ่าน 18 tests
- ชุดตรวจ component จริงผ่าน 14 checks ตามตารางด้านล่าง
- ไฟล์เปิดใช้งาน RUN-AI.cmd: เปิดจริง ถาม–ตอบด้วย LLM พร้อม sources และตรวจ CPU จาก Ollama API ผ่านแล้ว

## ผลทดสอบ component จริงของงาน 4

| การทดสอบจริง | สถานะ | วินาที |
|---|---|---:|
| ollama_models | ผ่าน | 0.048 |
| real_llm_request | ผ่าน | 5.483 |
| real_missing_model_error | ผ่าน | 0.024 |
| real_unavailable_server_error | ผ่าน | 2.011 |
| grounded_llm_generation_and_citations | ผ่าน | 64.908 |
| out_of_scope_llm_refusal | ผ่าน | 13.722 |
| query_transform_rewrite | ผ่าน | 4.405 |
| query_transform_multi_query | ผ่าน | 9.500 |
| query_transform_hyde | ผ่าน | 56.589 |
| real_multi_turn_memory_and_rewrite | ผ่าน | 91.877 |
| empty_context_refusal | ผ่าน | 0.000 |
| actual_cross_encoder_reranking | ผ่าน | 7.291 |
| realistic_query_quality_comparison | ผ่าน | 27.471 |
| combined_rewrite_hybrid_rerank_llm_memory | ผ่าน | 34.286 |

การทดสอบคำตอบตรวจว่าเรียกโมเดลจริง (`answer_mode=llm`), ได้คำตอบไม่ว่าง,
มีเลขอ้างอิงที่ตรงกับ source ที่ส่งเข้าโมเดล และไม่มีการ fallback เป็น extractive แล้วนับว่าผ่าน
ตรวจ rewrite/multi-query/HyDE ว่ามีผลจริงและนำไปค้นเอกสารได้
ตรวจบทสนทนาสองรอบว่ามีประวัติและ rewrite คำถามต่อเนื่องโดยมีหัวข้อก่อนหน้า
reranking ใช้ BAAI/bge-reranker-v2-m3 จริง ไม่ใช่การให้คะแนนด้วยกฎจำลองของงาน 5
HyDE สร้างข้อความสมมติเพื่อใช้ค้นหาเท่านั้น ข้อความนั้นอาจผิดและไม่ได้ใช้เป็นคำตอบอ้างอิงของผู้ใช้

## คุณภาพ retrieval บนคำถามเขียนใหม่ 8 ข้อ

| วิธี | Hit@1 | Hit@3 |
|---|---:|---:|
| dense | 0.375 | 0.500 |
| hybrid | 0.500 | 0.750 |
| hybrid_rerank | 0.750 | 0.875 |

คำถามและ labels ชุดนี้จัดทำด้วย AI เพื่อทดสอบเพิ่มเติม ไม่ใช่ benchmark อิสระที่มนุษย์รับรอง
ผลเต็มพร้อมคำถาม คำตอบเป้าหมาย และสามอันดับแรก อยู่ใน evidence/full/live_checks.json
การผ่านการรันไม่ใช่การรับรองว่าตอบถูกทุกคำถาม หรือข้อมูลสุขภาพทุกข้อถูกต้อง

ข้อที่ hybrid+rerank ยังไม่พบเป้าหมายใน Top-3:

- ถ้าเขาเงียบเฉยไม่ได้ขัดขืน แปลว่าตกลงไหม → อันดับแรก: เขาไม่ได้ห้าม แปลว่ายอมใช่ไหม

เมื่อตรวจข้อมูลของข้อที่พลาด พบว่า label เลือกเฉพาะ chunk 52 (ภาษาทางการ)
แต่ระบบคืน chunk 372/506 ซึ่งเป็นคำถามเดียวกันในภาษากันเองและมีคำตอบใจความเดียวกัน
จึงมีข้อจำกัดของ labels ที่ไม่ครอบคลุมคำตอบเทียบเท่า ตัวเลขด้านบนยังคงค่าที่วัดเดิมไว้
ไม่ได้ปรับคะแนนให้สูงขึ้นหลังเห็นผล และไม่ควรตีความว่า 7/8 แปลว่าคำตอบผิด 1 ข้อแน่นอน

## ปัญหาที่พบและสิ่งที่แก้

- ค่า Gemini 1.5 ในต้นฉบับปิดบริการแล้ว: ป้องกันชื่อรุ่นเก่าและยกเลิก cloud model default
- GPT-4o mini รุ่นเดิมมีประกาศเลิกบริการในอนาคต: ให้เลือก cloud model เองและแสดงคำเตือนรุ่นเก่า
- placeholder key ของ Ollama เดิมมีภาษาไทยซึ่งไม่เหมาะกับ HTTP header: เปลี่ยนเป็น ASCII `ollama`
- ถ้าเปิด LLM แต่ key ขาด/model หาย/server ล่ม/คำตอบว่าง จะรายงาน failure ชัดเจน
- ป้องกัน NoLLM ทำหน้าที่เสมือน LLM; query transformation ที่ล้มเหลวจะไม่เงียบแล้วนับว่าผ่าน
- ทดสอบ HTTP 404 จากชื่อโมเดลที่ไม่มีจริง และ connection error จาก port ที่ไม่มี server จริง
- แก้การ normalize ซ้ำ และไม่แทนคำ AIDS ด้วย HIV เพราะไม่ใช่คำเดียวกัน
- ต้นฉบับงาน 5 import Problem 10 ที่ไม่มีไฟล์: แก้เมนูให้ตรงกับ 9 ข้อที่มีจริง

## Runtime ที่เลือกให้เครื่องนี้

Ollama portable 0.40.12, qwen2.5:3b, context 4096, localhost เท่านั้น และปิด cloud features
ใช้ CPU ทั้ง LLM และ reranker หลังพบ CUDA request timeout ในการทดสอบครั้งแรก
ยังไม่ได้ยืนยันสาเหตุเฉพาะหรือเสถียรภาพเส้นทาง GPU จึงไม่อ้างว่า GPU ผ่าน
เก็บ attempt ที่ timeout ไว้ใน evidence/full/cuda_timeout_attempt.json
โหมด CPU ใช้เวลามากกว่า GPU; ดูเวลาราย check ในตาราง ไม่ได้เรียก hosted inference เพื่อทำให้ผลเร็วขึ้น

## API key และขอบเขตการยืนยัน

ทั้งสามงานในโหมด Local ที่ทดสอบไม่ต้องมี API key
หากเปลี่ยนไปใช้ OpenAI ต้องตั้ง OPENAI_API_KEY; ถ้าเลือก Gemini ต้องตั้ง GOOGLE_API_KEY
ตั้งเฉพาะ key ของ provider ที่เลือก ไม่ต้องมีทั้งสอง key และไม่ต้องใส่ key ในโค้ด
การเรียก OpenAI/Gemini cloud จริงยังไม่ได้ทดสอบ เพราะไม่มี key ที่ผู้ใช้ให้ใช้กับงานนี้
unit tests ตรวจรูปแบบ request และ key-missing โดย mock เท่านั้น ไม่ได้นับเป็น cloud inference ที่สำเร็จ
ดู AI-SETUP.md สำหรับแหล่งข้อมูลทางการ สถานะรุ่น และคำสั่งใช้งาน

## ไฟล์เริ่มใช้งาน

- `DL-04-RAG System Development I/RUN-AI.cmd`: เริ่ม Local LLM และถาม–ตอบ
- `DL-04-RAG System Development I/TEST-ALL.cmd`: รันทดสอบ configuration และ live components ใหม่
- `DL-03-LLM Retrieval System/RUN.cmd`, `DL-04-RAG System Development I/RUN.cmd`, `DL-05-RAG System Development II/RUN.cmd`: ทดลองพื้นฐานแต่ละงาน
- `verification.json`: ผลตรวจเปิดใช้งานพื้นฐาน
- `DL-04-RAG System Development I/evidence/full/live_checks.json`: หลักฐาน component จริงและผลคุณภาพ
- `DL-04-RAG System Development I/evidence/full/unit_tests.txt`: ผล unit tests ล่าสุด

การจับคู่ใบงาน 3–5 กับ DL-03/04/05 อ้างอิงหัวข้อคะแนนและเนื้อหา GitHub
ยังไม่มี rubric/รูปแบบส่งเฉพาะจากอาจารย์ให้ตรวจ จึงไม่รับรองว่าเอกสารนี้ตรงเกณฑ์ส่งทั้งหมด
ผู้เรียนควรอ่านผล ทดลองด้วยตนเอง และอธิบายโค้ดก่อนนำไปส่ง
