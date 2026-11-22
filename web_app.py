"""로컬 학원 관리 웹 앱. 실행: python3 web_app.py (외부 의존성 없음)."""
import argparse
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from mysql.connector import DataError, IntegrityError

import db

WEB = Path(__file__).resolve().parent / 'web'


def records(rows):
    return [dict(row) for row in rows]


def dispatch(action, data):
    """공개할 업무 함수만 명시적으로 연결한다."""
    if action == 'student.save':
        args = [data.get(k) for k in ('name', 'school', 'grade', 'day_of_admission', 'contact_number', 'student_classification')]
        if data.get('student_id'):
            db.update_student(int(data['student_id']), *args)
        else:
            db.add_student(*args)
    elif action == 'teacher.save':
        args = [data.get('name', ''), data.get('contact_number', '')]
        if data.get('teacher_id'):
            db.update_teacher(int(data['teacher_id']), *args)
        else:
            db.add_teacher(*args)
    elif action == 'course.save':
        args = [data.get('name', ''), data.get('fee', '')]
        if data.get('course_id'):
            db.update_course(int(data['course_id']), *args)
        else:
            db.add_course(*args)
    elif action == 'class.save':
        teacher = int(data['teacher_id']) if data.get('teacher_id') else None
        grade = db.validate_grade(data.get('grade'))
        name = data.get('class_name', '').strip()
        if not name:
            raise ValueError('반 이름은 필수입니다.')
        if data.get('class_id'):
            db.update_class(int(data['class_id']), name, grade, teacher)
        else:
            args = [int(data['course_id']), teacher, grade, name]
            if data.get('kind') == 'short':
                db.add_short_course(*args, data.get('start_date', ''), data.get('end_date', ''))
            else:
                db.add_class(*args)
    elif action == 'enrollment.add':
        db.add_enrollment(int(data['student_id']), int(data['class_id']), data.get('enrolled_date', ''))
    elif action == 'enrollment.status':
        db.update_enrollment_status(int(data['enrollment_id']), data.get('status'))
    elif action == 'payment.add':
        db.add_class_payment(int(data['student_id']), int(data['class_id']), data.get('payment_date', ''),
                             data.get('status', 'PAID'), data.get('billing_month'))
    elif action == 'payment.status':
        db.update_payment_status(int(data['payment_id']), data.get('status'), data.get('payment_date'))
    elif action == 'timetable.save':
        if not isinstance(data.get('schedule'), dict):
            raise ValueError('시간표 형식이 올바르지 않습니다.')
        db.save_timetable_by_class(int(data['class_id']), data['schedule'])
    else:
        raise ValueError('지원하지 않는 작업입니다.')


class Handler(BaseHTTPRequestHandler):
    def send(self, status, payload, mime='application/json; charset=utf-8'):
        body = json.dumps(payload, ensure_ascii=False).encode() if mime.startswith('application/json') else payload
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlsplit(self.path)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        try:
            if url.path == '/api/state':
                return self.send(200, {k: records(fn()) for k, fn in (
                    ('students', db.list_students), ('teachers', db.list_teachers),
                    ('courses', db.list_courses), ('classes', db.list_classes),
                    ('enrollments', db.list_enrollments))} | {'grade_levels': db.GRADE_LEVELS})
            if url.path == '/api/payment-targets':
                return self.send(200, records(db.list_payment_targets(q.get('billing_month'), q.get('student_id'))))
            if url.path == '/api/payments':
                rows = records(db.list_payments(q.get('student_id'), q.get('start_date'), q.get('end_date'),
                                                q.get('billing_month')))
                return self.send(200, {'rows': rows, 'total': sum(r['course_fee'] for r in rows if r['status'] == 'PAID')})
            if url.path == '/api/student':
                sid = int(q['id'])
                return self.send(200, {'enrollments': records(db.list_enrollments_by_student(sid)),
                                       'active_classes': records(db.list_active_classes_by_student(sid))})
            if url.path == '/api/class':
                cid = int(q['id'])
                return self.send(200, {'students': records(db.list_students_by_class(cid)),
                                       'timetable': records(db.list_timetable_by_class(cid))})
            files = {'/': ('index.html', 'text/html; charset=utf-8'),
                     '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                     '/style.css': ('style.css', 'text/css; charset=utf-8')}
            if url.path not in files:
                return self.send(404, {'error': '페이지를 찾을 수 없습니다.'})
            name, mime = files[url.path]
            self.send(200, (WEB / name).read_bytes(), mime)
        except (ValueError, KeyError, TypeError) as exc:
            self.send(400, {'error': str(exc)})
        except Exception:
            self.send(500, {'error': '조회 중 오류가 발생했습니다.'})

    def do_POST(self):
        # JSON + same-origin 검사를 통해 다른 사이트의 폼 요청을 차단한다.
        host = self.headers.get('Host', '')
        allowed = {f'localhost:{self.server.server_port}', f'127.0.0.1:{self.server.server_port}'}
        if host not in allowed or self.headers.get('Origin') not in (None, 'http://' + host):
            return self.send(403, {'error': '허용되지 않은 요청입니다.'})
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.send(415, {'error': 'JSON 요청만 허용합니다.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 65536:
                raise ValueError('요청 크기가 올바르지 않습니다.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('요청 형식이 올바르지 않습니다.')
            dispatch(urlsplit(self.path).path.removeprefix('/api/'), data)
            self.send(200, {'ok': True})
        except (ValueError, KeyError, TypeError, OverflowError) as exc:
            # DB의 사용자용 검증 메시지는 그대로 전달한다.
            self.send(400, {'error': str(exc) or '입력값을 확인하세요.'})
        except (DataError, IntegrityError):
            self.send(400, {'error': '연결된 항목이나 중복 등록을 확인하세요.'})
        except Exception:
            self.send(500, {'error': '저장 중 오류가 발생했습니다. 다시 시도하세요.'})


def open_browser(url):
    """브라우저 실행 실패가 서버 실행을 막지 않도록 처리한다."""
    try:
        opened = webbrowser.open(url, new=2)
    except Exception:
        opened = False
    if not opened:
        print(f'브라우저를 자동으로 열지 못했습니다. 직접 접속하세요: {url}', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--no-browser', action='store_true', help='브라우저 자동 열기 생략')
    args = parser.parse_args()
    db.init_db()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'학원 관리 웹: {url}  (종료: Ctrl+C)', flush=True)
    try:
        if not args.no_browser:
            threading.Thread(target=open_browser, args=(url,), daemon=True).start()
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
