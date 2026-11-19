-- =====================================================
-- 샘플 데이터 (발표 시연용)
-- 실행 순서: 부모 테이블 먼저 (teacher, course → class → student → enrollment/payment/timetable/short_course)
-- =====================================================

-- 선생님
INSERT INTO teacher (name, contact_number) VALUES
 ('김민수', '010-1111-2222'),
 ('이수진', '010-3333-4444'),
 ('박정호', '010-5555-6666');

-- 수강과정
INSERT INTO course (name, fee) VALUES
 ('중등 수학 정규반', 250000),
 ('고등 수학 정규반', 320000),
 ('고등 미적분 심화', 400000),
 ('겨울방학 특강', 180000);

-- 반 (course_id, teacher_id, grade, class_name)
INSERT INTO class (course_id, teacher_id, grade, class_name) VALUES
 (1, 1, '중2', '중2-A반'),
 (1, 1, '중3', '중3-B반'),
 (2, 2, '고1', '고1-수학반'),
 (3, 3, '고2', '고2-미적분반'),
 (4, 2, '고3', '겨울특강-고3');

-- 특강(short_course): 5번 반이 특강
INSERT INTO short_course (class_id, start_date, end_date) VALUES
 (5, '2026-12-26', '2027-01-25');

-- 학생
INSERT INTO student (name, school, grade, day_of_admission, contact_number, student_classification) VALUES
 ('홍길동', '숭실중', '중2', '2026-03-02', '010-1000-0001', 'ACTIVE'),
 ('김영희', '숭실중', '중3', '2026-03-05', '010-1000-0002', 'ACTIVE'),
 ('이철수', '숭실고', '고1', '2026-03-10', '010-1000-0003', 'ACTIVE'),
 ('박민지', '상도고', '고2', '2026-04-01', '010-1000-0004', 'ACTIVE'),
 ('최준영', '상도고', '고3', '2026-04-15', '010-1000-0005', 'INACTIVE'),
 ('정블랙', '미상', NULL, '2026-05-01', '010-1000-0006', 'BLACK');

-- 수강 등록 (student_id, class_id, enrolled_date, status)
INSERT INTO enrollment (student_id, class_id, enrolled_date, status) VALUES
 (1, 1, '2026-03-02', 'ACTIVE'),
 (2, 2, '2026-03-05', 'ACTIVE'),
 (3, 3, '2026-03-10', 'ACTIVE'),
 (4, 4, '2026-04-01', 'ACTIVE'),
 (3, 5, '2026-11-20', 'ACTIVE');

-- 시간표 (요일, class_id, start, end)
INSERT INTO timetable (day_of_class, class_id, start_time, end_time) VALUES
 ('MON', 1, '18:00', '20:00'),
 ('WED', 1, '18:00', '20:00'),
 ('TUE', 2, '19:00', '21:00'),
 ('THU', 3, '18:30', '20:30'),
 ('SAT', 4, '10:00', '12:00');

-- 결제 (student_id, course_name, course_fee, payment_date, status)
INSERT INTO payment (student_id, course_name, course_fee, payment_date, status) VALUES
 (1, '중등 수학 정규반', 250000, '2026-03-02', 'PAID'),
 (2, '중등 수학 정규반', 250000, '2026-03-05', 'PAID'),
 (3, '고등 수학 정규반', 320000, '2026-03-10', 'PAID'),
 (4, '고등 미적분 심화', 400000, '2026-04-01', 'PAID'),
 (3, '겨울방학 특강',     180000, '2026-11-20', 'PAID');
