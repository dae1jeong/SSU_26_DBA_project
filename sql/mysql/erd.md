# 학원 관리 시스템 MySQL ERD

```mermaid
erDiagram
    COURSE ||--o{ CLASS : "과정"
    TEACHER o|--o{ CLASS : "담당"
    STUDENT ||--o{ ENROLLMENT : "수강"
    CLASS ||--o{ ENROLLMENT : "등록 반"
    CLASS ||--o{ TIMETABLE : "요일별 수업"
    CLASS ||--o| SHORT_COURSE : "특강 기간"
    STUDENT ||--o{ PAYMENT : "결제 학생"
    ENROLLMENT ||--o{ PAYMENT : "월별 청구"
    STUDENT {
        BIGINT student_id PK
        ENUM grade "초1~초6, 중1~중3, 고1~고3, 미지정"
        VARCHAR contact_number "휴대전화"
    }
    TEACHER {
        BIGINT teacher_id PK
        VARCHAR contact_number "국내 전화번호"
    }
    COURSE {
        BIGINT course_id PK
    }
    CLASS {
        BIGINT class_id PK
        BIGINT course_id FK
        BIGINT teacher_id FK "미지정 가능"
        ENUM grade "초1~초6, 중1~중3, 고1~고3, 미지정"
    }
    ENROLLMENT {
        BIGINT enrollment_id PK
        BIGINT student_id FK
        BIGINT class_id FK
        ENUM status "ACTIVE, COMPLETED, CANCELED"
    }
    PAYMENT {
        BIGINT payment_id PK
        BIGINT student_id FK
        BIGINT enrollment_id FK
        DATE billing_month "매월 1일로 저장"
        DATE payment_date "미납이면 미지정"
        ENUM status "PAID, UNPAID, REFUNDED"
    }
    TIMETABLE {
        BIGINT class_id PK, FK
        ENUM day_of_class PK
    }
    SHORT_COURSE {
        BIGINT class_id PK, FK
        DATE start_date
        DATE end_date
    }
```

- 수강은 같은 학생과 반의 조합에 한 행을 저장합니다.
- 결제는 같은 수강과 청구월의 조합에 한 행을 저장합니다.
- 특강 종료일 다음 날부터 해당 반의 `ACTIVE` 수강을 `COMPLETED`로 갱신합니다.
