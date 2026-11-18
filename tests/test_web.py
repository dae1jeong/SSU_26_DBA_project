"""웹 연결 계층의 기능·요청 검증. 실제 데이터 파일을 사용하지 않는다."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from email.message import Message
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import db
from web_app import dispatch, Handler


class WebWorkflows(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = db.DB_PATH
        db.DB_PATH = str(Path(self.temp.name) / 'web.db')
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self.previous
        self.temp.cleanup()

    def test_web_full_workflow_and_updates(self):
        dispatch('student.save', dict(name='웹학생', school='중학교', grade='2', day_of_admission='2026-11-19', contact_number='', student_classification='ACTIVE'))
        sid = db.list_students()[-1]['student_id']
        dispatch('student.save', dict(student_id=sid, name='수정학생', school='', grade='3', day_of_admission='', contact_number='', student_classification='ACTIVE'))
        dispatch('teacher.save', dict(name='담당교사', contact_number=''))
        tid = db.list_teachers()[-1]['teacher_id']
        dispatch('teacher.save', dict(teacher_id=tid, name='수정교사', contact_number='010-0000-0000'))
        dispatch('course.save', dict(name='새과정', fee='10000'))
        coid = db.list_courses()[-1]['course_id']
        dispatch('course.save', dict(course_id=coid, name='무료과정', fee='0'))
        dispatch('class.save', dict(course_id=coid, teacher_id=tid, grade='3', class_name='특강', kind='short', start_date='2026-12-01', end_date='2026-12-31'))
        cid = db.list_classes()[-1]['class_id']
        dispatch('class.save', dict(class_id=cid, teacher_id='', grade='3', class_name='수정특강'))
        self.assertIsNone(db.list_classes()[-1]['teacher_id'])
        dispatch('timetable.save', dict(class_id=cid, schedule={'MON': ['18:00', '20:00']}))
        dispatch('enrollment.add', dict(student_id=sid, class_id=cid, enrolled_date='2026-11-19'))
        dispatch('payment.add', dict(student_id=sid, class_id=cid, payment_date='2026-11-19'))
        self.assertEqual(db.list_payments(sid)[0]['course_fee'], 0)
        eid = db.list_enrollments()[-1]['enrollment_id']
        dispatch('enrollment.status', dict(enrollment_id=eid, status='CANCELED'))
        with self.assertRaises(ValueError):
            dispatch('payment.add', dict(student_id=sid, class_id=cid))
        self.assertEqual(len(db.list_students_by_class(cid)), 1)
        self.assertEqual(db.list_timetable_by_class(cid)[0]['start_time'], '18:00')

    def request(self, method, path, body=None, origin=None, content_type='application/json'):
        h = Handler.__new__(Handler)
        h.path = path
        h.server = SimpleNamespace(server_port=8000)
        h.headers = Message()
        h.headers['Host'] = '127.0.0.1:8000'
        h.headers['Content-Type'] = content_type
        if origin:
            h.headers['Origin'] = origin
        raw = json.dumps(body).encode() if body is not None else b''
        h.headers['Content-Length'] = str(len(raw))
        h.rfile = io.BytesIO(raw)
        result = []
        h.send = lambda status, payload, *args: result.append((status, payload))
        getattr(h, 'do_' + method)()
        return result[0]

    def test_routes_errors_and_cross_origin(self):
        self.assertEqual(self.request('GET', '/api/state')[0], 200)
        status, payload = self.request('GET', '/api/payments?student_id=1&start_date=2026-03-02&end_date=2026-03-02')
        self.assertEqual((status, payload['total']), (200, 250000))
        self.assertEqual(self.request('GET', '/api/payments?start_date=bad')[0], 400)
        self.assertEqual(self.request('GET', '/api/student?id=1')[0], 200)
        self.assertEqual(self.request('GET', '/api/class?id=1')[0], 200)
        self.assertEqual(self.request('GET', '/academy.db')[0], 404)
        self.assertEqual(self.request('POST', '/api/course.save', {'name':'侵入', 'fee':0}, origin='https://other.example')[0], 403)
        self.assertEqual(self.request('POST', '/api/course.save', {}, content_type='text/plain')[0], 415)
        self.assertEqual(self.request('POST', '/api/course.save', {'name':'정상', 'fee':0})[0], 200)
        self.assertEqual(self.request('POST', '/api/not-allowed', {})[0], 400)


if __name__ == '__main__':
    unittest.main()
