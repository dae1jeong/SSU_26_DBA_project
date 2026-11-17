# -*- coding: utf-8 -*-
"""
app.py - Tkinter GUI (프론트엔드)
중고등 수학학원 관리 시스템

실행: python app.py
- 실행 시 academy.db가 없으면 자동 생성(스키마 + 샘플데이터).
- 탭: 학생 관리 / 수강 과정 관리 / 반 관리 / 수강 등록 / 결제
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
    # 테마의 X 표시 대신 직접 그린 체크 표시를 사용한다 (키보드 조작은 ttk 유지).
    unchecked = tk.PhotoImage(master=root, width=20, height=20)
    checked = tk.PhotoImage(master=root, width=20, height=20)
    for icon in (unchecked, checked):
        icon.put("#777777", to=(1, 1, 19, 19))
        icon.put("#ffffff", to=(2, 2, 18, 18))
    for x, y in ((4, 9), (5, 10), (6, 11), (7, 12), (8, 11),
                 (9, 10), (10, 9), (11, 8), (12, 7), (13, 6), (14, 5)):
        checked.put("#16723b", to=(x, y, x + 2, y + 2))
    root.timetable_check_images = (unchecked, checked)
    style.element_create("Timetable.indicator", "image", unchecked, ("selected", checked))
    style.layout("Timetable.TCheckbutton", [
        ("Checkbutton.padding", {"sticky": "nswe", "children": [
            ("Checkbutton.focus", {"sticky": "nswe", "children": [
                ("Timetable.indicator", {"side": "left", "sticky": ""}),
                ("Checkbutton.label", {"side": "left", "sticky": "nswe"}),
            ]}),
        ]}),
    ])


class AcademyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("중고등 수학학원 관리 시스템 (초안)")
        self.geometry("900x600")
        setup_style(self)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_student = StudentTab(nb)
        self.tab_course = CourseTab(nb)
        self.tab_class = ClassTab(nb)
        self.tab_enroll = EnrollTab(nb)
        self.tab_payment = PaymentTab(nb)

        nb.add(self.tab_student, text="학생 관리")
        nb.add(self.tab_course, text="수강 과정 관리")
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
        ttk.Label(self, text="목록의 분류 칸을 클릭하면 학생 상태를 변경할 수 있습니다.").pack(anchor="w", padx=8)
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for c, t, w in [
            ("id", "ID", 40), ("name", "이름", 90), ("school", "학교", 90),
            ("grade", "학년", 50), ("date", "등록일", 100),
            ("contact", "연락처", 130), ("cls", "분류", 80),
        ]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree.bind("<ButtonRelease-1>", self.on_classification_click)

        self.refresh()

    def on_classification_click(self, event):
        if self.tree.identify_region(event.x, event.y) != "cell":
            return
        if self.tree.identify_column(event.x) != "#7":
            return
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        student_id = int(self.tree.set(item, "id"))
        current = self.tree.set(item, "cls")
        menu = tk.Menu(self, tearoff=False)
        selected = tk.StringVar(value=current)
        for classification in ("ACTIVE", "INACTIVE", "BLACK"):
            menu.add_radiobutton(
                label=classification, variable=selected, value=classification,
                command=lambda value=classification: self.change_classification(item, student_id, value),
            )
        # 메뉴가 열린 동안 선택 변수와 메뉴 객체를 유지한다.
        self.classification_menu = menu
        self.classification_selection = selected
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def change_classification(self, item, student_id, classification):
        try:
            db.update_student_classification(student_id, classification)
        except Exception as ex:
            messagebox.showerror("오류", f"학생 상태를 변경하지 못했습니다.\n{ex}")
            return
        if self.tree.exists(item):
            self.tree.set(item, "cls", classification)

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
# 수강 과정 관리 탭
# ------------------------------------------------------------
class CourseTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        form = ttk.LabelFrame(self, text="수강 과정 등록")
        form.pack(fill="x", padx=8, pady=8)

        ttk.Label(form, text="과정명").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.e_name = ttk.Entry(form)
        self.e_name.grid(row=0, column=1, sticky="we", padx=6, pady=4)

        ttk.Label(form, text="수강비(원)").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.e_fee = ttk.Entry(form)
        self.e_fee.grid(row=1, column=1, sticky="we", padx=6, pady=4)

        ttk.Button(form, text="과정 등록", command=self.on_add).grid(
            row=2, column=0, columnspan=2, pady=6,
        )
        form.columnconfigure(1, weight=1)

        listing = ttk.LabelFrame(self, text="등록된 수강 과정")
        listing.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree = ttk.Treeview(listing, columns=("id", "name", "fee"), show="headings", height=12)
        for c, title, width in [
            ("id", "ID", 60), ("name", "과정명", 300), ("fee", "수강비(원)", 150),
        ]:
            self.tree.heading(c, text=title)
            self.tree.column(c, width=width, anchor="center")
        scrollbar = ttk.Scrollbar(listing, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.refresh()

    def on_add(self):
        name = self.e_name.get().strip()
        if not name:
            messagebox.showwarning("입력 오류", "과정명은 필수입니다.")
            return
        try:
            fee = int(self.e_fee.get().strip())
        except ValueError:
            messagebox.showwarning("입력 오류", "수강비는 1원 이상의 정수로 입력하세요.")
            return
        if fee <= 0:
            messagebox.showwarning("입력 오류", "수강비는 1원 이상의 정수로 입력하세요.")
            return
        try:
            db.add_course(name, fee)
        except Exception as ex:
            messagebox.showerror("오류", f"과정 등록에 실패했습니다.\n{ex}")
            return
        messagebox.showinfo("완료", f"'{name}' 과정이 등록되었습니다.")
        self.e_name.delete(0, "end")
        self.e_fee.delete(0, "end")
        self.refresh()

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in db.list_courses():
            self.tree.insert("", "end", values=(r["course_id"], r["name"], f'{r["fee"]:,}'))


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

        self.is_short_course = False
        self.period_form = ttk.Frame(form)
        self.period_form.grid(row=4, column=0, columnspan=2, sticky="we")
        self.period_form.columnconfigure(1, weight=1)
        ttk.Label(self.period_form, text="시작일(YYYY-MM-DD)").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.e_start_date = ttk.Entry(self.period_form)
        self.e_start_date.grid(row=0, column=1, sticky="we", padx=6, pady=4)
        ttk.Label(self.period_form, text="종료일(YYYY-MM-DD)").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.e_end_date = ttk.Entry(self.period_form)
        self.e_end_date.grid(row=1, column=1, sticky="we", padx=6, pady=4)
        self.period_form.grid_remove()

        buttons = ttk.Frame(form)
        buttons.grid(row=5, column=0, columnspan=2, pady=6)
        self.btn_add = ttk.Button(buttons, text="반 생성", command=self.on_add)
        self.btn_add.pack(side="left", padx=4)
        self.btn_short_course = ttk.Button(buttons, text="특강 생성", command=self.toggle_short_course)
        self.btn_short_course.pack(side="left", padx=4)
        form.columnconfigure(1, weight=1)

        cols = ("id", "name", "grade", "course", "teacher", "start_date", "end_date")
        ttk.Label(self, text="반을 선택한 뒤 아래 버튼으로 학생 명단이나 시간표를 확인하세요.").pack(anchor="w", padx=8)
        actions = ttk.Frame(self)
        actions.pack(side="bottom", fill="x", padx=8, pady=(0, 8))
        ttk.Button(actions, text="학생 명단 확인", command=self.show_class_students).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="시간표 조회/수정", command=self.show_class_timetable).pack(side="left")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12, selectmode="browse")
        for c, t, w in [
            ("id", "ID", 40), ("name", "반 이름", 120), ("grade", "학년", 50),
            ("course", "과정", 160), ("teacher", "선생님", 100),
            ("start_date", "특강 시작일", 100), ("end_date", "특강 종료일", 100),
        ]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)

        self.courses = []
        self.teachers = []
        self.refresh()

    def selected_class_item(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("반 선택", "반을 선택하세요.", parent=self)
            return None
        return selection[0]

    def show_class_students(self):
        item = self.selected_class_item()
        if not item:
            return
        class_id = int(self.tree.set(item, "id"))
        class_name = self.tree.set(item, "name")
        try:
            students = db.list_students_by_class(class_id)
        except Exception as ex:
            messagebox.showerror("오류", f"학생 명단을 불러오지 못했습니다.\n{ex}")
            return

        window = tk.Toplevel(self)
        window.title(f"{class_name} - 학생 명단")
        window.geometry("600x400")
        window.transient(self.winfo_toplevel())
        ttk.Label(window, text=f"{class_name} · 수강 등록 학생 {len(students)}명 (수료·취소 포함)").pack(
            anchor="w", padx=12, pady=12,
        )
        frame = ttk.Frame(window)
        frame.pack(fill="both", expand=True, padx=12, pady=4)
        tree = ttk.Treeview(frame, columns=("id", "name", "school", "status"), show="headings")
        for column, title, width in [
            ("id", "학생 ID", 70), ("name", "이름", 120),
            ("school", "학교", 160), ("status", "수강 상태", 120),
        ]:
            tree.heading(column, text=title)
            tree.column(column, width=width, anchor="center")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True)
        for student in students:
            tree.insert("", "end", values=(
                student["student_id"], student["name"], student["school"] or "", student["status"],
            ))
        if not students:
            ttk.Label(window, text="등록된 학생이 없습니다.").pack(pady=6)
        ttk.Button(window, text="닫기", command=window.destroy).pack(pady=8)

    def show_class_timetable(self):
        item = self.selected_class_item()
        if not item:
            return
        class_id = int(self.tree.set(item, "id"))
        class_name = self.tree.set(item, "name")
        try:
            timetable = db.list_timetable_by_class(class_id)
        except Exception as ex:
            messagebox.showerror("오류", f"시간표를 불러오지 못했습니다.\n{ex}", parent=self)
            return

        window = tk.Toplevel(self)
        window.title(f"{class_name} - 시간표 조회/수정")
        window.geometry("620x520")
        window.minsize(560, 500)
        window.transient(self.winfo_toplevel())
        ttk.Label(window, text=f"{class_name} · 주간 시간표", font=("맑은 고딕", 13, "bold")).pack(
            anchor="w", padx=16, pady=(16, 6),
        )
        teacher = self.tree.set(item, "teacher")
        if teacher in ("", "None"):
            teacher = "미지정"
        ttk.Label(window, text=f"과정: {self.tree.set(item, 'course')}    담당 선생님: {teacher}").pack(
            anchor="w", padx=16, pady=(0, 12),
        )

        form = ttk.LabelFrame(window, text="요일별 수업 시간")
        form.pack(fill="both", expand=True, padx=16, pady=4)
        for column, title in enumerate(("요일", "수업 있음", "시작 시간", "종료 시간")):
            ttk.Label(form, text=title).grid(row=0, column=column, padx=12, pady=10)
        form.columnconfigure(2, weight=1)
        form.columnconfigure(3, weight=1)
        by_day = {row["day_of_class"]: row for row in timetable}
        # 팝업이 열려 있는 동안 체크박스 변수를 유지한다.
        window.day_variables = []
        day_inputs = {}
        days = zip(("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"),
                   ("월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"))
        for index, (day, label) in enumerate(days, start=1):
            existing = by_day.get(day)
            enabled = tk.BooleanVar(master=window, value=existing is not None)
            window.day_variables.append(enabled)
            ttk.Label(form, text=label).grid(row=index, column=0, padx=12, pady=7)
            start = ttk.Entry(form, width=12)
            end = ttk.Entry(form, width=12)
            start.grid(row=index, column=2, sticky="ew", padx=12, pady=7)
            end.grid(row=index, column=3, sticky="ew", padx=12, pady=7)
            if existing is not None:
                start.insert(0, existing["start_time"])
                end.insert(0, existing["end_time"])

            def toggle_inputs(variable=enabled, entries=(start, end)):
                for entry in entries:
                    entry.configure(state="normal" if variable.get() else "disabled")

            ttk.Checkbutton(form, variable=enabled, command=toggle_inputs,
                            style="Timetable.TCheckbutton").grid(row=index, column=1)
            day_inputs[day] = (enabled, start, end)
            toggle_inputs()

        ttk.Label(window, text="시간 입력 형식: HH:MM (예: 18:30)").pack(anchor="w", padx=16, pady=(8, 4))
        ttk.Label(window, text="체크한 요일만 저장됩니다. 체크를 해제하고 저장하면 해당 수업이 삭제됩니다.",
                  wraplength=500).pack(anchor="w", padx=16)

        def save_timetable():
            schedule = {
                day: (start.get().strip(), end.get().strip())
                for day, (enabled, start, end) in day_inputs.items() if enabled.get()
            }
            try:
                db.save_timetable_by_class(class_id, schedule)
            except ValueError as ex:
                messagebox.showwarning("입력 오류", str(ex), parent=window)
                return
            except Exception as ex:
                messagebox.showerror("저장 오류", f"시간표를 저장하지 못했습니다. 다시 시도해 주세요.\n{ex}", parent=window)
                return
            messagebox.showinfo("완료", "시간표가 저장되었습니다.", parent=window)

        buttons = ttk.Frame(window)
        buttons.pack(fill="x", padx=16, pady=12)
        ttk.Button(buttons, text="닫기", command=window.destroy).pack(side="right")
        ttk.Button(buttons, text="저장", command=save_timetable).pack(side="right", padx=8)

    def toggle_short_course(self):
        self.is_short_course = not self.is_short_course
        if self.is_short_course:
            self.period_form.grid()
            self.btn_add.config(text="특강 등록")
            self.btn_short_course.config(text="일반 반으로 전환")
        else:
            self.period_form.grid_remove()
            self.btn_add.config(text="반 생성")
            self.btn_short_course.config(text="특강 생성")

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
            if self.is_short_course:
                db.add_short_course(
                    course_id, teacher_id, grade, self.e_name.get().strip(),
                    self.e_start_date.get().strip(), self.e_end_date.get().strip(),
                )
            else:
                db.add_class(course_id, teacher_id, grade, self.e_name.get().strip())
            messagebox.showinfo("완료", "특강이 생성되었습니다." if self.is_short_course else "반이 생성되었습니다.")
            self.e_name.delete(0, "end")
            self.e_grade.delete(0, "end")
            self.e_start_date.delete(0, "end")
            self.e_end_date.delete(0, "end")
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
                r["start_date"] or "", r["end_date"] or "",
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

        self.cb_student.bind("<<ComboboxSelected>>", self.on_student_selected)
        ttk.Label(form, text="반").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.cb_class = ttk.Combobox(form, state="disabled")
        self.cb_class.grid(row=1, column=1, sticky="we", padx=6, pady=4)
        self.cb_class.bind("<<ComboboxSelected>>", self.on_class_selected)

        ttk.Label(form, text="금액").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        self.fee_var = tk.StringVar(master=self)
        self.e_fee = ttk.Entry(form, textvariable=self.fee_var, state="readonly")
        self.e_fee.grid(row=2, column=1, sticky="we", padx=6, pady=4)

        ttk.Label(form, text="결제일(YYYY-MM-DD)").grid(row=3, column=0, sticky="w", padx=6, pady=4)
        self.e_date = ttk.Entry(form)
        self.e_date.grid(row=3, column=1, sticky="we", padx=6, pady=4)

        self.btn_add = ttk.Button(form, text="결제 등록", command=self.on_add, state="disabled")
        self.btn_add.grid(row=4, column=0, columnspan=2, pady=6)
        self.selection_hint = ttk.Label(form, text="학생을 선택하면 수강 중인 반을 확인할 수 있습니다.")
        self.selection_hint.grid(row=5, column=0, columnspan=2, sticky="w", padx=6, pady=4)
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

    def on_student_selected(self, event=None):
        self.classes = []
        self.cb_class.configure(values=(), state="disabled")
        self.cb_class.set("")
        self.fee_var.set("")
        self.btn_add.configure(state="disabled")
        if self.cb_student.current() < 0:
            self.selection_hint.configure(text="학생을 선택하면 수강 중인 반을 확인할 수 있습니다.")
            return
        student_id = self.students[self.cb_student.current()]["student_id"]
        try:
            self.classes = list(db.list_active_classes_by_student(student_id))
        except Exception as ex:
            self.selection_hint.configure(text="수강 중인 반을 불러오지 못했습니다.")
            messagebox.showerror("조회 오류", f"수강 중인 반을 불러오지 못했습니다.\n{ex}", parent=self)
            return
        if not self.classes:
            self.selection_hint.configure(text="현재 수강 중인 반이 없습니다.")
            return
        self.cb_class.configure(state="readonly", values=[
            f'{row["class_name"]} · {row["course_name"]} (반 ID: {row["class_id"]})'
            for row in self.classes
        ])
        self.selection_hint.configure(text="반을 선택하면 해당 과정의 금액이 자동으로 입력됩니다.")

    def on_class_selected(self, event=None):
        index = self.cb_class.current()
        self.fee_var.set(str(self.classes[index]["fee"]) if index >= 0 else "")
        self.btn_add.configure(state="normal" if index >= 0 else "disabled")

    def on_add(self):
        if self.cb_student.current() < 0:
            messagebox.showwarning("입력 오류", "학생을 선택하세요.")
            return
        if self.cb_class.current() < 0:
            messagebox.showwarning("입력 오류", "수강 중인 반을 선택하세요.")
            return
        try:
            sid = self.students[self.cb_student.current()]["student_id"]
            class_id = self.classes[self.cb_class.current()]["class_id"]
            db.add_class_payment(sid, class_id, self.e_date.get().strip() or "2026-11-14")
            messagebox.showinfo("완료", "결제가 등록되었습니다.")
            self.refresh()
        except ValueError as ve:
            messagebox.showerror("오류", str(ve))
        except Exception as ex:
            messagebox.showerror("오류", f"결제를 등록하지 못했습니다.\n{ex}")

    def refresh(self):
        self.students = list(db.list_students())
        self.cb_student["values"] = [f'{s["name"]} ({s["student_classification"]})' for s in self.students]
        self.cb_student.set("")
        self.on_student_selected()
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
