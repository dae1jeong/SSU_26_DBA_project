# -*- coding: utf-8 -*-
"""MySQL v6 데이터베이스 접근 계층."""

import datetime
import os
import re
from calendar import monthrange
from contextlib import closing
from datetime import date, timedelta

GRADE_LEVELS = tuple(f"{level}{grade}" for level, count in (("초", 6), ("중", 3), ("고", 3))
                     for grade in range(1, count + 1))
PAYMENT_TRANSITIONS = {"UNPAID": "PAID", "PAID": "REFUNDED"}


def get_mysql_conn():
    """프로젝트 환경 변수로 MySQL v6 데이터베이스에 연결한다."""
    from mysql.connector import connect
    from mysql.connector.constants import ClientFlag

    user = os.getenv("ACADEMY_MYSQL_USER")
    if not user:
        raise ValueError("ACADEMY_MYSQL_USER에 MySQL 계정을 설정하세요.")
    return connect(
        host=os.getenv("ACADEMY_MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("ACADEMY_MYSQL_PORT", "3306")),
        database=os.getenv("ACADEMY_MYSQL_DATABASE", "math_academy"),
        user=user,
        password=os.getenv("ACADEMY_MYSQL_PASSWORD", ""),
        connection_timeout=5,
        client_flags=[ClientFlag.FOUND_ROWS],
    )


class QueryResult:
    def __init__(self, cursor):
        self.rowcount = cursor.rowcount
        self.lastrowid = cursor.lastrowid
        self.rows = iter(cursor.fetchall() if cursor.with_rows else ())

    @staticmethod
    def format_row(row):
        for key, value in row.items():
            if isinstance(value, datetime.date):
                row[key] = value.isoformat()
            elif isinstance(value, timedelta):
                hours, seconds = divmod(int(value.total_seconds()), 3600)
                row[key] = f"{hours:02d}:{seconds // 60:02d}"
        return row

    def fetchall(self):
        return [self.format_row(row) for row in self.rows]

    def fetchone(self):
        row = next(self.rows, None)
        return self.format_row(row) if row is not None else None


class DatabaseSession:
    """한 연결에서 여러 SQL 문을 실행하고 트랜잭션을 관리한다."""

    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, values=()):
        with closing(self.connection.cursor(dictionary=True)) as cursor:
            cursor.execute(query, values)
            return QueryResult(cursor)

    def executemany(self, query, rows):
        with closing(self.connection.cursor()) as cursor:
            cursor.executemany(query, rows)

    def __enter__(self):
        return self

    def __exit__(self, error_type, error, traceback):
        if error_type is None:
            self.connection.commit()
        else:
            self.connection.rollback()

    def close(self):
        self.connection.close()


def get_conn():
    return DatabaseSession(get_mysql_conn())


def init_db():
    """v6 스키마가 설치된 서버에 앱이 접근할 수 있는지 확인한다."""
    with closing(get_conn()) as conn:
        conn.execute("SELECT student_id FROM student LIMIT 0")
    sync_expired_short_courses()


def sync_expired_short_courses():
    """종료일 다음 날부터 진행 중인 특강 수강을 수료 처리한다."""
    conn = get_conn()
    try:
        with conn:
            conn.execute("""UPDATE enrollment SET status = 'COMPLETED'
                WHERE status = 'ACTIVE' AND class_id IN (
                    SELECT class_id FROM short_course WHERE end_date < %s
                )""", (date.today().isoformat(),))
    finally:
        conn.close()


def prevent_expired_enrollment(conn, class_id):
    if conn.execute("SELECT 1 FROM short_course WHERE class_id = %s AND end_date < %s",
                    (class_id, date.today().isoformat())).fetchone():
        raise ValueError("종료된 특강은 수강을 등록하거나 활성화할 수 없습니다.")


# ============================================================
# 학생 (student)
# ============================================================
def add_student(name, school, grade, day_of_admission, contact_number, classification="ACTIVE"):
    values = validate_student(name, school, grade, day_of_admission, contact_number, classification)
    return write_student(
        """INSERT INTO student (name, school, grade, day_of_admission, contact_number, student_classification)
           VALUES (%s, %s, %s, %s, %s, %s)""", values,
    )


