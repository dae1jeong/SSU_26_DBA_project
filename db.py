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

GRADE_LEVELS = tuple(f"{level}{grade}" for level, count in (("초", 6), ("중", 3), ("고", 3))
                     for grade in range(1, count + 1))
PAYMENT_TRANSITIONS = {"UNPAID": "PAID", "PAID": "REFUNDED"}

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
        schema = f.read()
        conn.executescript(schema)
    # 테이블이 비어있고 seed 요청이면 샘플 삽입
    if need_seed and os.path.exists(SEED_PATH):
        cur = conn.execute("SELECT COUNT(*) FROM student;")
        if cur.fetchone()[0] == 0:
            with open(SEED_PATH, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
    conn.commit()
    conn.close()
    migrate_nonnegative_fees()
    migrate_academy_fields(schema)
    sync_expired_short_courses()


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
                columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({table})")]
                replace_table(conn, table, updated, {}, columns)
            if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise ValueError("DB 연결 관계 검증에 실패하여 금액 제약 변경을 취소했습니다.")
    finally:
        conn.close()


def replace_table(conn, table, ddl, replacements, columns):
    """트랜잭션 안에서 테이블을 재구성하고 명시 인덱스·트리거·ID 시퀀스를 복원한다."""
    temporary = f"{table}_migration"
    ddl = re.sub(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?["`\[]?' + table + r'["`\]]?',
                 f"CREATE TABLE {temporary}", ddl, count=1, flags=re.IGNORECASE)
    objects = conn.execute(
        "SELECT sql FROM sqlite_master WHERE tbl_name = ? "
        "AND type IN ('index', 'trigger') AND sql IS NOT NULL", (table,),
    ).fetchall()
    sequence = conn.execute("SELECT seq FROM sqlite_sequence WHERE name = ?", (table,)).fetchone()
    names = ", ".join(f'"{name}"' for name in columns)
    placeholders = ", ".join("?" for name in columns)
    rows = [tuple(replacements.get((row[0], name), row[name]) for name in columns)
            for row in conn.execute(f"SELECT {names} FROM {table}")]
    conn.execute(ddl)
    conn.executemany(f"INSERT INTO {temporary} ({names}) VALUES ({placeholders})", rows)
    conn.execute(f"DROP TABLE {table}")
    conn.execute(f"ALTER TABLE {temporary} RENAME TO {table}")
    if sequence is not None:
        conn.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
        conn.execute("INSERT INTO sqlite_sequence(name, seq) VALUES (?, ?)", (table, sequence[0]))
    for obj in objects:
        conn.execute(obj["sql"])


def migrate_academy_fields(schema):
    conn = get_conn()
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            for table, hint in (("student", "school"), ("class", "class_name"), ("payment", None)):
                fields = {row["name"]: row["type"] for row in conn.execute(f"PRAGMA table_info({table})")}
                key = "grade" if hint else "status"
                if fields.get(key) == "TEXT":
                    continue
                ddl = re.search(rf'^CREATE TABLE IF NOT EXISTS {table} \(.*?^\);',
                                schema, flags=re.M | re.S)[0]
                replacements = {}
                if hint:
                    id_column = f"{table}_id"
                    for row in conn.execute(f"SELECT {id_column}, grade, {hint} FROM {table} WHERE grade IS NOT NULL"):
                        grade = legacy_grade(row["grade"], row[hint], table)
                        replacements[row[0], "grade"] = grade
                        if grade is None:
                            conn.execute("""CREATE TABLE IF NOT EXISTS legacy_grade (
                                source_table TEXT NOT NULL, record_id INTEGER NOT NULL,
                                original_grade TEXT NOT NULL, PRIMARY KEY (source_table, record_id)
                            )""")
                            conn.execute("INSERT INTO legacy_grade VALUES (?, ?, ?)", (table, row[0], row["grade"]))
                else:
                    # 이전 결제에는 실제 결제일이 있었으므로 납부 완료로 이관한다.
                    conn.execute("ALTER TABLE payment ADD COLUMN status TEXT NOT NULL DEFAULT 'PAID'")
                    fields["status"] = "TEXT"
                replace_table(conn, table, ddl, replacements, fields)
            if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise ValueError("외래키 검증에 실패하여 DB 변경을 취소했습니다.")
    finally:
        conn.close()


def legacy_grade(grade, hint, table):
    grade = str(grade)
    if grade in GRADE_LEVELS:
        return grade
    hint = (hint or "").strip()
    if table == "student":
        match = re.search(r"(초|중|고)(?:등학교|학교)?$", hint)
    else:
        match = re.search(rf"(초|중|고){re.escape(grade)}(?![0-9])", hint)
    level_grade = match[1] + grade if match else None
    return level_grade if level_grade in GRADE_LEVELS else None


def sync_expired_short_courses():
    """종료일 다음 날부터 진행 중인 특강 수강을 수료 처리한다."""
    conn = get_conn()
    try:
        with conn:
            conn.execute("""UPDATE enrollment SET status = 'COMPLETED'
                WHERE status = 'ACTIVE' AND class_id IN (
                    SELECT class_id FROM short_course WHERE end_date < ?
                )""", (date.today().isoformat(),))
    finally:
        conn.close()


def prevent_expired_enrollment(conn, class_id):
    if conn.execute("SELECT 1 FROM short_course WHERE class_id = ? AND end_date < ?",
                    (class_id, date.today().isoformat())).fetchone():
        raise ValueError("종료된 특강은 수강을 등록하거나 활성화할 수 없습니다.")


# ============================================================
# 학생 (student)
# ============================================================
def add_student(name, school, grade, day_of_admission, contact_number, classification="ACTIVE"):
    name, school, grade, day_of_admission, contact_number, classification = validate_student(
        name, school, grade, day_of_admission, contact_number, classification)
    conn = get_conn()
    try:
        with conn:
            conn.execute(
                """INSERT INTO student (name, school, grade, day_of_admission, contact_number, student_classification)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, school, grade, day_of_admission, contact_number, classification),
            )
    finally:
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
    try:
        with conn:
            conn.execute(
                "UPDATE student SET student_classification = ? WHERE student_id = ?",
                (classification, student_id),
            )
    finally:
        conn.close()


# ============================================================
# 선생님 (teacher)
# ============================================================
def add_teacher(name, contact_number):
    name = name.strip()
    if not name:
        raise ValueError("선생님 이름은 필수입니다.")
    conn = get_conn()
    try:
        with conn:
            conn.execute(
                "INSERT INTO teacher (name, contact_number) VALUES (?, ?)",
                (name, normalize_contact(contact_number)),
            )
    finally:
        conn.close()


def list_teachers():
    conn = get_conn()
    rows = conn.execute("SELECT teacher_id, name, contact_number FROM teacher ORDER BY teacher_id").fetchall()
    conn.close()
    return rows


def update_teacher(teacher_id, name, contact_number):
    name = name.strip()
    if not name:
        raise ValueError("선생님 이름은 필수입니다.")
    conn = get_conn()
    try:
        with conn:
            result = conn.execute(
                "UPDATE teacher SET name = ?, contact_number = ? WHERE teacher_id = ?",
                (name, normalize_contact(contact_number), teacher_id),
            )
            if result.rowcount != 1:
                raise ValueError("존재하지 않는 선생님입니다.")
    finally:
        conn.close()


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
    grade = validate_grade(grade)
    class_name = class_name.strip()
    if not class_name:
        raise ValueError("반 이름은 필수입니다.")
    conn = get_conn()
    try:
        with conn:
            conn.execute(
                "INSERT INTO class (course_id, teacher_id, grade, class_name) VALUES (?, ?, ?, ?)",
                (course_id, teacher_id, grade, class_name),
            )
    finally:
        conn.close()


def add_short_course(course_id, teacher_id, grade, class_name, start_date, end_date):
    """반과 특강 기간을 함께 저장. 실패하면 반 생성도 취소한다."""
    grade = validate_grade(grade)
    if not class_name.strip():
        raise ValueError("반 이름은 필수입니다.")
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


def update_class(class_id, class_name, grade, teacher_id):
    """과정과 특강 기간은 유지하고 반 이름·학년·담당 선생님만 변경한다."""
    class_name = class_name.strip()
    if not class_name:
        raise ValueError("반 이름은 필수입니다.")
    grade = validate_grade(grade)
    conn = get_conn()
    try:
        with conn:
            if teacher_id is not None and conn.execute(
                "SELECT 1 FROM teacher WHERE teacher_id = ?", (teacher_id,),
            ).fetchone() is None:
                raise ValueError("존재하지 않는 선생님입니다. 다시 선택하세요.")
            result = conn.execute(
                "UPDATE class SET class_name = ?, grade = ?, teacher_id = ? WHERE class_id = ?",
                (class_name, grade, teacher_id, class_id),
            )
            if result.rowcount != 1:
                raise ValueError("존재하지 않는 반입니다.")
    finally:
        conn.close()


def list_classes():
    """반 목록 + 과정명/선생님명을 JOIN해서 함께 반환."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT c.class_id, c.class_name, c.grade, c.course_id, c.teacher_id,
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
    enrolled_date = validate_date(enrolled_date)
    if status not in ("ACTIVE", "COMPLETED", "CANCELED"):
        raise ValueError("올바른 수강 상태를 선택하세요.")
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
    try:
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            if status == "ACTIVE":
                prevent_expired_enrollment(conn, class_id)
            if conn.execute("SELECT 1 FROM enrollment WHERE student_id=? AND class_id=?",
                            (student_id, class_id)).fetchone():
                raise ValueError("이미 등록된 반입니다. 기존 수강의 상태를 변경하세요.")
            conn.execute("INSERT INTO enrollment (student_id, class_id, enrolled_date, status) VALUES (?, ?, ?, ?)",
                         (student_id, class_id, enrolled_date, status))
    finally:
        conn.close()


def list_enrollments():
    sync_expired_short_courses()
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
    sync_expired_short_courses()
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
    sync_expired_short_courses()
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


def add_class_payment(student_id, class_id, payment_date, status="PAID"):
    """수강 상태를 재확인하고 DB의 과정명·수강비로 결제 내역을 저장한다."""
    if status not in ("PAID", "UNPAID"):
        raise ValueError("신규 결제 상태는 완납 또는 미납을 선택하세요.")
    payment_date = validate_date(payment_date) if status == "PAID" else None
    sync_expired_short_courses()
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
                   WHERE e.student_id = ? AND e.class_id = ? AND e.status = 'ACTIVE'
                     AND NOT EXISTS (SELECT 1 FROM short_course sc
                         WHERE sc.class_id = c.class_id AND sc.end_date < ?)""",
                (student_id, class_id, date.today().isoformat()),
            ).fetchone()
            if course is None:
                raise ValueError("현재 수강 중인 반만 결제할 수 있습니다. 학생과 반을 다시 선택하세요.")
            conn.execute(
                "INSERT INTO payment (student_id, course_name, course_fee, payment_date, status) VALUES (?, ?, ?, ?, ?)",
                (student_id, course["name"], course["fee"], payment_date, status),
            )
    finally:
        conn.close()


def add_payment(student_id, course_name, course_fee, payment_date):
    """결제 입력. 블랙리스트 학생은 결제 차단."""
    course_name, course_fee = validate_course(course_name, course_fee)
    payment_date = validate_date(payment_date)
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
    try:
        with conn:
            conn.execute(
                "INSERT INTO payment (student_id, course_name, course_fee, payment_date, status) VALUES (?, ?, ?, ?, 'PAID')",
                (student_id, course_name, course_fee, payment_date),
            )
    finally:
        conn.close()


def update_payment_status(payment_id, status, payment_date=None):
    conn = get_conn()
    try:
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("""SELECT p.status, p.payment_date, s.student_classification
                FROM payment p JOIN student s ON p.student_id = s.student_id
                WHERE p.payment_id = ?""", (payment_id,)).fetchone()
            if row is None:
                raise ValueError("존재하지 않는 결제 내역입니다.")
            if not status or PAYMENT_TRANSITIONS.get(row["status"]) != status:
                raise ValueError("미납은 완납으로, 완납은 환불로 변경할 수 있습니다.")
            if status == "PAID" and row["student_classification"] == "BLACK":
                raise ValueError("블랙리스트 학생은 결제가 불가합니다.")
            paid_on = validate_date(payment_date) if status == "PAID" else row["payment_date"]
            conn.execute("UPDATE payment SET status = ?, payment_date = ? WHERE payment_id = ?",
                         (status, paid_on, payment_id))
    finally:
        conn.close()


def payment_filters(student_id=None, start_date=None, end_date=None):
    clauses, values = [], []
    for value, column, operator in ((student_id, 'p.student_id', '='),
                                     (start_date, 'p.payment_date', '>='),
                                     (end_date, 'p.payment_date', '<=')):
        if value is not None and value != '':
            if column == 'p.payment_date':
                value = validate_date(value)
            clauses.append(f"{column} {operator} ?")
            values.append(value)
    if start_date and end_date and start_date > end_date:
        raise ValueError("종료일은 시작일보다 빠를 수 없습니다.")
    return (' WHERE ' + ' AND '.join(clauses) if clauses else ''), values


def list_payments(student_id=None, start_date=None, end_date=None):
    where, values = payment_filters(student_id, start_date, end_date)
    conn = get_conn()
    rows = conn.execute(
        """SELECT p.payment_id, s.name AS student_name, p.course_name,
                  p.course_fee, p.payment_date, p.status
           FROM payment p
           JOIN student s ON p.student_id = s.student_id
           """ + where + " ORDER BY p.payment_date DESC, p.payment_id DESC", values
    ).fetchall()
    conn.close()
    return rows


def total_revenue(student_id=None, start_date=None, end_date=None):
    where, values = payment_filters(student_id, start_date, end_date)
    paid_clause = " AND p.status = 'PAID'" if where else " WHERE p.status = 'PAID'"
    conn = get_conn()
    try:
        return conn.execute("SELECT COALESCE(SUM(p.course_fee), 0) FROM payment p" + where + paid_clause,
                            values).fetchone()[0]
    finally:
        conn.close()


def validate_date(value, optional=False):
    value = (value or "").strip()
    if not value:
        return None if optional else date.today().isoformat()
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except ValueError:
        raise ValueError("날짜는 YYYY-MM-DD 형식의 올바른 날짜로 입력하세요.") from None
    return value


def validate_student(name, school, grade, admission, contact, classification):
    name = name.strip()
    if not name:
        raise ValueError("학생 이름은 필수입니다.")
    if classification not in ('ACTIVE', 'INACTIVE', 'BLACK'):
        raise ValueError("올바른 학생 분류를 선택하세요.")
    grade = validate_grade(grade)
    return name, (school or '').strip() or None, grade, validate_date(admission, True), normalize_contact(contact, student=True), classification


def normalize_contact(value, student=False):
    value = (value or "").strip()
    if not value:
        return None
    prefix = r"01[0-9]" if student else r"0[0-9]{1,2}"
    if re.fullmatch(rf"{prefix}-[0-9]{{3,4}}-[0-9]{{4}}", value):
        return value
    prefix = r"02" if not student and value.startswith("02") else r"0[0-9]{2}"
    if re.fullmatch(rf"{prefix}[0-9]{{7,8}}", value) and (not student or value.startswith("01")):
        prefix_length = 2 if prefix == "02" else 3
        return f"{value[:prefix_length]}-{value[prefix_length:-4]}-{value[-4:]}"
    description = "휴대전화 번호" if student else "국내 전화번호"
    raise ValueError(f"{description}를 올바르게 입력하세요 (예: 010-1234-5678).")


def validate_grade(grade):
    if grade is None or (isinstance(grade, str) and not grade.strip()):
        return None
    if not isinstance(grade, str) or grade.strip() not in GRADE_LEVELS:
        raise ValueError("초1~초6, 중1~중3, 고1~고3 중에서 학년을 선택하세요.")
    return grade.strip()


def update_student(student_id, name, school, grade, admission, contact, classification):
    values = validate_student(name, school, grade, admission, contact, classification)
    conn = get_conn()
    try:
        with conn:
            result = conn.execute("""UPDATE student SET name=?, school=?, grade=?,
                day_of_admission=?, contact_number=?, student_classification=? WHERE student_id=?""",
                (*values, student_id))
            if result.rowcount != 1:
                raise ValueError("존재하지 않는 학생입니다.")
    finally:
        conn.close()


def update_enrollment_status(enrollment_id, status):
    if status not in ('ACTIVE', 'COMPLETED', 'CANCELED'):
        raise ValueError("올바른 수강 상태를 선택하세요.")
    conn = get_conn()
    try:
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("""SELECT s.student_classification, e.class_id FROM enrollment e
                JOIN student s ON s.student_id=e.student_id WHERE e.enrollment_id=?""",
                (enrollment_id,)).fetchone()
            if row is None:
                raise ValueError("존재하지 않는 수강 등록입니다.")
            if status == 'ACTIVE' and row[0] == 'BLACK':
                raise ValueError("블랙리스트 학생의 수강을 활성화할 수 없습니다.")
            if status == "ACTIVE":
                prevent_expired_enrollment(conn, row["class_id"])
            conn.execute("UPDATE enrollment SET status=? WHERE enrollment_id=?", (status, enrollment_id))
    finally:
        conn.close()


def list_enrollments_by_student(student_id):
    sync_expired_short_courses()
    conn = get_conn()
    try:
        return conn.execute("""SELECT e.enrollment_id, c.class_name, co.name AS course_name,
            co.fee, e.enrolled_date, e.status FROM enrollment e
            JOIN class c ON c.class_id=e.class_id JOIN course co ON co.course_id=c.course_id
            WHERE e.student_id=? ORDER BY e.enrollment_id""", (student_id,)).fetchall()
    finally:
        conn.close()


if __name__ == "__main__":
    # 단독 실행 시: DB 초기화 + 간단 확인
    init_db()
    print("academy.db 초기화 완료")
    print("학생 수:", len(list_students()))
    print("총 매출:", total_revenue())
