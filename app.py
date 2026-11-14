# -*- coding: utf-8 -*-
"""
app.py - Tkinter GUI (프론트엔드)
중고등 수학학원 관리 시스템

실행: python app.py
- 실행 시 academy.db가 없으면 자동 생성(스키마 + 샘플데이터).
- 탭: 학생관리 / 반관리 / 수강등록 / 결제 / 조회
- 모든 DB 작업은 db.py 함수를 통해서만 수행 (화면/DB 분리)

[팀원 보완 포인트]
- UI 스타일/레이아웃 개선, 입력 폼 검증 강화
- 수정/삭제 버튼 추가, 검색 필터, 통계 화면
- 날짜 피커, 콤보박스 자동 새로고침 등
"""

import tkinter as tk
from tkinter import ttk, messagebox

import db


def setup_style(root):
    """맥 다크모드에서 위젯이 안 보이는 문제 방지 — 밝은 테마 강제 지정."""
    root.configure(bg="#f0f0f0")
    style = ttk.Style()
    try:
        style.theme_use("clam")   # 'default'/'aqua'보다 색 지정이 잘 먹는 테마
    except Exception:
        pass
    style.configure(".", background="#f0f0f0", foreground="#000000", fieldbackground="#ffffff")
    style.configure("TFrame", background="#f0f0f0")
    style.configure("TLabel", background="#f0f0f0", foreground="#000000")
    style.configure("TLabelframe", background="#f0f0f0", foreground="#000000")
    style.configure("TLabelframe.Label", background="#f0f0f0", foreground="#000000")
    style.configure("TButton", background="#e1e1e1", foreground="#000000")
    style.configure("TNotebook", background="#f0f0f0")
    style.configure("TNotebook.Tab", background="#d9d9d9", foreground="#000000", padding=(12, 6))
    style.map("TNotebook.Tab", background=[("selected", "#ffffff")])
    style.configure("TEntry", fieldbackground="#ffffff", foreground="#000000")
    style.configure("TCombobox", fieldbackground="#ffffff", foreground="#000000")
    style.configure("Treeview", background="#ffffff", foreground="#000000",
                    fieldbackground="#ffffff", rowheight=24)
    style.configure("Treeview.Heading", background="#d9d9d9", foreground="#000000")


class AcademyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("중고등 수학학원 관리 시스템 (초안)")
        self.geometry("900x600")
        setup_style(self)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_student = StudentTab(nb)
        self.tab_class = ClassTab(nb)
        self.tab_enroll = EnrollTab(nb)
        self.tab_payment = PaymentTab(nb)

        nb.add(self.tab_student, text="학생 관리")
        nb.add(self.tab_class, text="반 관리")
        nb.add(self.tab_enroll, text="수강 등록")
        nb.add(self.tab_payment, text="결제")

        # 탭 전환 시 데이터 새로고침
        nb.bind("<<NotebookTabChanged>>", lambda e: self.refresh_current(nb))

    def refresh_current(self, nb):
        current = nb.nametowidget(nb.select())
        if hasattr(current, "refresh"):
            current.refresh()


# ------------------------------------------------------------
# 학생 관리 탭
# ------------------------------------------------------------
class StudentTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        # 입력 폼
        form = ttk.LabelFrame(self, text="학생 등록")
        form.pack(fill="x", padx=8, pady=8)

        self.e_name = self._row(form, "이름", 0)
        self.e_school = self._row(form, "학교", 1)
        self.e_grade = self._row(form, "학년", 2)
        self.e_date = self._row(form, "등록일(YYYY-MM-DD)", 3)
        self.e_contact = self._row(form, "연락처", 4)

        ttk.Label(form, text="분류").grid(row=5, column=0, sticky="w", padx=6, pady=4)
        self.cb_cls = ttk.Combobox(form, values=["ACTIVE", "INACTIVE", "BLACK"], state="readonly")
        self.cb_cls.set("ACTIVE")
        self.cb_cls.grid(row=5, column=1, sticky="we", padx=6, pady=4)

        ttk.Button(form, text="등록", command=self.on_add).grid(row=6, column=0, columnspan=2, pady=6)
        form.columnconfigure(1, weight=1)

        # 목록
        cols = ("id", "name", "school", "grade", "date", "contact", "cls")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for c, t, w in [
            ("id", "ID", 40), ("name", "이름", 90), ("school", "학교", 90),
            ("grade", "학년", 50), ("date", "등록일", 100),
            ("contact", "연락처", 130), ("cls", "분류", 80),
        ]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)

        self.refresh()

    def _row(self, parent, label, r):
        ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", padx=6, pady=4)
        e = ttk.Entry(parent)
        e.grid(row=r, column=1, sticky="we", padx=6, pady=4)
        return e

    def on_add(self):
        name = self.e_name.get().strip()
        if not name:
            messagebox.showwarning("입력 오류", "이름은 필수입니다.")
            return
        try:
            grade = self.e_grade.get().strip()
            grade = int(grade) if grade else None
            db.add_student(
                name, self.e_school.get().strip() or None, grade,
                self.e_date.get().strip() or None, self.e_contact.get().strip() or None,
                self.cb_cls.get(),
            )
            messagebox.showinfo("완료", f"'{name}' 학생이 등록되었습니다.")
            for e in (self.e_name, self.e_school, self.e_grade, self.e_date, self.e_contact):
                e.delete(0, "end")
            self.refresh()
        except Exception as ex:
            messagebox.showerror("오류", str(ex))

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in db.list_students():
            self.tree.insert("", "end", values=(
                r["student_id"], r["name"], r["school"], r["grade"],
                r["day_of_admission"], r["contact_number"], r["student_classification"],
            ))


