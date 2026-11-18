"""실제 academy.db를 변경하지 않는 기능 통합 검사."""
import ast
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import db


class Workflows(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_path = db.DB_PATH
        db.DB_PATH = str(Path(self.temp.name) / 'academy.db')
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self.old_path
        self.temp.cleanup()

    def test_student_edit_preserves_relations_and_validates(self):
        db.update_student(1, '수정학생', '새학교', '3', '2026-11-19', '', 'INACTIVE')
        row = db.list_students()[0]
        self.assertEqual((row['name'], row['grade'], row['contact_number']), ('수정학생', 3, None))
        self.assertEqual(len(db.list_enrollments_by_student(1)), 1)
        self.assertEqual(len(db.list_payments(1)), 1)
        for grade, admission in (('-1', ''), ('2', '2026-02-30'), ('abc', '')):
            with self.assertRaises(ValueError):
                db.update_student(1, '학생', '', grade, admission, '', 'ACTIVE')
        self.assertEqual(db.list_students()[0]['name'], '수정학생')

    def test_status_payment_and_reactivation(self):
        db.update_enrollment_status(1, 'COMPLETED')
        self.assertEqual(len(db.list_active_classes_by_student(1)), 0)
        with self.assertRaises(ValueError):
            db.add_class_payment(1, 1, '')
        self.assertEqual(len(db.list_payments(1)), 1)
        db.update_enrollment_status(1, 'ACTIVE')
        db.add_class_payment(1, 1, '')
        self.assertEqual(db.list_payments(1)[0]['payment_date'], date.today().isoformat())
        db.update_student_classification(1, 'BLACK')
        db.update_enrollment_status(1, 'CANCELED')
        with self.assertRaises(ValueError):
            db.update_enrollment_status(1, 'ACTIVE')
        with self.assertRaises(ValueError):
            db.add_class_payment(1, 1, '')
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
        db.add_class_payment(1, 1, '2026-11-19')
        payments = db.list_payments(1)
        self.assertEqual(payments[0]['course_fee'], 0)
        self.assertEqual(payments[1]['course_fee'], 250000)
        self.assertEqual(payments[1]['course_name'], '중등 수학 정규반')

    def test_duplicate_dates_timetable_and_short_course(self):
        with self.assertRaisesRegex(ValueError, '이미 등록'):
            db.add_enrollment(1, 1, '')
        with self.assertRaises(ValueError):
            db.add_enrollment(2, 1, '2026-13-01')
        db.add_enrollment(2, 1, '')
        self.assertEqual(db.list_enrollments()[-1]['enrolled_date'], date.today().isoformat())
        original = [tuple(r) for r in db.list_timetable_by_class(1)]
        with self.assertRaises(ValueError):
            db.save_timetable_by_class(1, {'MON': ('20:00', '19:00')})
        self.assertEqual([tuple(r) for r in db.list_timetable_by_class(1)], original)
        before = len(db.list_classes())
        with self.assertRaises(ValueError):
            db.add_short_course(1, None, 2, '특강', '2026-12-31', '2026-12-01')
        self.assertEqual(len(db.list_classes()), before)
        conn = db.get_conn()
        try:
            self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(), [])
        finally:
            conn.close()

    def test_old_database_migration(self):
        old = sqlite3.connect(db.DB_PATH)
        old.close()
        # 최초 개발 브랜치의 양수 제약 DB를 별도 파일에서 검사한다.
        import subprocess
        old_schema = subprocess.check_output(['git', 'show', 'ecda2f1:schema_sqlite.sql'], text=True)
        legacy = str(Path(self.temp.name) / 'legacy.db')
        conn = sqlite3.connect(legacy)
        conn.executescript(old_schema)
        conn.executescript(Path(db.SEED_PATH).read_text())
        conn.close()
        db.DB_PATH = legacy
        db.init_db()
        db.update_course(1, '무료', 0)
        db.add_class_payment(1, 1, '2026-11-19')
        self.assertEqual(db.total_revenue(), 1400000)
        conn = db.get_conn()
        self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(), [])
        self.assertEqual(len(db.list_classes()), 5)
        conn.close()


if __name__ == '__main__':
    unittest.main()
