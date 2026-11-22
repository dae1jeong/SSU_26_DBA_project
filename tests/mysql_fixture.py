"""MySQL integration fixtures in a fresh schema on an explicit test instance."""
import os
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from mysql.connector import connect
from mysql.connector.constants import ClientFlag

import db


class MySQLTestCase(unittest.TestCase):
    def setUp(self):
        socket = os.getenv("ACADEMY_MYSQL_TEST_SOCKET")
        if not socket:
            self.skipTest("Set ACADEMY_MYSQL_TEST_SOCKET to a dedicated MySQL test server.")
        schema = f"academy_test_{uuid4().hex}"
        settings = {
            "unix_socket": socket,
            "user": os.getenv("ACADEMY_MYSQL_TEST_USER", "root"),
            "password": os.getenv("ACADEMY_MYSQL_TEST_PASSWORD", ""),
            "client_flags": [ClientFlag.FOUND_ROWS],
        }
        self.addCleanup(self.drop_schema, settings, schema)
        ddl = (Path(__file__).resolve().parents[1] / "sql/mysql/academy_physical_model_v6.sql").read_text()
        tables, routines = ddl.replace("math_academy", schema).split("DELIMITER $$")
        with closing(connect(**settings)) as connection, closing(connection.cursor()) as cursor:
            for statement in tables.split(";") + routines.split("DELIMITER ;")[0].split("$$"):
                if statement.strip():
                    cursor.execute(statement)

        backend = patch.object(db, "get_mysql_conn", side_effect=lambda: connect(database=schema, **settings))
        backend.start()
        self.addCleanup(backend.stop)
        db.init_db()
        for name in ("학생 하나", "학생 둘", "학생 셋"):
            db.add_student(name, None, "중2", None, None)
        for name, fee in (("중등 수학 정규반", 250000), ("두 번째 과정", 350000), ("세 번째 과정", 800000)):
            db.add_course(name, fee)
        for course_id in range(1, 4):
            db.add_class(course_id, None, "중2", f"{course_id}반")
            db.add_enrollment(course_id, course_id, "2026-01-01")
        db.add_class(1, None, "중2", "여분 반")
        db.add_class_payment(1, 1, "2026-03-02", billing_month="2026-03")
        db.add_class_payment(2, 2, "2026-03-05", billing_month="2026-03")
        db.add_class_payment(3, 3, "2026-04-01", billing_month="2026-04")
        db.save_timetable_by_class(1, {"MON": ("18:00", "20:00")})

    @staticmethod
    def drop_schema(settings, schema):
        with closing(connect(**settings)) as connection, closing(connection.cursor()) as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{schema}`")
