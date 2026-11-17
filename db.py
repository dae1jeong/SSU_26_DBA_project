# -*- coding: utf-8 -*-
"""
db.py - 데이터베이스 접근 계층 (백엔드)
중고등 수학학원 관리 시스템

- SQLite(academy.db)에 연결하고, 테이블별 CRUD 함수를 제공한다.
- 화면(app.py)은 이 파일의 함수만 호출한다. (화면/DB 코드 분리)

[팀원 보완 포인트]
- 입력값 검증(전화번호 형식, 중복 체크 등)
- 더 많은 조회/통계 함수 (매출 집계, 기간 필터 등)
- 예외 처리 메시지 다듬기
"""

import os
import re
import sqlite3
from datetime import date

# 이 파일이 있는 폴더 기준으로 academy.db 경로 지정 (어느 위치에서 실행해도 동일)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "academy.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema_sqlite.sql")
SEED_PATH = os.path.join(BASE_DIR, "seed.sql")


def get_conn():
    """DB 커넥션 반환. FK 제약을 켜고, row를 dict처럼 접근 가능하게 설정."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(with_seed=True):
    """academy.db가 없으면 스키마(+샘플데이터)로 새로 생성."""
    need_seed = with_seed and not os.path.exists(DB_PATH)
    conn = get_conn()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    # 테이블이 비어있고 seed 요청이면 샘플 삽입
    if need_seed and os.path.exists(SEED_PATH):
        cur = conn.execute("SELECT COUNT(*) FROM student;")
        if cur.fetchone()[0] == 0:
            with open(SEED_PATH, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
    conn.commit()
    conn.close()
    migrate_nonnegative_fees()


def migrate_nonnegative_fees():
    """기존 양수 금액 제약을 0원 허용 제약으로 변경하고 ID·참조·인덱스를 보존한다."""
    conn = get_conn()
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            for table, column in (("course", "fee"), ("payment", "course_fee")):
                sql = conn.execute(
                    "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,),
                ).fetchone()[0]
                pattern = rf"\b{column}\s*>\s*0\b"
                if not re.search(pattern, sql, re.IGNORECASE):
                    continue
                updated = re.sub(pattern, f"typeof({column}) = 'integer' AND {column} >= 0", sql,
                                 flags=re.IGNORECASE)
                temporary = f"{table}_fee_migration"
                updated = re.sub(rf'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?["`\[]?{table}["`\]]?',
                                 f"CREATE TABLE {temporary}", updated, count=1, flags=re.IGNORECASE)
                objects = conn.execute(
                    "SELECT sql FROM sqlite_master WHERE tbl_name = ? "
                    "AND type IN ('index', 'trigger') AND sql IS NOT NULL", (table,),
                ).fetchall()
                sequence = conn.execute("SELECT seq FROM sqlite_sequence WHERE name = ?", (table,)).fetchone()
                conn.execute(updated)
                conn.execute(f"INSERT INTO {temporary} SELECT * FROM {table}")
                conn.execute(f"DROP TABLE {table}")
                conn.execute(f"ALTER TABLE {temporary} RENAME TO {table}")
                if sequence is not None:
                    conn.execute("UPDATE sqlite_sequence SET seq = MAX(seq, ?) WHERE name = ?",
                                 (sequence[0], table))
                for obj in objects:
                    conn.execute(obj["sql"])
            if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise ValueError("DB 연결 관계 검증에 실패하여 금액 제약 변경을 취소했습니다.")
    finally:
        conn.close()


# ============================================================
# 학생 (student)
# ============================================================
def add_student(name, school, grade, day_of_admission, contact_number, classification="ACTIVE"):
    conn = get_conn()
    conn.execute(
        """INSERT INTO student (name, school, grade, day_of_admission, contact_number, student_classification)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (name, school, grade, day_of_admission, contact_number, classification),
    )
    conn.commit()
    conn.close()


