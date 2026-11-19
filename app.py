# -*- coding: utf-8 -*-
"""
app.py - Tkinter GUI (프론트엔드)
중고등 수학학원 관리 시스템

실행: python app.py
- 실행 시 academy.db가 없으면 자동 생성(스키마 + 샘플데이터).
- 탭: 학생 관리 / 선생님 관리 / 수강 과정 관리 / 반 관리 / 수강 등록 / 결제
- 모든 DB 작업은 db.py 함수를 통해서만 수행 (화면/DB 분리)

[팀원 보완 포인트]
- UI 스타일/레이아웃 개선, 입력 폼 검증 강화
- 수정/삭제 버튼 추가, 검색 필터, 통계 화면
- 날짜 피커, 콤보박스 자동 새로고침 등
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import date

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
        self.title("중고등 수학학원 관리 시스템")
        self.geometry("900x600")
        setup_style(self)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_student = StudentTab(nb)
        self.tab_teacher = TeacherTab(nb)
        self.tab_course = CourseTab(nb)
        self.tab_class = ClassTab(nb)
        self.tab_enroll = EnrollTab(nb)
        self.tab_payment = PaymentTab(nb)

        nb.add(self.tab_student, text="학생 관리")
        nb.add(self.tab_teacher, text="선생님 관리")
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
        ttk.Label(form, text="학년").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        self.e_grade = ttk.Combobox(form, values=("", *db.GRADE_LEVELS), state="readonly")
        self.e_grade.grid(row=2, column=1, sticky="we", padx=6, pady=4)
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
        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=8)
        ttk.Button(actions, text="학생 정보 수정", command=self.edit_student).pack(side="left")
        ttk.Button(actions, text="학생별 수강 목록 / 총 수강비", command=self.show_enrollments).pack(side="left", padx=8)


        self.refresh()

    def selected_student(self):
        items = self.tree.selection()
        if not items:
            messagebox.showwarning("학생 선택", "학생을 선택하세요.", parent=self)
            return None
        sid = int(self.tree.set(items[0], "id"))
        return next((r for r in db.list_students() if r["student_id"] == sid), None)

    def edit_student(self):
        record = self.selected_student()
        if record is None:
            return
        window = tk.Toplevel(self)
        window.title("학생 정보 수정")
        window.transient(self.winfo_toplevel())
        fields = []
        for i, (label, key) in enumerate((("이름", "name"), ("학교", "school"), ("학년", "grade"),
                                         ("등록일(YYYY-MM-DD)", "day_of_admission"), ("연락처", "contact_number"))):
            if key == "grade":
                ttk.Label(window, text=label).grid(row=i, column=0, sticky="w", padx=6, pady=4)
                entry = ttk.Combobox(window, values=("", *db.GRADE_LEVELS), state="readonly")
                entry.grid(row=i, column=1, sticky="we", padx=6, pady=4)
                entry.set(record[key] or "")
            else:
                entry = self._row(window, label, i)
                entry.insert(0, str(record[key]) if record[key] is not None else "")
            fields.append(entry)
        ttk.Label(window, text="분류").grid(row=5, column=0, padx=6, pady=4)
        classification = ttk.Combobox(window, values=("ACTIVE", "INACTIVE", "BLACK"), state="readonly")
        classification.set(record["student_classification"])
        classification.grid(row=5, column=1, padx=6, pady=4)
        def save():
            try:
                db.update_student(record["student_id"], *(e.get() for e in fields), classification.get())
            except Exception as ex:
                messagebox.showerror("수정 오류", str(ex), parent=window)
                return
            window.destroy()
            self.refresh()
        ttk.Button(window, text="저장", command=save).grid(row=6, column=0, pady=8)
        ttk.Button(window, text="취소", command=window.destroy).grid(row=6, column=1, pady=8)
        window.grab_set()

    def show_enrollments(self):
        record = self.selected_student()
        if record is None:
            return
        rows = db.list_enrollments_by_student(record["student_id"])
        window = tk.Toplevel(self)
        window.title(f"{record['name']} (ID: {record['student_id']}) - 수강 목록")
        window.geometry("800x400")
        total = sum(r["fee"] for r in rows if r["status"] == "ACTIVE")
        ttk.Label(window, text=f"현재 수강비 합계: {total:,}원 (ACTIVE만 합산 · 현재 과정 가격 기준, 납부액 아님)").pack(padx=8, pady=8)
        tree = ttk.Treeview(window, columns=("id", "class", "course", "fee", "date", "status"), show="headings")
        for key, title in zip(tree["columns"], ("수강 ID", "반", "과정", "현재 수강비", "등록일", "상태")):
            tree.heading(key, text=title)
            tree.column(key, width=120, anchor="center")
        tree.pack(fill="both", expand=True, padx=8, pady=8)
        for r in rows:
            tree.insert("", "end", values=tuple(r))
        ttk.Button(window, text="닫기", command=window.destroy).pack(pady=8)

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
            db.add_student(
                name, self.e_school.get().strip() or None, grade,
                self.e_date.get().strip() or None, self.e_contact.get().strip() or None,
                self.cb_cls.get(),
            )
            messagebox.showinfo("완료", f"'{name}' 학생이 등록되었습니다.")
            self.e_grade.set("")
            for e in (self.e_name, self.e_school, self.e_date, self.e_contact):
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
# 선생님 관리 탭
# ------------------------------------------------------------
class TeacherTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        form = ttk.LabelFrame(self, text="선생님 등록")
        form.pack(fill="x", padx=8, pady=8)
        ttk.Label(form, text="이름").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.e_name = ttk.Entry(form)
        self.e_name.grid(row=0, column=1, sticky="we", padx=6, pady=4)
        ttk.Label(form, text="연락처").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.e_contact = ttk.Entry(form)
        self.e_contact.grid(row=1, column=1, sticky="we", padx=6, pady=4)
        ttk.Button(form, text="등록", command=self.on_add).grid(row=2, column=0, columnspan=2, pady=6)
        form.columnconfigure(1, weight=1)
        window = self
        ttk.Label(self, text="목록에서 선생님을 선택한 뒤 아래 버튼으로 정보를 수정하세요.").pack(anchor="w", padx=8, pady=(8, 0))
        buttons = ttk.Frame(window)
        buttons.pack(side="bottom", fill="x", padx=12, pady=12)
        frame = ttk.Frame(window)
        frame.pack(fill="both", expand=True, padx=12, pady=12)
        tree = ttk.Treeview(frame, columns=("id", "name", "contact"), show="headings", selectmode="browse")
        for column, title, width in (("id", "ID", 60), ("name", "이름", 160), ("contact", "연락처", 240)):
            tree.heading(column, text=title)
            tree.column(column, width=width, anchor="center")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True)

        def reload_teachers():
            try:
                teachers = db.list_teachers()
            except Exception as ex:
                messagebox.showerror("조회 오류", f"선생님 목록을 불러오지 못했습니다.\n{ex}", parent=window)
                return
            for item in tree.get_children():
                tree.delete(item)
            for teacher in teachers:
                tree.insert("", "end", values=(teacher["teacher_id"], teacher["name"], teacher["contact_number"] or ""))

        def edit_teacher():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("선생님 선택", "수정할 선생님을 선택하세요.", parent=window)
                return
            item = selection[0]
            teacher_id = int(tree.set(item, "id"))
            editor = tk.Toplevel(window)
            editor.title("선생님 정보 수정")
            editor.transient(self.winfo_toplevel())
            editor.resizable(False, False)
            form = ttk.Frame(editor, padding=16)
            form.pack(fill="both", expand=True)
            ttk.Label(form, text="이름").grid(row=0, column=0, padx=6, pady=6)
            name = ttk.Entry(form, width=30)
            name.grid(row=0, column=1, padx=6, pady=6)
            name.insert(0, tree.set(item, "name"))
            ttk.Label(form, text="연락처").grid(row=1, column=0, padx=6, pady=6)
            contact = ttk.Entry(form, width=30)
            contact.grid(row=1, column=1, padx=6, pady=6)
            contact.insert(0, tree.set(item, "contact"))

            def close_editor():
                editor.destroy()

            def save():
                try:
                    db.update_teacher(teacher_id, name.get(), contact.get())
                except ValueError as ex:
                    messagebox.showwarning("입력 오류", str(ex), parent=editor)
                    return
                except Exception as ex:
                    messagebox.showerror("저장 오류", f"선생님 정보를 저장하지 못했습니다.\n{ex}", parent=editor)
                    return
                close_editor()
                reload_teachers()
                messagebox.showinfo("완료", "선생님 정보가 수정되었습니다.", parent=window)

            controls = ttk.Frame(form)
            controls.grid(row=2, column=0, columnspan=2, pady=10)
            ttk.Button(controls, text="저장", command=save).pack(side="left", padx=4)
            ttk.Button(controls, text="취소", command=close_editor).pack(side="left", padx=4)
            editor.protocol("WM_DELETE_WINDOW", close_editor)
            editor.grab_set()
            name.focus_set()

        ttk.Button(buttons, text="선생님 정보 수정", command=edit_teacher).pack(side="left")
        self.refresh = reload_teachers
        self.refresh()

    def on_add(self):
        try:
            db.add_teacher(self.e_name.get(), self.e_contact.get())
        except ValueError as ex:
            messagebox.showwarning("입력 오류", str(ex), parent=self)
            return
        except Exception as ex:
            messagebox.showerror("등록 오류", f"선생님을 등록하지 못했습니다.\n{ex}", parent=self)
            return
        self.e_name.delete(0, "end")
        self.e_contact.delete(0, "end")
        self.refresh()
        messagebox.showinfo("완료", "선생님이 등록되었습니다.", parent=self)


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

        actions = ttk.Frame(self)
        actions.pack(side="bottom", fill="x", padx=8, pady=(0, 8))
        ttk.Button(actions, text="수정", command=self.on_edit).pack(side="left")
        listing = ttk.LabelFrame(self, text="등록된 수강 과정")
        listing.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree = ttk.Treeview(listing, columns=("id", "name", "fee"), show="headings", height=12,
                                 selectmode="browse")
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
            db.add_course(name, self.e_fee.get())
        except ValueError as ex:
            messagebox.showwarning("입력 오류", str(ex), parent=self)
            return
        except Exception as ex:
            messagebox.showerror("오류", f"과정 등록에 실패했습니다.\n{ex}")
            return
        messagebox.showinfo("완료", f"'{name}' 과정이 등록되었습니다.")
        self.e_name.delete(0, "end")
        self.e_fee.delete(0, "end")
        self.refresh()

    def on_edit(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("과정 선택", "수정할 과정을 선택하세요.", parent=self)
            return
        item = selection[0]
        course_id = int(self.tree.set(item, "id"))
        window = tk.Toplevel(self)
        window.title("수강 과정 수정")
        window.resizable(False, False)
        window.transient(self.winfo_toplevel())
        form = ttk.Frame(window, padding=16)
        form.pack(fill="both", expand=True)
        ttk.Label(form, text="과정명").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        name_entry = ttk.Entry(form, width=35)
        name_entry.grid(row=0, column=1, padx=6, pady=6)
        name_entry.insert(0, self.tree.set(item, "name"))
        ttk.Label(form, text="수강비(원)").grid(row=1, column=0, sticky="w", padx=6, pady=6)
        fee_entry = ttk.Entry(form, width=35)
        fee_entry.grid(row=1, column=1, padx=6, pady=6)
        fee_entry.insert(0, self.tree.set(item, "fee").replace(",", ""))
        ttk.Label(form, text="수강비는 0 이상의 정수로 입력하세요.").grid(
            row=2, column=0, columnspan=2, sticky="w", padx=6, pady=6,
        )

        def save():
            try:
                db.update_course(course_id, name_entry.get(), fee_entry.get())
            except ValueError as ex:
                messagebox.showwarning("입력 오류", str(ex), parent=window)
                return
            except Exception as ex:
                messagebox.showerror("저장 오류", f"과정을 수정하지 못했습니다.\n{ex}", parent=window)
                return
            window.destroy()
            self.refresh()
            messagebox.showinfo("완료", "수강 과정이 수정되었습니다.", parent=self)

        buttons = ttk.Frame(form)
        buttons.grid(row=3, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(buttons, text="저장", command=save).pack(side="left", padx=4)
        ttk.Button(buttons, text="취소", command=window.destroy).pack(side="left", padx=4)
        window.grab_set()
        name_entry.focus_set()

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
        self.e_grade = ttk.Combobox(form, values=("", *db.GRADE_LEVELS), state="readonly")
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
        ttk.Button(actions, text="반 정보 수정", command=self.edit_class).pack(side="left", padx=8)
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

    def edit_class(self):
        item = self.selected_class_item()
        if not item:
            return
        class_id = int(self.tree.set(item, "id"))
        try:
            record = next((row for row in db.list_classes() if row["class_id"] == class_id), None)
            teachers = list(db.list_teachers())
            if record is None:
                raise ValueError("존재하지 않는 반입니다.")
        except Exception as ex:
            messagebox.showerror("조회 오류", str(ex), parent=self)
            return
        window = tk.Toplevel(self)
        window.title("반 정보 수정")
        window.transient(self.winfo_toplevel())
        window.resizable(False, False)
        form = ttk.Frame(window, padding=16)
        form.pack(fill="both", expand=True)
        for row, text in enumerate(("과정 (변경 불가)", "반 이름", "학년", "선생님")):
            ttk.Label(form, text=text).grid(row=row, column=0, sticky="w", padx=6, pady=6)
        window.course_var = tk.StringVar(master=window, value=record["course_name"])
        ttk.Entry(form, textvariable=window.course_var, state="readonly", width=35).grid(row=0, column=1, padx=6, pady=6)
        name = ttk.Entry(form, width=35)
        name.grid(row=1, column=1, padx=6, pady=6)
        name.insert(0, record["class_name"])
        grade = ttk.Combobox(form, width=35, values=("", *db.GRADE_LEVELS), state="readonly")
        grade.grid(row=2, column=1, padx=6, pady=6)
        grade.set(record["grade"] or "")
        teacher = ttk.Combobox(form, state="readonly", width=33,
                               values=["NULL (미지정)"] + [f'{t["name"]} (ID: {t["teacher_id"]})' for t in teachers])
        teacher.grid(row=3, column=1, padx=6, pady=6)
        teacher.current(next((i + 1 for i, t in enumerate(teachers)
                              if t["teacher_id"] == record["teacher_id"]), 0))

        def save():
            teacher_id = teachers[teacher.current() - 1]["teacher_id"] if teacher.current() > 0 else None
            try:
                db.update_class(class_id, name.get(), grade.get(), teacher_id)
            except ValueError as ex:
                messagebox.showwarning("입력 오류", str(ex), parent=window)
                return
            except Exception as ex:
                messagebox.showerror("저장 오류", f"반 정보를 저장하지 못했습니다.\n{ex}", parent=window)
                return
            window.destroy()
            self.refresh()
            messagebox.showinfo("완료", "반 정보가 수정되었습니다.", parent=self)

        controls = ttk.Frame(form)
        controls.grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(controls, text="저장", command=save).pack(side="left", padx=4)
        ttk.Button(controls, text="취소", command=window.destroy).pack(side="left", padx=4)
        window.grab_set()
        name.focus_set()

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
            if self.cb_teacher.current() > 0:
                teacher_id = self.teachers[self.cb_teacher.current() - 1]["teacher_id"]
            grade = self.e_grade.get().strip()
            if self.is_short_course:
                db.add_short_course(
                    course_id, teacher_id, grade, self.e_name.get().strip(),
                    self.e_start_date.get().strip(), self.e_end_date.get().strip(),
                )
            else:
                db.add_class(course_id, teacher_id, grade, self.e_name.get().strip())
            messagebox.showinfo("완료", "특강이 생성되었습니다." if self.is_short_course else "반이 생성되었습니다.")
            self.e_name.delete(0, "end")
            self.e_grade.set("")
            self.e_start_date.delete(0, "end")
            self.e_end_date.delete(0, "end")
            self.refresh()
        except Exception as ex:
            messagebox.showerror("오류", str(ex))

    def refresh(self):
        previous_teacher = None
        teacher_index = self.cb_teacher.current() - 1
        if 0 <= teacher_index < len(self.teachers):
            previous_teacher = self.teachers[teacher_index]["teacher_id"]
        self.courses = list(db.list_courses())
        self.teachers = list(db.list_teachers())
        self.cb_course["values"] = [f'{c["name"]} ({c["fee"]}원)' for c in self.courses]
        self.cb_course.set("")
        self.cb_teacher["values"] = ["NULL (미지정)"] + [f'{t["name"]} (ID: {t["teacher_id"]})' for t in self.teachers]
        self.cb_teacher.current(next((i + 1 for i, t in enumerate(self.teachers)
                                      if t["teacher_id"] == previous_teacher), 0))
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in db.list_classes():
            self.tree.insert("", "end", values=(
                r["class_id"], r["class_name"], r["grade"] if r["grade"] is not None else "",
                r["course_name"], r["teacher_name"] or "NULL (미지정)",
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
        self.e_date.insert(0, date.today().isoformat())

        ttk.Button(form, text="수강 등록", command=self.on_add).grid(row=3, column=0, columnspan=2, pady=6)
        form.columnconfigure(1, weight=1)

        controls = ttk.Frame(self)
        controls.pack(fill="x", padx=8)
        ttk.Label(controls, text="선택한 수강 상태").pack(side="left")
        self.cb_status = ttk.Combobox(controls, values=("ACTIVE", "COMPLETED", "CANCELED"), state="readonly", width=14)
        self.cb_status.set("COMPLETED")
        self.cb_status.pack(side="left", padx=8)
        ttk.Button(controls, text="상태 변경", command=self.change_status).pack(side="left")

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

    def change_status(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("수강 선택", "변경할 수강을 선택하세요.", parent=self)
            return
        try:
            db.update_enrollment_status(int(self.tree.set(selection[0], "id")), self.cb_status.get())
        except Exception as ex:
            messagebox.showerror("변경 오류", str(ex), parent=self)
            return
        self.refresh()
        messagebox.showinfo("완료", "수강 상태가 변경되었습니다.", parent=self)

    def on_add(self):
        if self.cb_student.current() < 0 or self.cb_class.current() < 0:
            messagebox.showwarning("입력 오류", "학생과 반을 선택하세요.")
            return
        try:
            sid = self.students[self.cb_student.current()]["student_id"]
            cid = self.classes[self.cb_class.current()]["class_id"]
            date = self.e_date.get().strip() or ""
            db.add_enrollment(sid, cid, date)
            messagebox.showinfo("완료", "수강 등록되었습니다.")
            self.refresh()
        except Exception as ex:
            messagebox.showerror("오류", str(ex))

    def refresh(self):
        self.students = list(db.list_students())
        self.classes = list(db.list_classes())
        self.cb_student["values"] = [f'{s["name"]} (ID: {s["student_id"]}, {s["student_classification"]})' for s in self.students]
        self.cb_class["values"] = [c["class_name"] for c in self.classes]
        self.cb_student.set("")
        self.cb_class.set("")
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
        self.e_date.insert(0, date.today().isoformat())

        ttk.Label(form, text="결제 상태").grid(row=4, column=0, sticky="w", padx=6, pady=4)
        self.cb_payment_status = ttk.Combobox(form, values=("완납", "미납"), state="readonly")
        self.cb_payment_status.current(0)
        self.cb_payment_status.grid(row=4, column=1, sticky="we", padx=6, pady=4)
        self.cb_payment_status.bind("<<ComboboxSelected>>", lambda event: self.e_date.configure(
            state="normal" if self.cb_payment_status.current() == 0 else "disabled"))
        self.btn_add = ttk.Button(form, text="결제 등록", command=self.on_add, state="disabled")
        ttk.Label(form, text="청구월(YYYY-MM)").grid(row=5, column=0, sticky="w", padx=6, pady=4)
        self.e_month = ttk.Entry(form)
        self.e_month.grid(row=5, column=1, sticky="we", padx=6, pady=4)
        self.e_month.insert(0, date.today().isoformat()[:7])
        self.e_month.bind("<FocusOut>", self.on_student_selected)
        self.e_month.bind("<Return>", self.on_student_selected)
        self.btn_add.grid(row=6, column=0, columnspan=2, pady=6)
        self.selection_hint = ttk.Label(form, text="학생을 선택하면 수강 중인 반을 확인할 수 있습니다.")
        self.selection_hint.grid(row=7, column=0, columnspan=2, sticky="w", padx=6, pady=4)
        form.columnconfigure(1, weight=1)

        filters = ttk.LabelFrame(self, text="결제 내역 조회 (학생·기간 조건을 함께 적용, 경계 날짜 포함)")
        filters.pack(fill="x", padx=8, pady=4)
        self.cb_filter_student = ttk.Combobox(filters, state="readonly", width=24)
        self.cb_filter_student.pack(side="left", padx=4)
        self.filter_start = ttk.Entry(filters, width=12)
        self.filter_start.pack(side="left", padx=4)
        ttk.Label(filters, text="~").pack(side="left")
        self.filter_end = ttk.Entry(filters, width=12)
        self.filter_end.pack(side="left", padx=4)
        ttk.Label(filters, text="청구월").pack(side="left")
        self.filter_month = ttk.Entry(filters, width=9)
        self.filter_month.pack(side="left", padx=4)
        ttk.Button(filters, text="조회", command=self.reload_payments).pack(side="left", padx=4)
        ttk.Button(filters, text="전체 보기", command=self.reset_filters).pack(side="left")
        ttk.Label(self, text="조회 기간: YYYY-MM-DD · 빈 시작일/종료일은 해당 방향 제한 없음").pack(anchor="w", padx=8)
        self.lbl_total = ttk.Label(self, text="총 매출: -")
        self.lbl_total.pack(anchor="e", padx=12)

        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=8)
        ttk.Button(actions, text="결제 대상 조회", command=self.show_payment_targets).pack(side="left")
        ttk.Button(actions, text="선택한 결제 상태 변경", command=self.change_payment_status).pack(side="left", padx=8)
        cols = ("id", "student", "class", "course", "month", "fee", "date", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=11)
        for c, t, w in [
            ("id", "ID", 40), ("student", "학생", 100), ("class", "반", 105), ("course", "과정명", 140),
            ("month", "청구월", 70),
            ("fee", "금액", 90), ("date", "결제일", 100), ("status", "상태", 70),
        ]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)

        self.students = []
        self.refresh()

    def show_payment_targets(self):
        window = tk.Toplevel(self)
        window.title("월별 결제 대상")
        window.geometry("720x420")
        window.transient(self.winfo_toplevel())
        controls = ttk.Frame(window, padding=8)
        controls.pack(fill="x")
        ttk.Label(controls, text="청구월(YYYY-MM)").pack(side="left", padx=4)
        month = ttk.Entry(controls, width=10)
        month.insert(0, self.e_month.get())
        month.pack(side="left", padx=4)
        tree = ttk.Treeview(window, columns=("student", "class", "fee", "status"), show="headings",
                            selectmode="browse")
        for column, label, width in (("student", "학생", 180), ("class", "반", 160),
                                     ("fee", "수강비", 120), ("status", "상태", 100)):
            tree.heading(column, text=label)
            tree.column(column, width=width, anchor="center")
        tree.pack(fill="both", expand=True, padx=8, pady=8)
        labels = {"PAID": "완납", "UNPAID": "미납", "REFUNDED": "환불"}
        targets = {}
        loaded_month = None

        def reload_targets():
            nonlocal targets, loaded_month
            loaded_month = None
            tree.delete(*tree.get_children())
            try:
                targets = {str(row["enrollment_id"]): row for row in db.list_payment_targets(month.get())}
            except Exception as error:
                messagebox.showerror("결제 대상 조회", str(error), parent=window)
                return
            loaded_month = month.get()
            for key, row in targets.items():
                fee = row["billed_fee"] if row["payment_id"] is not None else row["fee"]
                tree.insert("", "end", iid=key, values=(f'{row["student_name"]} (ID: {row["student_id"]})',
                            row["class_name"], f"{fee:,}원", labels.get(row["status"], "미발행")))

        def issue():
            selection = tree.selection()
            if not selection or month.get() != loaded_month:
                messagebox.showwarning("미납 등록", "청구월을 조회하고 대상 행을 선택하세요.", parent=window)
                return
            row = targets[selection[0]]
            try:
                db.add_class_payment(row["student_id"], row["class_id"], None, "UNPAID", loaded_month)
            except Exception as error:
                messagebox.showerror("미납 등록", str(error), parent=window)
                return
            reload_targets()
            self.reload_payments()
            self.on_student_selected()

        ttk.Button(controls, text="조회", command=reload_targets).pack(side="left", padx=4)
        ttk.Button(controls, text="선택한 대상 미납 등록", command=issue).pack(side="left", padx=8)
        reload_targets()

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
            self.classes = [row for row in db.list_payment_targets(self.e_month.get(), student_id)
                            if row["payment_id"] is None]
        except Exception as ex:
            self.selection_hint.configure(text="수강 중인 반을 불러오지 못했습니다.")
            if event is None or event.keysym == "Return":
                messagebox.showerror("조회 오류", str(ex), parent=self)
            return
        if not self.classes:
            self.selection_hint.configure(text="선택한 청구월에 미발행 수강이 없습니다.")
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
            status = ("PAID", "UNPAID")[self.cb_payment_status.current()]
            db.add_class_payment(sid, class_id, self.e_date.get(), status, self.e_month.get())
            messagebox.showinfo("완료", "결제가 등록되었습니다.")
            self.refresh()
        except ValueError as ve:
            messagebox.showerror("오류", str(ve))
        except Exception as ex:
            messagebox.showerror("오류", f"결제를 등록하지 못했습니다.\n{ex}")

    def change_payment_status(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("결제 선택", "상태를 바꿀 결제를 선택하세요.", parent=self)
            return
        item = selected[0]
        status = self.tree.set(item, "status")
        if status == "미납":
            paid_on = simpledialog.askstring("완납 처리", "실제 결제일 (YYYY-MM-DD)",
                                             initialvalue=date.today().isoformat(), parent=self)
            if paid_on is None:
                return
            next_status = "PAID"
        elif status == "완납":
            if not messagebox.askyesno("환불 처리", "선택한 결제를 전액 환불 상태로 기록할까요?", parent=self):
                return
            next_status, paid_on = "REFUNDED", None
        else:
            messagebox.showinfo("결제 상태", "이미 환불 처리된 결제입니다.", parent=self)
            return
        try:
            db.update_payment_status(int(self.tree.set(item, "id")), next_status, paid_on)
        except Exception as exc:
            messagebox.showerror("변경 오류", str(exc), parent=self)
            return
        self.reload_payments()

    def reset_filters(self):
        self.cb_filter_student.current(0)
        self.filter_start.delete(0, "end")
        self.filter_end.delete(0, "end")
        self.filter_month.delete(0, "end")
        self.reload_payments()

    def reload_payments(self):
        sid = self.filter_ids[self.cb_filter_student.current()] if self.cb_filter_student.current() >= 0 else None
        try:
            rows = db.list_payments(sid, self.filter_start.get().strip(), self.filter_end.get().strip(), self.filter_month.get().strip())
        except Exception as ex:
            messagebox.showerror("조회 오류", str(ex), parent=self)
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        labels = {"PAID": "완납", "UNPAID": "미납", "REFUNDED": "환불"}
        for r in rows:
            self.tree.insert("", "end", values=(r["payment_id"], r["student_name"], r["class_name"] or "", r["course_name"],
                                                  (r["billing_month"] or "미지정")[:7], r["course_fee"],
                                                  r["payment_date"] or "", labels[r["status"]]))
        total = sum(r["course_fee"] for r in rows if r["status"] == "PAID")
        self.lbl_total.configure(text=f"조회 결과: {len(rows)}건 · 수납 합계: {total:,}원")

    def refresh(self):
        old_ids = getattr(self, "filter_ids", [None])
        index = self.cb_filter_student.current()
        previous = old_ids[index] if 0 <= index < len(old_ids) else None
        self.students = list(db.list_students())
        self.cb_student["values"] = [f'{r["name"]} (ID: {r["student_id"]}, {r["student_classification"]})' for r in self.students]
        self.cb_student.set("")
        self.on_student_selected()
        self.filter_ids = [None] + [r["student_id"] for r in self.students]
        self.cb_filter_student["values"] = ["전체 학생"] + [f'{r["name"]} (ID: {r["student_id"]})' for r in self.students]
        self.cb_filter_student.current(self.filter_ids.index(previous) if previous in self.filter_ids else 0)
        self.reload_payments()


if __name__ == "__main__":
    db.init_db()           # academy.db 없으면 자동 생성(+샘플)
    app = AcademyApp()
    app.mainloop()