# ------------------------------------------------------------
# 반 관리 탭
# ------------------------------------------------------------
class ClassTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        form = ttk.LabelFrame(self, text="반 생성")
        form.pack(fill="x", padx=8, pady=8)

        ttk.Label(form, text="과정").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.cb_course = ttk.Combobox(form, state="readonly")
        self.cb_course.grid(row=0, column=1, sticky="we", padx=6, pady=4)

        ttk.Label(form, text="선생님").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.cb_teacher = ttk.Combobox(form, state="readonly")
        self.cb_teacher.grid(row=1, column=1, sticky="we", padx=6, pady=4)

        ttk.Label(form, text="학년").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        self.e_grade = ttk.Entry(form)
        self.e_grade.grid(row=2, column=1, sticky="we", padx=6, pady=4)

        ttk.Label(form, text="반 이름").grid(row=3, column=0, sticky="w", padx=6, pady=4)
        self.e_name = ttk.Entry(form)
        self.e_name.grid(row=3, column=1, sticky="we", padx=6, pady=4)

        ttk.Button(form, text="반 생성", command=self.on_add).grid(row=4, column=0, columnspan=2, pady=6)
        form.columnconfigure(1, weight=1)

        cols = ("id", "name", "grade", "course", "teacher")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for c, t, w in [
            ("id", "ID", 40), ("name", "반 이름", 120), ("grade", "학년", 50),
            ("course", "과정", 160), ("teacher", "선생님", 100),
        ]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)

        self.courses = []
        self.teachers = []
        self.refresh()

    def on_add(self):
        if not self.cb_course.current() >= 0 or not self.e_name.get().strip():
            messagebox.showwarning("입력 오류", "과정과 반 이름은 필수입니다.")
            return
        try:
            course_id = self.courses[self.cb_course.current()]["course_id"]
            teacher_id = None
            if self.cb_teacher.current() >= 0:
                teacher_id = self.teachers[self.cb_teacher.current()]["teacher_id"]
            grade = self.e_grade.get().strip()
            grade = int(grade) if grade else None
            db.add_class(course_id, teacher_id, grade, self.e_name.get().strip())
            messagebox.showinfo("완료", "반이 생성되었습니다.")
            self.e_name.delete(0, "end")
            self.e_grade.delete(0, "end")
            self.refresh()
        except Exception as ex:
            messagebox.showerror("오류", str(ex))

    def refresh(self):
        self.courses = list(db.list_courses())
        self.teachers = list(db.list_teachers())
        self.cb_course["values"] = [f'{c["name"]} ({c["fee"]}원)' for c in self.courses]
        self.cb_teacher["values"] = [t["name"] for t in self.teachers]
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in db.list_classes():
            self.tree.insert("", "end", values=(
                r["class_id"], r["class_name"], r["grade"], r["course_name"], r["teacher_name"],
            ))


