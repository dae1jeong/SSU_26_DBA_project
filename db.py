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
import sqlite3

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
    conn = get_conn()
    conn.execute("INSERT INTO course (name, fee) VALUES (?, ?)", (name, fee))
    conn.commit()
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


def list_classes():
    """반 목록 + 과정명/선생님명을 JOIN해서 함께 반환."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT c.class_id, c.class_name, c.grade,
                  co.name AS course_name,
                  t.name  AS teacher_name
           FROM class c
           LEFT JOIN course  co ON c.course_id  = co.course_id
           LEFT JOIN teacher t  ON c.teacher_id = t.teacher_id
           ORDER BY c.class_id"""
    ).fetchall()
    conn.close()
    return rows


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
