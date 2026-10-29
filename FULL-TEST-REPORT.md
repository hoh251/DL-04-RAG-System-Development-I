# DL-04: ผลทดสอบ Gemini

อัปเดตรายงาน UTC 2026-10-29T14:16:52.569345+00:00
Unit tests: ผ่าน
Gemini functional live tests ที่บันทึกไว้: passed
Gemini benchmark: 162/162 คำตอบ; รันครบ: True

หลักฐานเรียก API จริงอยู่ใน `evidence/gemini/` และ `outputs/benchmark/trials.jsonl`
เวลา live tests และ manifest เป็นเวลาที่รันจริงเดิม การสร้างรายงานนี้รัน unit tests ใหม่และอ่านหลักฐานเดิม ไม่ได้เรียก API เพิ่ม
อ่าน [GEMINI-EVALUATION-REPORT.md](GEMINI-EVALUATION-REPORT.md) สำหรับการออกแบบการทดลองและผลสามวิธี
คะแนน token overlap เป็น proxy ไม่ใช่การยืนยันข้อเท็จจริงของคำตอบทุกข้อ

ทดสอบซ้ำด้วย TEST-ALL.cmd; ถาม–ตอบด้วย RUN-AI.cmd; ประเมินทั้งชุดด้วย RUN-EVALUATION.cmd
กรอก API key แบบซ่อนตัวอักษร ใช้เฉพาะ session ไม่บันทึกใน repository