def list_students():
    with closing(get_conn()) as conn:
        return conn.execute(
            "SELECT student_id, name, school, grade, day_of_admission, contact_number, student_classification "
            "FROM student ORDER BY student_id"
        ).fetchall()


def update_student_classification(student_id, classification):
    if classification not in ("ACTIVE", "INACTIVE", "BLACK"):
        raise ValueError("올바른 학생 분류를 선택하세요.")
    write_student("UPDATE student SET student_classification = %s WHERE student_id = %s",
                  (classification, student_id))


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
                "INSERT INTO teacher (name, contact_number) VALUES (%s, %s)",
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
                "UPDATE teacher SET name = %s, contact_number = %s WHERE teacher_id = %s",
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
            conn.execute("INSERT INTO course (name, fee) VALUES (%s, %s)", (name, fee))
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
    if fee > 4294967295:
        raise ValueError("수강비가 저장 가능한 정수 범위를 초과했습니다.")
    return name, fee


def update_course(course_id, name, fee):
    name, fee = validate_course(name, fee)
    conn = get_conn()
    try:
        with conn:
            result = conn.execute("UPDATE course SET name = %s, fee = %s WHERE course_id = %s",
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
                "INSERT INTO class (course_id, teacher_id, grade, class_name) VALUES (%s, %s, %s, %s)",
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
                "INSERT INTO class (course_id, teacher_id, grade, class_name) VALUES (%s, %s, %s, %s)",
                (course_id, teacher_id, grade, class_name),
            )
            conn.execute(
                "INSERT INTO short_course (class_id, start_date, end_date) VALUES (%s, %s, %s)",
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
                "SELECT 1 FROM teacher WHERE teacher_id = %s", (teacher_id,),
            ).fetchone() is None:
                raise ValueError("존재하지 않는 선생님입니다. 다시 선택하세요.")
            result = conn.execute(
                "UPDATE class SET class_name = %s, grade = %s, teacher_id = %s WHERE class_id = %s",
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
            if conn.execute("SELECT 1 FROM class WHERE class_id = %s FOR UPDATE", (class_id,)).fetchone() is None:
                raise ValueError("존재하지 않는 반입니다.")
            conn.execute("DELETE FROM timetable WHERE class_id = %s", (class_id,))
            conn.executemany(
                "INSERT INTO timetable (day_of_class, class_id, start_time, end_time) VALUES (%s, %s, %s, %s)",
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
               FROM timetable WHERE class_id = %s
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
    try:
        with conn:
            row = conn.execute(
                "SELECT student_classification FROM student WHERE student_id = %s FOR UPDATE", (student_id,)
            ).fetchone()
            if row is None:
                raise ValueError("존재하지 않는 학생입니다.")
            if row["student_classification"] == "BLACK":
                raise ValueError("블랙리스트 학생은 수강 등록이 불가합니다.")
            if status == "ACTIVE":
                prevent_expired_enrollment(conn, class_id)
            if conn.execute("SELECT 1 FROM enrollment WHERE student_id=%s AND class_id=%s",
                            (student_id, class_id)).fetchone():
                raise ValueError("이미 등록된 반입니다. 기존 수강의 상태를 변경하세요.")
            conn.execute("INSERT INTO enrollment (student_id, class_id, enrolled_date, status) VALUES (%s, %s, %s, %s)",
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
           WHERE e.class_id = %s
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
               WHERE e.student_id = %s AND e.status = 'ACTIVE'
               ORDER BY c.class_id""", (student_id,),
        ).fetchall()
    finally:
        conn.close()


def normalize_billing_month(value):
    """YYYY-MM 또는 DB 저장 형식 YYYY-MM-01을 월 초 날짜로 변환한다."""
    if isinstance(value, str):
        value = value.strip()
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}(?:-01)?", value):
            try:
                return date.fromisoformat(value[:7] + "-01")
            except ValueError:
                pass
    raise ValueError("청구월은 실제 연·월을 YYYY-MM 형식으로 입력하세요.")


def payment_targets_query(month):
    last_day = month.replace(day=monthrange(month.year, month.month)[1])
    return """SELECT e.enrollment_id, e.student_id, e.class_id, s.name AS student_name,
                c.class_name, co.name AS course_name, co.fee,
                p.payment_id, p.status, p.course_fee AS billed_fee
           FROM enrollment e
           JOIN student s ON s.student_id = e.student_id
           JOIN class c ON c.class_id = e.class_id
           JOIN course co ON co.course_id = c.course_id
           LEFT JOIN short_course sc ON sc.class_id = c.class_id
           LEFT JOIN payment p ON p.enrollment_id = e.enrollment_id AND p.billing_month = %s
           WHERE e.status = 'ACTIVE' AND s.student_classification <> 'BLACK'
             AND e.enrolled_date <= %s
             AND (sc.class_id IS NULL OR (sc.start_date <= %s AND sc.end_date >= %s))""", (
        month.isoformat(), last_day.isoformat(), last_day.isoformat(), max(month, date.today()).isoformat(),
    )


def list_payment_targets(billing_month, student_id=None):
    month = normalize_billing_month(billing_month)
    sync_expired_short_courses()
    conn = get_conn()
    try:
        query, params = payment_targets_query(month)
        if student_id is not None:
            query += " AND e.student_id = %s"
            params = (*params, student_id)
        return conn.execute(query + " ORDER BY s.name, e.student_id, c.class_name, e.class_id", params).fetchall()
    finally:
        conn.close()


def add_class_payment(student_id, class_id, payment_date, status="PAID", billing_month=None):
    """선택 월의 수강 자격을 확인하고 월별 청구와 당시 수강비를 저장한다."""
    if status not in ("PAID", "UNPAID"):
        raise ValueError("신규 결제 상태는 완납 또는 미납을 선택하세요.")
    month = normalize_billing_month(date.today().isoformat()[:7] if billing_month is None else billing_month)
    payment_date = validate_date(payment_date) if status == "PAID" else None
    sync_expired_short_courses()
    conn = get_conn()
    try:
        with conn:
            query, params = payment_targets_query(month)
            target = conn.execute(query + " AND e.student_id = %s AND e.class_id = %s FOR UPDATE",
                                  (*params, student_id, class_id)).fetchone()
            if target is None:
                raise ValueError("선택한 월의 결제 대상이 아닙니다. 학생·반과 수강 기간을 확인하세요.")
            if target["payment_id"] is not None:
                raise ValueError("이 수강의 청구가 해당 월에 이미 등록되어 있습니다.")
            conn.execute("""INSERT INTO payment
                (enrollment_id, billing_month, course_name, course_fee, payment_date, status)
                VALUES (%s, %s, %s, %s, %s, %s)""",
                (target["enrollment_id"], month.isoformat(), target["course_name"],
                 target["fee"], payment_date, status),
            )
    finally:
        conn.close()


def update_payment_status(payment_id, status, payment_date=None):
    conn = get_conn()
    try:
        with conn:
            row = conn.execute("""SELECT p.status, p.payment_date, s.student_classification
                FROM payment p JOIN enrollment e ON e.enrollment_id = p.enrollment_id
                JOIN student s ON e.student_id = s.student_id
                WHERE p.payment_id = %s FOR UPDATE""", (payment_id,)).fetchone()
            if row is None:
                raise ValueError("존재하지 않는 결제 내역입니다.")
            if not status or PAYMENT_TRANSITIONS.get(row["status"]) != status:
                raise ValueError("미납은 완납으로, 완납은 환불로 변경할 수 있습니다.")
            if status == "PAID" and row["student_classification"] == "BLACK":
                raise ValueError("블랙리스트 학생은 결제가 불가합니다.")
            paid_on = validate_date(payment_date) if status == "PAID" else row["payment_date"]
            conn.execute("UPDATE payment SET status = %s, payment_date = %s WHERE payment_id = %s",
                         (status, paid_on, payment_id))
    finally:
        conn.close()


def payment_filters(student_id=None, start_date=None, end_date=None, billing_month=None):
    clauses, values = [], []
    for value, column, operator in ((student_id, 'e.student_id', '='),
                                     (start_date, 'p.payment_date', '>='),
                                     (end_date, 'p.payment_date', '<=')):
        if value is not None and value != '':
            if column == 'p.payment_date':
                value = validate_date(value)
            clauses.append(f"{column} {operator} %s")
            values.append(value)
    if billing_month:
        clauses.append('p.billing_month = %s')
        values.append(normalize_billing_month(billing_month).isoformat())
    if start_date and end_date and start_date > end_date:
        raise ValueError("종료일은 시작일보다 빠를 수 없습니다.")
    return (' WHERE ' + ' AND '.join(clauses) if clauses else ''), values


def list_payments(student_id=None, start_date=None, end_date=None, billing_month=None):
    where, values = payment_filters(student_id, start_date, end_date, billing_month)
    conn = get_conn()
    rows = conn.execute(
        """SELECT p.payment_id, s.name AS student_name, p.course_name,
                  p.course_fee, p.payment_date, p.status, p.billing_month, c.class_name
           FROM payment p
           JOIN enrollment e ON e.enrollment_id = p.enrollment_id
           JOIN student s ON e.student_id = s.student_id
           LEFT JOIN class c ON c.class_id = e.class_id
           """ + where + " ORDER BY p.payment_date DESC, p.payment_id DESC", values
    ).fetchall()
    conn.close()
    return rows


def total_revenue(student_id=None, start_date=None, end_date=None, billing_month=None):
    where, values = payment_filters(student_id, start_date, end_date, billing_month)
    paid_clause = " AND p.status = 'PAID'" if where else " WHERE p.status = 'PAID'"
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(p.course_fee), 0) AS revenue FROM payment p "
            "JOIN enrollment e ON e.enrollment_id = p.enrollment_id" + where + paid_clause, values,
        ).fetchone()
        return int(row["revenue"])
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
    school = (school or "").strip() or None
    if len(name) > 20 or (school and len(school) > 20):
        raise ValueError("학생 이름과 학교는 각각 20자 이하여야 합니다.")
    return name, school, grade, validate_date(admission, True), normalize_contact(contact, student=True), classification


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


def write_student(query, values):
    with closing(get_conn()) as conn, conn:
        result = conn.execute(query, values)
        if result.rowcount != 1:
            raise ValueError("존재하지 않는 학생입니다.")
        return result.lastrowid


def update_student(student_id, name, school, grade, admission, contact, classification):
    values = validate_student(name, school, grade, admission, contact, classification)
    write_student("""UPDATE student SET name=%s, school=%s, grade=%s,
        day_of_admission=%s, contact_number=%s, student_classification=%s WHERE student_id=%s""",
        (*values, student_id))


def delete_mysql_student(student_id):
    """수강 기록이 연결되지 않은 학생을 삭제한다."""
    write_student("DELETE FROM student WHERE student_id = %s", (student_id,))


def update_enrollment_status(enrollment_id, status):
    if status not in ('ACTIVE', 'COMPLETED', 'CANCELED'):
        raise ValueError("올바른 수강 상태를 선택하세요.")
    conn = get_conn()
    try:
        with conn:
            row = conn.execute("""SELECT s.student_classification, e.class_id FROM enrollment e
                JOIN student s ON s.student_id=e.student_id WHERE e.enrollment_id=%s FOR UPDATE""",
                (enrollment_id,)).fetchone()
            if row is None:
                raise ValueError("존재하지 않는 수강 등록입니다.")
            if status == 'ACTIVE' and row['student_classification'] == 'BLACK':
                raise ValueError("블랙리스트 학생의 수강을 활성화할 수 없습니다.")
            if status == "ACTIVE":
                prevent_expired_enrollment(conn, row["class_id"])
            conn.execute("UPDATE enrollment SET status=%s WHERE enrollment_id=%s", (status, enrollment_id))
    finally:
        conn.close()


def list_enrollments_by_student(student_id):
    sync_expired_short_courses()
    conn = get_conn()
    try:
        return conn.execute("""SELECT e.enrollment_id, c.class_name, co.name AS course_name,
            co.fee, e.enrolled_date, e.status FROM enrollment e
            JOIN class c ON c.class_id=e.class_id JOIN course co ON co.course_id=c.course_id
            WHERE e.student_id=%s ORDER BY e.enrollment_id""", (student_id,)).fetchall()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print("MySQL 연결 확인 완료")
    print("학생 수:", len(list_students()))
    print("총 매출:", total_revenue())
