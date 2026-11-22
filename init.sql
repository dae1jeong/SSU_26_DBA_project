-- ============================================================================
-- 초중고등 수학학원 관리 시스템 (Math Academy Management System)
-- 물리 데이터베이스 DDL 스크립트 (MySQL 8.0.16+ 기준, v6)
-- 반영 사항:
--   월별 청구: billing_month는 해당 월 1일로 저장, 수강등록 및 월별 청구 중복 방지
--   1. 학년(grade) ENUM 적용: 초1~초6, 중1~중3, 고1~고3 (student, class)
--   2. 전화번호(contact_number) 하이픈 포맷 검증 제약조건 추가 (student, teacher)
--   3. 존재하지 않는 날짜(예: '2026-11-60') 입력 차단 (STRICT 모드 + 날짜 포맷/유효성 검사)
--   4. 아이디(PK) 수정 차단 및 아이디 제외 나머지 속성 수정 허용 (BEFORE UPDATE 트리거)
--   5. 방학특강(short_course) 종료 시 수강 상태(enrollment.status) 'COMPLETED' 전환
--   v6: payment.course_fee NOT NULL, 학생/수강등록 삭제 RESTRICT
--   수업 시간 및 특강 기간 CHECK 유지, enrollment의 student_id 단일 인덱스 미생성
-- ============================================================================

SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS math_academy
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE math_academy;

-- 빈 MySQL 시연 DB에 최초 1회 적용합니다.