def list_students():
    conn = get_conn()
    rows = conn.execute(
        "SELECT student_id, name, school, grade, day_of_admission, contact_number, student_classification "
        "FROM student ORDER BY student_id"
    ).fetchall()
    conn.close()
    return rows


def update_student_classification(student_id, classification):
    conn = get_conn()
    conn.execute(
        "UPDATE student SET student_classification = ? WHERE student_id = ?",
        (classification, student_id),
    )
    conn.commit()
    conn.close()


# ============================================================
# 선생님 (teacher)
# ============================================================
def add_teacher(name, contact_number):
    conn = get_conn()
    conn.execute("INSERT INTO teacher (name, contact_number) VALUES (?, ?)", (name, contact_number))
    conn.commit()
    conn.close()


def list_teachers():
    conn = get_conn()
    rows = conn.execute("SELECT teacher_id, name, contact_number FROM teacher ORDER BY teacher_id").fetchall()
    conn.close()
    return rows


# ============================================================
# 수강과정 (course)
# ============================================================
def add_course(name, fee):
    name, fee = validate_course(name, fee)
    conn = get_conn()
    try:
        with conn:
            conn.execute("INSERT INTO course (name, fee) VALUES (?, ?)", (name, fee))
    finally:
        conn.close()


def validate_course(name, fee):
    name = name.strip()
    if not name:
        raise ValueError("과정명은 필수입니다.")
    if isinstance(fee, str):
        fee = fee.strip()
        if not re.fullmatch(r"[0-9]+", fee):
            raise ValueError("수강비는 0 이상의 정수로 입력하세요.")
        try:
            fee = int(fee)
        except ValueError:
            raise ValueError("수강비가 저장 가능한 정수 범위를 초과했습니다.") from None
    if type(fee) is not int or fee < 0:
        raise ValueError("수강비는 0 이상의 정수로 입력하세요.")
    if fee > 9223372036854775807:
        raise ValueError("수강비가 저장 가능한 정수 범위를 초과했습니다.")
    return name, fee


def update_course(course_id, name, fee):
    name, fee = validate_course(name, fee)
    conn = get_conn()
    try:
        with conn:
            result = conn.execute("UPDATE course SET name = ?, fee = ? WHERE course_id = ?",
                                  (name, fee, course_id))
            if result.rowcount != 1:
                raise ValueError("존재하지 않는 과정입니다. 목록을 새로고침하세요.")
    finally:
        conn.close()


def list_courses():
    conn = get_conn()
    rows = conn.execute("SELECT course_id, name, fee FROM course ORDER BY course_id").fetchall()
    conn.close()
    return rows


# ============================================================
# 반 (class)
# ============================================================
def add_class(course_id, teacher_id, grade, class_name):
    conn = get_conn()
    conn.execute(
        "INSERT INTO class (course_id, teacher_id, grade, class_name) VALUES (?, ?, ?, ?)",
        (course_id, teacher_id, grade, class_name),
    )
    conn.commit()
    conn.close()


def add_short_course(course_id, teacher_id, grade, class_name, start_date, end_date):
    """반과 특강 기간을 함께 저장. 실패하면 반 생성도 취소한다."""
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        if start.isoformat() != start_date or end.isoformat() != end_date:
            raise ValueError
    except ValueError:
        raise ValueError("특강 시작일과 종료일을 YYYY-MM-DD 형식의 올바른 날짜로 입력하세요.") from None
    if start > end:
        raise ValueError("특강 종료일은 시작일보다 빠를 수 없습니다.")

    conn = get_conn()
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO class (course_id, teacher_id, grade, class_name) VALUES (?, ?, ?, ?)",
                (course_id, teacher_id, grade, class_name),
            )
            conn.execute(
                "INSERT INTO short_course (class_id, start_date, end_date) VALUES (?, ?, ?)",
                (cur.lastrowid, start_date, end_date),
            )
    finally:
        conn.close()


