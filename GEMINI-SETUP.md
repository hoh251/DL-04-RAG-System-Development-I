# ตั้งค่า Gemini

1. เปิด `SETUP.cmd` เพื่อติดตั้ง dependencies แล้วเปิด `RUN.cmd` เพื่อสร้าง index
2. เปิด `RUN-AI.cmd` แล้วกรอก Gemini API key ในช่องที่ซ่อนตัวอักษร
3. โปรแกรมตรวจสิทธิ์เข้าถึงโมเดลก่อนเริ่มถาม–ตอบ

รองรับ `GOOGLE_API_KEY` หรือ `GEMINI_API_KEY` จาก environment หากมีทั้งสองจะใช้ `GOOGLE_API_KEY` ก่อน
key ที่กรอกใช้เฉพาะ session ไม่บันทึกลงไฟล์หรือ User Environment
สร้าง key ได้ที่ [Google AI Studio](https://aistudio.google.com/api-keys)

ค่าเริ่มต้นคือ `gemini-3.5-flash-lite` เปลี่ยนได้ด้วย `RAG_GEMINI_MODEL`
โปรแกรมตรวจรายชื่อโมเดลที่ key เข้าถึงได้ หากไม่รองรับหรือโควตาหมดจะแจ้งข้อผิดพลาด ไม่เปลี่ยน provider อัตโนมัติ

การตอบ การแปลงคำถาม และการใช้บริบทจาก memory เรียก Gemini API ส่วน embedding, FAISS และ reranker ทำงานในเครื่อง
คำถาม ประวัติที่ใช้เป็นบริบท และข้อความที่ค้นคืนได้จะส่งไปยัง Gemini และใช้โควตาของบัญชี
แพ็กเกจ `openai` เป็น client สำหรับ endpoint ที่เข้ากันได้ของ Google ไม่ต้องมี `OPENAI_API_KEY`

`RUN-EVALUATION.cmd` ใช้คำถาม 54 ข้อเปรียบเทียบ 3 วิธี รวม 162 คำตอบ มี checkpoint เพื่อทำต่อด้วย `--resume`
ผลอยู่ใน `outputs/benchmark/` และรายงานที่สร้างขึ้นในเครื่อง ไฟล์ผลลัพธ์ไม่ถูกติดตามใน Git
คะแนน token overlap เป็นเพียง proxy ไม่ใช่การยืนยันข้อเท็จจริงทุกคำตอบ
