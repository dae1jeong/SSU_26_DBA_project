# SSU_26_DBA_project — 중고등 수학학원 관리 시스템

숭실대학교 데이터베이스응용(2026-2) 팀 프로젝트.
응용프로그램 + 데이터베이스(SQLite)를 통합한 학원 관리 시스템.

## 기술 스택
- **언어:** Python 3 (표준 라이브러리만 사용 — 별도 설치 불필요)
- **데이터베이스:** SQLite (`academy.db` 단일 파일)
- **GUI:** Tkinter (Python 기본 내장)

> 외부 패키지가 없어 가상환경 없이 기본 Python으로 바로 실행됩니다.

## 실행 방법
```bash
python app.py
```
- 최초 실행 시 `academy.db`가 없으면 `schema_sqlite.sql` + `seed.sql`로 자동 생성됩니다.
- 창이 뜨면 학생관리 / 반관리 / 수강등록 / 결제 탭에서 조작할 수 있습니다.

## 파일 구성
| 파일 | 설명 |
|---|---|
| `app.py` | Tkinter GUI (프론트엔드) |
| `db.py` | DB 연결 + CRUD 함수 (백엔드) |
| `schema_sqlite.sql` | 테이블 생성 스크립트 (SQLite용) |
| `seed.sql` | 시연용 샘플 데이터 |
| `academy.db` | 통합 데이터베이스 파일 (실행 시 생성) |

## 데이터 모델 (8개 테이블)
student · enrollment · class · course · teacher · timetable · short_course · payment

- 물리 모델 원본은 **MySQL 기준**으로 설계되었고, 배포/실행용으로 **SQLite로 변환**했습니다.
  - `ENUM` → `CHECK(col IN (...))`
  - `AUTO_INCREMENT` → `INTEGER PRIMARY KEY AUTOINCREMENT`
  - `INT UNSIGNED` → `INTEGER + CHECK(> 0)`
  - `DATE/TIME` → `TEXT` ('YYYY-MM-DD' / 'HH:MM')

## 구현된 기능 (초안)
- 학생 등록 / 목록 / 분류(ACTIVE·INACTIVE·BLACK)
- 반 생성 / 목록 (과정·선생님 연결)
- 수강 등록 / 목록 (블랙리스트 학생 자동 차단)
- 결제 입력 / 목록 / 총 매출 (블랙리스트 학생 자동 차단)

## 향후 보완 (팀 분담)
- UI 디자인/레이아웃 개선, 수정·삭제 기능
- 입력값 검증 강화 (날짜/전화번호 형식, 중복 체크)
- 검색·필터, 기간별 매출 통계, 시간표 관리 화면
- 예외 처리 메시지 정리

## 브랜치 전략
- `main`: 안정 버전
- `dev`: 개발 작업용