def list_classes():
    """반 목록 + 과정명/선생님명을 JOIN해서 함께 반환."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT c.class_id, c.class_name, c.grade,
                  co.name AS course_name,
                  t.name  AS teacher_name,
                  sc.start_date, sc.end_date
           FROM class c
           LEFT JOIN course  co ON c.course_id  = co.course_id
           LEFT JOIN teacher t  ON c.teacher_id = t.teacher_id
           LEFT JOIN short_course sc ON c.class_id = sc.class_id
           ORDER BY c.class_id"""
    ).fetchall()
    conn.close()
    return rows


# ============================================================
# 시간표 (timetable)
# ============================================================
def save_timetable_by_class(class_id, schedule):
    """{요일 코드: (시작, 종료)} 전체를 검증한 뒤 반의 시간표를 원자적으로 저장한다."""
    labels = dict(zip(
        ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"),
        ("월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"),
    ))
    rows = []
    for day, times in schedule.items():
        if day not in labels:
            raise ValueError("올바른 수업 요일을 선택하세요.")
        label = labels[day]
        if not isinstance(times, (tuple, list)) or len(times) != 2:
            raise ValueError(f"{label}: 시작 시간과 종료 시간을 입력하세요.")
        start, end = times
        for field, value in (("시작", start), ("종료", end)):
            if not isinstance(value, str) or not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value):
                raise ValueError(f"{label}: {field} 시간을 HH:MM 형식(00:00~23:59)으로 입력하세요.")
        if start >= end:
            raise ValueError(f"{label}: 종료 시간은 시작 시간보다 늦어야 합니다. 자정을 넘기는 수업은 등록할 수 없습니다.")
        rows.append((day, class_id, start, end))

    conn = get_conn()
    try:
        with conn:
            if conn.execute("SELECT 1 FROM class WHERE class_id = ?", (class_id,)).fetchone() is None:
                raise ValueError("존재하지 않는 반입니다.")
            conn.execute("DELETE FROM timetable WHERE class_id = ?", (class_id,))
            conn.executemany(
                "INSERT INTO timetable (day_of_class, class_id, start_time, end_time) VALUES (?, ?, ?, ?)",
                rows,
            )
    finally:
        conn.close()


def list_timetable_by_class(class_id):
    """반의 주간 시간표를 월요일부터 일요일 순서로 조회한다."""
    conn = get_conn()
    try:
        return conn.execute(
            """SELECT day_of_class, start_time, end_time
               FROM timetable WHERE class_id = ?
               ORDER BY CASE day_of_class
                   WHEN 'MON' THEN 1 WHEN 'TUE' THEN 2 WHEN 'WED' THEN 3
                   WHEN 'THU' THEN 4 WHEN 'FRI' THEN 5 WHEN 'SAT' THEN 6
                   WHEN 'SUN' THEN 7 END""",
            (class_id,),
        ).fetchall()
    finally:
        conn.close()


# ============================================================
# 수강 등록 (enrollment)
# ============================================================
def add_enrollment(student_id, class_id, enrolled_date, status="ACTIVE"):
    """학생을 반에 등록. 블랙리스트 학생은 등록 차단."""
    conn = get_conn()
    # 블랙리스트 체크
    row = conn.execute(
        "SELECT student_classification FROM student WHERE student_id = ?", (student_id,)
    ).fetchone()
    if row is None:
        conn.close()
        raise ValueError("존재하지 않는 학생입니다.")
    if row["student_classification"] == "BLACK":
        conn.close()
        raise ValueError("블랙리스트 학생은 수강 등록이 불가합니다.")
    conn.execute(
        "INSERT INTO enrollment (student_id, class_id, enrolled_date, status) VALUES (?, ?, ?, ?)",
        (student_id, class_id, enrolled_date, status),
    )
    conn.commit()
    conn.close()


def list_enrollments():
    conn = get_conn()
    rows = conn.execute(
        """SELECT e.enrollment_id, s.name AS student_name, c.class_name,
                  e.enrolled_date, e.status
           FROM enrollment e
           JOIN student s ON e.student_id = s.student_id
           JOIN class   c ON e.class_id   = c.class_id
           ORDER BY e.enrollment_id"""
    ).fetchall()
    conn.close()
    return rows


