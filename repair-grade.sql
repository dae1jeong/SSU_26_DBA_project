-- Run against the empty database before importing seed.sql.
SET NAMES utf8mb4;
USE math_academy;

ALTER TABLE student MODIFY COLUMN grade ENUM(
  '초1','초2','초3','초4','초5','초6',
  '중1','중2','중3','고1','고2','고3'
) NULL COMMENT '학년 (초1~초6, 중1~중3, 고1~고3)';

ALTER TABLE class MODIFY COLUMN grade ENUM(
  '초1','초2','초3','초4','초5','초6',
  '중1','중2','중3','고1','고2','고3'
) NULL COMMENT '대상 학년 (초1~초6, 중1~중3, 고1~고3)';

SHOW COLUMNS FROM student LIKE 'grade';
SHOW COLUMNS FROM class LIKE 'grade';
