"""별도 MySQL 스키마에서 실행하는 기능 통합 검사."""
import unittest
from unittest.mock import patch
from datetime import date, timedelta
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import db


from mysql_fixture import MySQLTestCase


class Workflows(MySQLTestCase):
    def test_student_edit_preserves_relations_and_validates(self):
        db.update_student(1, '수정학생', '새학교', '고3', '2026-11-19', '', 'INACTIVE')
        row = db.list_students()[0]
        self.assertEqual((row['name'], row['grade'], row['contact_number']), ('수정학생', '고3', None))
        self.assertEqual(len(db.list_enrollments_by_student(1)), 1)
        self.assertEqual(len(db.list_payments(1)), 1)
        for grade, admission in (('-1', ''), ('중2', '2026-02-30'), ('abc', '')):
            with self.assertRaises(ValueError):
                db.update_student(1, '학생', '', grade, admission, '', 'ACTIVE')
        self.assertEqual(db.list_students()[0]['name'], '수정학생')

    def test_status_payment_and_reactivation(self):
        db.update_enrollment_status(1, 'COMPLETED')
        self.assertEqual(len(db.list_active_classes_by_student(1)), 0)
        with self.assertRaises(ValueError):
            db.add_class_payment(1, 1, '', billing_month='2026-11')
        self.assertEqual(len(db.list_payments(1)), 1)
        db.update_enrollment_status(1, 'ACTIVE')
        db.add_class_payment(1, 1, '', billing_month='2026-11')
        self.assertEqual(db.list_payments(1)[0]['payment_date'], date.today().isoformat())
        db.update_student_classification(1, 'BLACK')
        db.update_enrollment_status(1, 'CANCELED')
        with self.assertRaises(ValueError):
            db.update_enrollment_status(1, 'ACTIVE')
        with self.assertRaises(ValueError):
            db.add_class_payment(1, 1, '', billing_month='2026-11')
        with self.assertRaises(ValueError):
            db.update_enrollment_status(999, 'ACTIVE')

    def test_payment_filters_boundaries_totals_snapshot(self):
        self.assertEqual(db.total_revenue(), 1400000)
        self.assertEqual(db.total_revenue(1, '2026-03-02', '2026-03-02'), 250000)
        self.assertEqual(len(db.list_payments(None, '2026-03-02', '2026-03-05')), 2)
        self.assertEqual(db.total_revenue(None, '2027-01-01', None), 0)
        for start, end in (('2026-12-01', '2026-01-01'), ('bad', None), ('2026-02-30', None)):
            with self.assertRaises(ValueError):
                db.list_payments(None, start, end)
        db.update_course(1, '무료과정', 0)
        db.add_class_payment(1, 1, '2026-11-19', billing_month='2026-11')
        payments = db.list_payments(1)
        self.assertEqual(payments[0]['course_fee'], 0)
        self.assertEqual(payments[1]['course_fee'], 250000)
        self.assertEqual(payments[1]['course_name'], '중등 수학 정규반')

        db.update_course(1, '다음 과정', 10000)
        db.add_class_payment(1, 1, '', 'UNPAID', '2026-12')
        unpaid = next(row for row in db.list_payments(1) if row['status'] == 'UNPAID')
        self.assertIsNone(unpaid['payment_date'])
        self.assertEqual(unpaid['billing_month'], '2026-12-01')
        self.assertEqual(len(db.list_payments(1, billing_month='2026-12')), 1)
        with self.assertRaisesRegex(ValueError, '이미 등록'):
            db.add_class_payment(1, 1, '', 'UNPAID', '2026-12-01')
        self.assertEqual(db.total_revenue(1), 250000)
        db.update_payment_status(unpaid['payment_id'], 'PAID', '2026-11-30')
        self.assertEqual(db.total_revenue(1), 260000)
        db.update_payment_status(unpaid['payment_id'], 'REFUNDED')
        refunded = db.list_payments(1)[0]
        self.assertEqual((refunded['status'], refunded['payment_date'], refunded['course_fee']),
                         ('REFUNDED', '2026-11-30', 10000))
        self.assertEqual(db.total_revenue(1), 250000)
        with self.assertRaises(ValueError):
            db.update_payment_status(unpaid['payment_id'], 'PAID')

    def test_duplicate_dates_timetable_and_short_course(self):
        with self.assertRaisesRegex(ValueError, '이미 등록'):
            db.add_enrollment(1, 1, '')
        with self.assertRaises(ValueError):
            db.add_enrollment(2, 1, '2026-13-01')
        db.add_enrollment(2, 1, '')
        self.assertEqual(db.list_enrollments()[-1]['enrolled_date'], date.today().isoformat())
        original = db.list_timetable_by_class(1)
        with self.assertRaises(ValueError):
            db.save_timetable_by_class(1, {'MON': ('20:00', '19:00')})
        self.assertEqual(db.list_timetable_by_class(1), original)
        before = len(db.list_classes())
        with self.assertRaises(ValueError):
            db.add_short_course(1, None, '중2', '특강', '2026-12-31', '2026-12-01')
        self.assertEqual(len(db.list_classes()), before)
        today = date.today()
        db.add_short_course(1, None, '중2', '종료 경계 특강', today.isoformat(), today.isoformat())
        class_id = db.list_classes()[-1]['class_id']
        db.add_enrollment(1, class_id, '')
        db.add_enrollment(2, class_id, '', 'CANCELED')
        self.assertEqual({r['student_id']: r['status'] for r in db.list_students_by_class(class_id)},
                         {1: 'ACTIVE', 2: 'CANCELED'})
        with patch('db.date', wraps=date) as clock:
            clock.today.return_value = today + timedelta(days=1)
            self.assertEqual({r['student_id']: r['status'] for r in db.list_students_by_class(class_id)},
                             {1: 'COMPLETED', 2: 'CANCELED'})
            with self.assertRaisesRegex(ValueError, '종료된 특강'):
                db.add_enrollment(3, class_id, '')
        self.assertEqual(db.list_timetable_by_class(1)[0]["start_time"], "18:00")

    def test_student_delete_respects_enrollment(self):
        from mysql.connector import IntegrityError

        student_id = db.add_student("삭제할 학생", None, None, None, None)
        db.update_student(student_id, "삭제할 학생", None, None, None, None, "ACTIVE")
        db.delete_mysql_student(student_id)
        self.assertNotIn(student_id, {row["student_id"] for row in db.list_students()})
        with self.assertRaises(IntegrityError):
            db.delete_mysql_student(1)


if __name__ == '__main__':
    unittest.main()