def list_students_by_class(class_id):
    """특정 반의 학생 명단."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT s.student_id, s.name, s.school, e.status
           FROM enrollment e
           JOIN student s ON e.student_id = s.student_id
           WHERE e.class_id = ?
           ORDER BY s.name""",
        (class_id,),
    ).fetchall()
    conn.close()
    return rows


# ============================================================
# 결제 (payment)
# ============================================================
def list_active_classes_by_student(student_id):
    """학생이 현재 수강 중인 반과 각 과정의 수강비를 조회한다."""
    conn = get_conn()
    try:
        return conn.execute(
            """SELECT c.class_id, c.class_name, co.name AS course_name, co.fee
               FROM enrollment e
               JOIN class c ON c.class_id = e.class_id
               JOIN course co ON co.course_id = c.course_id
               WHERE e.student_id = ? AND e.status = 'ACTIVE'
               ORDER BY c.class_id""", (student_id,),
        ).fetchall()
    finally:
        conn.close()


def add_class_payment(student_id, class_id, payment_date):
    """수강 상태를 재확인하고 DB의 과정명·수강비로 결제 내역을 저장한다."""
    conn = get_conn()
    try:
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            student = conn.execute(
                "SELECT student_classification FROM student WHERE student_id = ?", (student_id,),
            ).fetchone()
            if student is None:
                raise ValueError("존재하지 않는 학생입니다.")
            if student["student_classification"] == "BLACK":
                raise ValueError("블랙리스트 학생은 결제가 불가합니다.")
            course = conn.execute(
                """SELECT co.name, co.fee FROM enrollment e
                   JOIN class c ON c.class_id = e.class_id
                   JOIN course co ON co.course_id = c.course_id
                   WHERE e.student_id = ? AND e.class_id = ? AND e.status = 'ACTIVE'""",
                (student_id, class_id),
            ).fetchone()
            if course is None:
                raise ValueError("현재 수강 중인 반만 결제할 수 있습니다. 학생과 반을 다시 선택하세요.")
            conn.execute(
                "INSERT INTO payment (student_id, course_name, course_fee, payment_date) VALUES (?, ?, ?, ?)",
                (student_id, course["name"], course["fee"], payment_date),
            )
    finally:
        conn.close()


def add_payment(student_id, course_name, course_fee, payment_date):
    """결제 입력. 블랙리스트 학생은 결제 차단."""
    conn = get_conn()
    row = conn.execute(
        "SELECT student_classification FROM student WHERE student_id = ?", (student_id,)
    ).fetchone()
    if row is None:
        conn.close()
        raise ValueError("존재하지 않는 학생입니다.")
    if row["student_classification"] == "BLACK":
        conn.close()
        raise ValueError("블랙리스트 학생은 결제가 불가합니다.")
    conn.execute(
        "INSERT INTO payment (student_id, course_name, course_fee, payment_date) VALUES (?, ?, ?, ?)",
        (student_id, course_name, course_fee, payment_date),
    )
    conn.commit()
    conn.close()


def list_payments():
    conn = get_conn()
    rows = conn.execute(
        """SELECT p.payment_id, s.name AS student_name, p.course_name,
                  p.course_fee, p.payment_date
           FROM payment p
           JOIN student s ON p.student_id = s.student_id
           ORDER BY p.payment_date DESC, p.payment_id DESC"""
    ).fetchall()
    conn.close()
    return rows


def total_revenue():
    """총 매출 합계 (간단 통계 예시)."""
    conn = get_conn()
    row = conn.execute("SELECT COALESCE(SUM(course_fee), 0) AS total FROM payment").fetchone()
    conn.close()
    return row["total"]


if __name__ == "__main__":
    # 단독 실행 시: DB 초기화 + 간단 확인
    init_db()
    print("academy.db 초기화 완료")
    print("학생 수:", len(list_students()))
    print("총 매출:", total_revenue())