# ------------------------------------------------------------
# 수강 등록 탭
# ------------------------------------------------------------
class EnrollTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        form = ttk.LabelFrame(self, text="수강 등록 (블랙리스트 학생은 자동 차단)")
        form.pack(fill="x", padx=8, pady=8)

        ttk.Label(form, text="학생").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.cb_student = ttk.Combobox(form, state="readonly")
        self.cb_student.grid(row=0, column=1, sticky="we", padx=6, pady=4)

        ttk.Label(form, text="반").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.cb_class = ttk.Combobox(form, state="readonly")
        self.cb_class.grid(row=1, column=1, sticky="we", padx=6, pady=4)

        ttk.Label(form, text="등록일(YYYY-MM-DD)").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        self.e_date = ttk.Entry(form)
        self.e_date.grid(row=2, column=1, sticky="we", padx=6, pady=4)

        ttk.Button(form, text="수강 등록", command=self.on_add).grid(row=3, column=0, columnspan=2, pady=6)
        form.columnconfigure(1, weight=1)

        cols = ("id", "student", "class", "date", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for c, t, w in [
            ("id", "ID", 40), ("student", "학생", 100), ("class", "반", 120),
            ("date", "등록일", 100), ("status", "상태", 90),
        ]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)

        self.students = []
        self.classes = []
        self.refresh()

    def on_add(self):
        if self.cb_student.current() < 0 or self.cb_class.current() < 0:
            messagebox.showwarning("입력 오류", "학생과 반을 선택하세요.")
            return
        try:
            sid = self.students[self.cb_student.current()]["student_id"]
            cid = self.classes[self.cb_class.current()]["class_id"]
            date = self.e_date.get().strip() or "2026-11-14"
            db.add_enrollment(sid, cid, date)
            messagebox.showinfo("완료", "수강 등록되었습니다.")
            self.refresh()
        except Exception as ex:
            messagebox.showerror("오류", str(ex))

    def refresh(self):
        self.students = list(db.list_students())
        self.classes = list(db.list_classes())
        self.cb_student["values"] = [f'{s["name"]} ({s["student_classification"]})' for s in self.students]
        self.cb_class["values"] = [c["class_name"] for c in self.classes]
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in db.list_enrollments():
            self.tree.insert("", "end", values=(
                r["enrollment_id"], r["student_name"], r["class_name"], r["enrolled_date"], r["status"],
            ))


# ------------------------------------------------------------
# 결제 탭
# ------------------------------------------------------------
class PaymentTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        form = ttk.LabelFrame(self, text="결제 입력 (블랙리스트 학생은 자동 차단)")
        form.pack(fill="x", padx=8, pady=8)

        ttk.Label(form, text="학생").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.cb_student = ttk.Combobox(form, state="readonly")
        self.cb_student.grid(row=0, column=1, sticky="we", padx=6, pady=4)

        ttk.Label(form, text="과정명").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.e_course = ttk.Entry(form)
        self.e_course.grid(row=1, column=1, sticky="we", padx=6, pady=4)

        ttk.Label(form, text="금액").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        self.e_fee = ttk.Entry(form)
        self.e_fee.grid(row=2, column=1, sticky="we", padx=6, pady=4)

        ttk.Label(form, text="결제일(YYYY-MM-DD)").grid(row=3, column=0, sticky="w", padx=6, pady=4)
        self.e_date = ttk.Entry(form)
        self.e_date.grid(row=3, column=1, sticky="we", padx=6, pady=4)

        ttk.Button(form, text="결제 등록", command=self.on_add).grid(row=4, column=0, columnspan=2, pady=6)
        form.columnconfigure(1, weight=1)

        self.lbl_total = ttk.Label(self, text="총 매출: -")
        self.lbl_total.pack(anchor="e", padx=12)

        cols = ("id", "student", "course", "fee", "date")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=11)
        for c, t, w in [
            ("id", "ID", 40), ("student", "학생", 100), ("course", "과정명", 160),
            ("fee", "금액", 90), ("date", "결제일", 100),
        ]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)

        self.students = []
        self.refresh()

    def on_add(self):
        if self.cb_student.current() < 0:
            messagebox.showwarning("입력 오류", "학생을 선택하세요.")
            return
        try:
            sid = self.students[self.cb_student.current()]["student_id"]
            fee = int(self.e_fee.get().strip())
            db.add_payment(sid, self.e_course.get().strip(), fee, self.e_date.get().strip() or "2026-11-14")
            messagebox.showinfo("완료", "결제가 등록되었습니다.")
            self.e_course.delete(0, "end")
            self.e_fee.delete(0, "end")
            self.refresh()
        except ValueError as ve:
            messagebox.showerror("오류", str(ve))
        except Exception as ex:
            messagebox.showerror("오류", f"금액은 숫자로 입력하세요.\n{ex}")

    def refresh(self):
        self.students = list(db.list_students())
        self.cb_student["values"] = [f'{s["name"]} ({s["student_classification"]})' for s in self.students]
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in db.list_payments():
            self.tree.insert("", "end", values=(
                r["payment_id"], r["student_name"], r["course_name"], r["course_fee"], r["payment_date"],
            ))
        self.lbl_total.config(text=f"총 매출: {db.total_revenue():,}원")


if __name__ == "__main__":
    db.init_db()           # academy.db 없으면 자동 생성(+샘플)
    app = AcademyApp()
    app.mainloop()