-- 엄격한 날짜/데이터 검증을 위한 SQL 모드 설정 (존재하지 않는 날짜 입력 차단)
SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- ----------------------------------------------------------------------------
-- 1. 학생 (student)
-- ----------------------------------------------------------------------------
CREATE TABLE student (
    student_id             BIGINT      NOT NULL AUTO_INCREMENT COMMENT '학생 아이디 (수정 불가)',
    name                   VARCHAR(20) NOT NULL                COMMENT '이름',
    school                 VARCHAR(20) NULL                    COMMENT '학교',
    grade                  ENUM(
                               '초1', '초2', '초3', '초4', '초5', '초6',
                               '중1', '중2', '중3',
                               '고1', '고2', '고3'
                           )           NULL                    COMMENT '학년 (초1~초6, 중1~중3, 고1~고3)',
    day_of_admission       DATE        NULL                    COMMENT '최초 등록 일자',
    contact_number         VARCHAR(20) NULL                    COMMENT '학부모 전화번호 (하이픈 필수)',
    student_classification ENUM('BLACK', 'ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE' COMMENT '학생 분류 상태',
    PRIMARY KEY (student_id),
    INDEX idx_student_name (name),
    INDEX idx_student_classification (student_classification),
    CONSTRAINT chk_student_contact_hyphen
        CHECK (contact_number IS NULL OR contact_number REGEXP '^01[0-9]-[0-9]{3,4}-[0-9]{4}$')
) ENGINE=InnoDB COMMENT='학생 정보';

-- ----------------------------------------------------------------------------
-- 2. 수강 과정 (course)
-- ----------------------------------------------------------------------------
CREATE TABLE course (
    course_id BIGINT       NOT NULL AUTO_INCREMENT COMMENT '수강 과정 아이디 (수정 불가)',
    name      VARCHAR(20)  NOT NULL                COMMENT '수강 과정명',
    fee       INT UNSIGNED NOT NULL                COMMENT '기준 수강비 (0원 이상)',
    PRIMARY KEY (course_id),
    CONSTRAINT chk_course_fee CHECK (fee >= 0)
) ENGINE=InnoDB COMMENT='수강 과정 정보';

-- ----------------------------------------------------------------------------
-- 3. 선생님 (teacher)
-- ----------------------------------------------------------------------------
CREATE TABLE teacher (
    teacher_id     BIGINT      NOT NULL AUTO_INCREMENT COMMENT '선생님 아이디 (수정 불가)',
    name           VARCHAR(20) NOT NULL                COMMENT '이름',
    contact_number VARCHAR(20) NULL                    COMMENT '연락처 (하이픈 필수)',
    PRIMARY KEY (teacher_id),
    CONSTRAINT chk_teacher_contact_hyphen
        CHECK (contact_number IS NULL OR contact_number REGEXP '^0[0-9]{1,2}-[0-9]{3,4}-[0-9]{4}$')
) ENGINE=InnoDB COMMENT='선생님 정보';

-- ----------------------------------------------------------------------------
-- 4. 반 (class)
-- ----------------------------------------------------------------------------
CREATE TABLE class (
    class_id   BIGINT      NOT NULL AUTO_INCREMENT COMMENT '반 아이디 (수정 불가)',
    course_id  BIGINT      NOT NULL                COMMENT '수강 과정 아이디 (FK)',
    teacher_id BIGINT      NULL                    COMMENT '담당 선생님 아이디 (FK)',
    grade      ENUM(
                   '초1', '초2', '초3', '초4', '초5', '초6',
                   '중1', '중2', '중3',
                   '고1', '고2', '고3'
               )           NULL                    COMMENT '대상 학년 (초1~초6, 중1~중3, 고1~고3)',
    class_name VARCHAR(20) NOT NULL                COMMENT '반 이름',
    PRIMARY KEY (class_id),
    INDEX idx_class_course_id (course_id),
    INDEX idx_class_teacher_id (teacher_id),
    CONSTRAINT fk_class_course
        FOREIGN KEY (course_id) REFERENCES course (course_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_class_teacher
        FOREIGN KEY (teacher_id) REFERENCES teacher (teacher_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='개설 반 정보';

-- ----------------------------------------------------------------------------
-- 5. 학생-반 수강등록 (enrollment)
-- ----------------------------------------------------------------------------
CREATE TABLE enrollment (
    enrollment_id BIGINT NOT NULL AUTO_INCREMENT COMMENT '수강등록 아이디 (수정 불가)',
    student_id    BIGINT NOT NULL                COMMENT '학생 아이디 (FK)',
    class_id      BIGINT NOT NULL                COMMENT '반 아이디 (FK)',
    enrolled_date DATE   NOT NULL                COMMENT '수강 신청일',
    status        ENUM('ACTIVE', 'COMPLETED', 'CANCELED') NOT NULL DEFAULT 'ACTIVE' COMMENT '수강 상태 (특강 종료 시 COMPLETED 전환)',
    PRIMARY KEY (enrollment_id),
    UNIQUE KEY uq_enrollment_student_class (student_id, class_id),
    INDEX idx_enrollment_class_id (class_id),
    CONSTRAINT fk_enrollment_student
        FOREIGN KEY (student_id) REFERENCES student (student_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_enrollment_class
        FOREIGN KEY (class_id) REFERENCES class (class_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB COMMENT='학생별 반 수강등록 내역';

-- ----------------------------------------------------------------------------
-- 6. 결제 (payment)
-- ----------------------------------------------------------------------------
CREATE TABLE payment (
    payment_id    BIGINT       NOT NULL AUTO_INCREMENT COMMENT '결제 아이디 (수정 불가)',
    enrollment_id BIGINT       NOT NULL                COMMENT '수강등록 아이디 (FK)',
    billing_month DATE         NOT NULL                COMMENT '청구 대상 월 (해당 월 1일, 예: 2026-11-01)',
    course_name   VARCHAR(20)  NOT NULL                COMMENT '결제 당시 수강 과정명(스냅샷)',
    course_fee    INT UNSIGNED NOT NULL                COMMENT '결제 수강비(스냅샷)',
    payment_date  DATE         NULL                    COMMENT '결제일',
    status        ENUM('PAID', 'UNPAID', 'REFUNDED') NOT NULL DEFAULT 'UNPAID' COMMENT '결제 상태',
    PRIMARY KEY (payment_id),
    UNIQUE KEY uq_payment_enrollment_billing_month (enrollment_id, billing_month),
    INDEX idx_payment_billing_month (billing_month),
    INDEX idx_payment_date (payment_date),
    CONSTRAINT chk_payment_course_fee CHECK (course_fee >= 0),
    CONSTRAINT chk_payment_billing_month CHECK (DAYOFMONTH(billing_month) = 1),
    CONSTRAINT chk_payment_status_date CHECK ((status = 'UNPAID') = (payment_date IS NULL)),
    CONSTRAINT fk_payment_enrollment
        FOREIGN KEY (enrollment_id) REFERENCES enrollment (enrollment_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB COMMENT='수강료 결제 내역';

-- ----------------------------------------------------------------------------
-- 7. 시간표 (timetable)
-- ----------------------------------------------------------------------------
CREATE TABLE timetable (
    day_of_class ENUM('MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN') NOT NULL COMMENT '수업 요일',
    class_id     BIGINT NOT NULL COMMENT '반 아이디 (PK, FK)',
    start_time   TIME   NOT NULL COMMENT '시작 시각',
    end_time     TIME   NOT NULL COMMENT '종료 시각',
    PRIMARY KEY (day_of_class, class_id),
    INDEX idx_timetable_class_id (class_id),
    CONSTRAINT chk_timetable_time_order CHECK (start_time < end_time),
    CONSTRAINT fk_timetable_class
        FOREIGN KEY (class_id) REFERENCES class (class_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='반별 요일/시간표 정보';

-- ----------------------------------------------------------------------------
-- 8. 특강 (short_course)
-- ----------------------------------------------------------------------------
CREATE TABLE short_course (
    class_id   BIGINT NOT NULL COMMENT '반 아이디 (PK, FK)',
    start_date DATE   NOT NULL COMMENT '특강 시작 날짜',
    end_date   DATE   NOT NULL COMMENT '특강 종료 날짜',
    PRIMARY KEY (class_id),
    CONSTRAINT chk_short_course_date_order CHECK (start_date <= end_date),
    CONSTRAINT fk_short_course_class
        FOREIGN KEY (class_id) REFERENCES class (class_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='특강 반 기간 정보';

-- ----------------------------------------------------------------------------
-- 9. 트리거 / 프로시저 / 이벤트
-- ----------------------------------------------------------------------------
DELIMITER $$

-- 9-1. 아이디(PK) 수정 차단 (아이디 제외 나머지 속성만 수정 가능)
CREATE TRIGGER trg_student_prevent_pk_update
BEFORE UPDATE ON student
FOR EACH ROW
BEGIN
    IF NEW.student_id <> OLD.student_id THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '학생 아이디(student_id)는 수정할 수 없습니다.';
    END IF;
END$$

CREATE TRIGGER trg_course_prevent_pk_update
BEFORE UPDATE ON course
FOR EACH ROW
BEGIN
    IF NEW.course_id <> OLD.course_id THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '수강 과정 아이디(course_id)는 수정할 수 없습니다.';
    END IF;
END$$

CREATE TRIGGER trg_teacher_prevent_pk_update
BEFORE UPDATE ON teacher
FOR EACH ROW
BEGIN
    IF NEW.teacher_id <> OLD.teacher_id THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '선생님 아이디(teacher_id)는 수정할 수 없습니다.';
    END IF;
END$$

CREATE TRIGGER trg_class_prevent_pk_update
BEFORE UPDATE ON class
FOR EACH ROW
BEGIN
    IF NEW.class_id <> OLD.class_id THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '반 아이디(class_id)는 수정할 수 없습니다.';
    END IF;
END$$

CREATE TRIGGER trg_enrollment_prevent_pk_update
BEFORE UPDATE ON enrollment
FOR EACH ROW
BEGIN
    IF NEW.enrollment_id <> OLD.enrollment_id THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '수강등록 아이디(enrollment_id)는 수정할 수 없습니다.';
    END IF;
END$$

CREATE TRIGGER trg_payment_prevent_pk_update
BEFORE UPDATE ON payment
FOR EACH ROW
BEGIN
    IF NEW.payment_id <> OLD.payment_id THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '결제 아이디(payment_id)는 수정할 수 없습니다.';
    END IF;
END$$

CREATE TRIGGER trg_short_course_prevent_pk_update
BEFORE UPDATE ON short_course
FOR EACH ROW
BEGIN
    IF NEW.class_id <> OLD.class_id THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '특강 반 아이디(class_id)는 수정할 수 없습니다.';
    END IF;
END$$

-- 9-2. 방학특강 종료(end_date < CURDATE()) 시 해당 반의 수강 상태(enrollment.status)를 'COMPLETED'로 변경
CREATE PROCEDURE sp_sync_expired_short_courses()
BEGIN
    UPDATE enrollment e
    INNER JOIN short_course sc ON e.class_id = sc.class_id
    SET e.status = 'COMPLETED'
    WHERE sc.end_date < CURDATE()
      AND e.status = 'ACTIVE';
END$$

CREATE TRIGGER trg_short_course_insert_sync
AFTER INSERT ON short_course
FOR EACH ROW
BEGIN
    IF NEW.end_date < CURDATE() THEN
        UPDATE enrollment
        SET status = 'COMPLETED'
        WHERE class_id = NEW.class_id
          AND status = 'ACTIVE';
    END IF;
END$$

CREATE TRIGGER trg_short_course_update_sync
AFTER UPDATE ON short_course
FOR EACH ROW
BEGIN
    IF NEW.end_date < CURDATE() THEN
        UPDATE enrollment
        SET status = 'COMPLETED'
        WHERE class_id = NEW.class_id
          AND status = 'ACTIVE';
    END IF;
END$$

CREATE EVENT evt_close_expired_short_courses
ON SCHEDULE EVERY 1 DAY
STARTS (CURRENT_DATE + INTERVAL 1 DAY)
DO
BEGIN
    CALL sp_sync_expired_short_courses();
END$$

DELIMITER ;
