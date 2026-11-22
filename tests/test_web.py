"""웹 연결 계층의 기능·요청 검증. 별도 MySQL 스키마를 사용한다."""
import io
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from email.message import Message
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import db
from web_app import dispatch, Handler


from mysql_fixture import MySQLTestCase


class WebWorkflows(MySQLTestCase):
    def test_web_full_workflow_and_updates(self):
        dispatch('student.save', dict(name='웹학생', school='중학교', grade='중2', day_of_admission='2026-11-19', contact_number='01012345678', student_classification='ACTIVE'))
        self.assertEqual(db.list_students()[-1]['contact_number'], '010-1234-5678')
        sid = db.list_students()[-1]['student_id']
        dispatch('student.save', dict(student_id=sid, name='수정학생', school='', grade='중3', day_of_admission='', contact_number='', student_classification='ACTIVE'))
        dispatch('teacher.save', dict(name='담당교사', contact_number=''))
        tid = db.list_teachers()[-1]['teacher_id']
        dispatch('teacher.save', dict(teacher_id=tid, name='수정교사', contact_number='010-0000-0000'))
        dispatch('course.save', dict(name='새과정', fee='10000'))
        coid = db.list_courses()[-1]['course_id']
        dispatch('course.save', dict(course_id=coid, name='무료과정', fee='0'))
        dispatch('class.save', dict(course_id=coid, teacher_id=tid, grade='중3', class_name='검증반'))
        cid = db.list_classes()[-1]['class_id']
        dispatch('class.save', dict(class_id=cid, teacher_id='', grade='중3', class_name='수정특강'))
        self.assertIsNone(db.list_classes()[-1]['teacher_id'])
        dispatch('timetable.save', dict(class_id=cid, schedule={'MON': ['18:00', '20:00']}))
        dispatch('enrollment.add', dict(student_id=sid, class_id=cid, enrolled_date='2026-11-19'))
        dispatch('payment.add', dict(student_id=sid, class_id=cid, payment_date='2026-11-19', billing_month='2026-11'))
        self.assertEqual(db.list_payments(sid)[0]['course_fee'], 0)
        dispatch('payment.add', dict(student_id=sid, class_id=cid, status='UNPAID', billing_month='2026-12'))
        unpaid = next(row for row in db.list_payments(sid) if row['status'] == 'UNPAID')
        body = dict(payment_id=unpaid['payment_id'], status='PAID', payment_date='2026-11-20')
        self.assertEqual(self.request('POST', '/api/payment.status', body)[0], 200)
        body["status"] = "REFUNDED"
        self.assertEqual(self.request('POST', '/api/payment.status', body)[0], 200)
        self.assertEqual(db.list_payments(sid)[0]['status'], 'REFUNDED')
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

    def test_monthly_payment_targets_and_duplicate_issuance(self):
        status, targets = self.request('GET', '/api/payment-targets?billing_month=2026-11')
        self.assertEqual(status, 200)
        self.assertIn((1, 1), {(row['student_id'], row['class_id']) for row in targets})
        self.assertNotIn(5, {row['class_id'] for row in targets})  # 특강은 12월 시작
        db.update_student_classification(2, 'BLACK')
        db.update_enrollment_status(3, 'CANCELED')
        _, targets = self.request('GET', '/api/payment-targets?billing_month=2026-11')
        self.assertNotIn((2, 2), {(row['student_id'], row['class_id']) for row in targets})
        self.assertNotIn((3, 3), {(row['student_id'], row['class_id']) for row in targets})

        request = dict(student_id=1, class_id=1, billing_month='2026-11', status='UNPAID')
        self.assertEqual(self.request('POST', '/api/payment.add', request)[0], 200)
        self.assertEqual(self.request('POST', '/api/payment.add', request)[0], 400)
        self.assertEqual(self.request('GET', '/api/payment-targets?billing_month=2026-13')[0], 400)
        _, targets = self.request('GET', '/api/payment-targets?billing_month=2026-11&student_id=1')
        self.assertEqual([(row['class_id'], row['status']) for row in targets], [(1, 'UNPAID')])
        _, payload = self.request('GET', '/api/payments?billing_month=2026-11')
        self.assertEqual(len(payload['rows']), 1)
        self.assertEqual(payload['total'], 0)
        payment_id = payload['rows'][0]['payment_id']
        self.assertEqual(self.request('POST', '/api/payment.status', dict(
            payment_id=payment_id, status='PAID', payment_date='2026-12-03'))[0], 200)
        _, payload = self.request('GET', '/api/payments?billing_month=2026-11&start_date=2026-12-01')
        self.assertEqual(payload['total'], 250000)
        self.assertEqual(payload['rows'][0]['payment_date'], '2026-12-03')
        self.assertEqual(payload['rows'][0]['billing_month'], '2026-11-01')

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
