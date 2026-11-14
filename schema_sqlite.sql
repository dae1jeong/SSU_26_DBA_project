-- =====================================================
-- 중고등 수학학원 관리 시스템 - SQLite 스키마
-- (물리 모델 MySQL 기준 → SQLite 변환본)
--   ENUM          -> CHECK(col IN(...))
--   AUTO_INCREMENT-> INTEGER PRIMARY KEY AUTOINCREMENT
--   INT UNSIGNED  -> INTEGER + CHECK(>0)
--   BIGINT        -> INTEGER
-- =====================================================

PRAGMA foreign_keys = ON;   -- SQLite는 FK를 기본 OFF → 반드시 켜야 함

-- 1. 선생님
CREATE TABLE IF NOT EXISTS teacher (
    teacher_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    contact_number  TEXT
);

-- 2. 수강과정
CREATE TABLE IF NOT EXISTS course (
    course_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    fee         INTEGER NOT NULL CHECK (fee > 0)
);

-- 3. 반 (정규)
CREATE TABLE IF NOT EXISTS class (
    class_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id   INTEGER NOT NULL,
    teacher_id  INTEGER,
    grade       INTEGER,
    class_name  TEXT    NOT NULL,
    FOREIGN KEY (course_id)  REFERENCES course(course_id)   ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (teacher_id) REFERENCES teacher(teacher_id) ON DELETE SET NULL ON UPDATE CASCADE
);

-- 4. 학생
CREATE TABLE IF NOT EXISTS student (
    student_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name                    TEXT    NOT NULL,
    school                  TEXT,
    grade                   INTEGER,
    day_of_admission        TEXT,          -- SQLite는 DATE 타입이 없음 → TEXT 'YYYY-MM-DD'
    contact_number          TEXT,
    student_classification  TEXT    NOT NULL DEFAULT 'ACTIVE'
                            CHECK (student_classification IN ('BLACK','ACTIVE','INACTIVE'))
);

-- 5. 학생-반 수강 (교차 테이블, N:M 해소)
CREATE TABLE IF NOT EXISTS enrollment (
    enrollment_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id     INTEGER NOT NULL,
    class_id       INTEGER NOT NULL,
    enrolled_date  TEXT    NOT NULL,
    status         TEXT    NOT NULL DEFAULT 'ACTIVE'
                   CHECK (status IN ('ACTIVE','COMPLETED','CANCELED')),
    UNIQUE (student_id, class_id),
    FOREIGN KEY (student_id) REFERENCES student(student_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (class_id)   REFERENCES class(class_id)     ON DELETE RESTRICT ON UPDATE CASCADE
);

-- 6. 시간표
CREATE TABLE IF NOT EXISTS timetable (
    day_of_class  TEXT    NOT NULL
                  CHECK (day_of_class IN ('MON','TUE','WED','THU','FRI','SAT','SUN')),
    class_id      INTEGER NOT NULL,
    start_time    TEXT    NOT NULL,       -- 'HH:MM'
    end_time      TEXT    NOT NULL,
    PRIMARY KEY (day_of_class, class_id),
    FOREIGN KEY (class_id) REFERENCES class(class_id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- 7. 특강
CREATE TABLE IF NOT EXISTS short_course (
    class_id    INTEGER PRIMARY KEY,
    start_date  TEXT    NOT NULL,
    end_date    TEXT    NOT NULL,
    FOREIGN KEY (class_id) REFERENCES class(class_id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- 8. 결제
CREATE TABLE IF NOT EXISTS payment (
    payment_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL,
    course_name   TEXT    NOT NULL,
    course_fee    INTEGER NOT NULL CHECK (course_fee > 0),
    payment_date  TEXT    NOT NULL,
    FOREIGN KEY (student_id) REFERENCES student(student_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- 조회 성능 인덱스
CREATE INDEX IF NOT EXISTS idx_payment_date           ON payment(payment_date);
CREATE INDEX IF NOT EXISTS idx_student_classification ON student(student_classification);
CREATE INDEX IF NOT EXISTS idx_enrollment_class       ON enrollment(class_id);
CREATE INDEX IF NOT EXISTS idx_enrollment_student     ON enrollment(student_id);
