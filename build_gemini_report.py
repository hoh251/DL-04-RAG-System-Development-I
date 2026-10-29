"""Build a report for this independent DL-04 repository without sibling labs."""
from pathlib import Path
from datetime import datetime, timezone
import json
import subprocess
import sys

root = Path(__file__).resolve().parent
evidence = root / 'evidence/gemini'
evidence.mkdir(parents=True, exist_ok=True)
tests = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=root,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
(evidence / 'unit_tests.txt').write_text(tests.stdout + tests.stderr, encoding='utf-8')
def read(path):
    file = root / path
    return json.loads(file.read_text(encoding='utf-8')) if file.exists() else {}
live = read('evidence/gemini/live_checks.json')
benchmark = read('outputs/benchmark/summary.json')
result = {'updated_at_utc': datetime.now(timezone.utc).isoformat(), 'unit_tests_passed': tests.returncode == 0,
          'gemini_live_status': live.get('status', 'not_run'), 'cloud_inference_tested': live.get('cloud_inference_tested', False),
          'benchmark': {k: benchmark.get(k) for k in ['n_items', 'expected_trials', 'successful_answers', 'all_complete']},
          'key_value_saved': False}
(root / 'gemini-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
(root / 'FULL-TEST-REPORT.md').write_text(f'''# DL-04: ผลทดสอบ Gemini

อัปเดตรายงาน UTC {result['updated_at_utc']}
Unit tests: {'ผ่าน' if tests.returncode == 0 else 'มีข้อผิดพลาด ดู evidence/gemini/unit_tests.txt'}
Gemini functional live tests ที่บันทึกไว้: {result['gemini_live_status']}
Gemini benchmark: {benchmark.get('successful_answers', 0)}/{benchmark.get('expected_trials', 0)} คำตอบ; รันครบ: {benchmark.get('all_complete', False)}

หลักฐานเรียก API จริงอยู่ใน `evidence/gemini/` และ `outputs/benchmark/trials.jsonl`
เวลา live tests และ manifest เป็นเวลาที่รันจริงเดิม การสร้างรายงานนี้รัน unit tests ใหม่และอ่านหลักฐานเดิม ไม่ได้เรียก API เพิ่ม
อ่าน [GEMINI-EVALUATION-REPORT.md](GEMINI-EVALUATION-REPORT.md) สำหรับการออกแบบการทดลองและผลสามวิธี
คะแนน token overlap เป็น proxy ไม่ใช่การยืนยันข้อเท็จจริงของคำตอบทุกข้อ

ทดสอบซ้ำด้วย TEST-ALL.cmd; ถาม–ตอบด้วย RUN-AI.cmd; ประเมินทั้งชุดด้วย RUN-EVALUATION.cmd
กรอก API key แบบซ่อนตัวอักษร ใช้เฉพาะ session ไม่บันทึกใน repository
''', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(tests.returncode)
