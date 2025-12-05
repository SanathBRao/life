"""
SDBMS - Single-file Streamlit-only application
- Single SQLite DB file stored alongside the app (sdbms.db)
- Password hashing using PBKDF2 (standard library)
- Role-based access: Admin, Instructor, Student
- CRUD for Users, Students, Courses, Enrollments/Grades
- CSV export for tables
- Simple theme toggle (light/dark) via CSS
- All logic inside this Streamlit app (no external services)
"""

import streamlit as st
import sqlite3
import os
import pandas as pd
import hashlib
import binascii
import secrets
from io import BytesIO

DB_PATH = "sdbms.db"
PBKDF2_ITER = 120_000

# ----------------------- DB helpers -----------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    first = not os.path.exists(DB_PATH)
    conn = get_conn()
    cur = conn.cursor()
    # Users: username (unique), password_hash (salted pbkdf2), role (Admin/Instructor/Student)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        capacity INTEGER NOT NULL DEFAULT 0
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS enrollments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        course_code TEXT NOT NULL,
        grade INTEGER,
        FOREIGN KEY(student_id) REFERENCES students(student_id),
        FOREIGN KEY(course_code) REFERENCES courses(code)
    );
    """)
    conn.commit()

    # create default admin if no users
    cur.execute("SELECT COUNT(*) as c FROM users")
    if cur.fetchone()["c"] == 0:
        default_pw = "admin123"  # you can change this after first login
        h = hash_password(default_pw)
        cur.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    ("admin", h, "Admin"))
        conn.commit()
    conn.close()

# ----------------------- Password hashing -----------------------
def hash_password(password: str) -> str:
    """Return salt$hexhash"""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITER)
    return f"{binascii.hexlify(salt).decode()}${binascii.hexlify(dk).decode()}"

def verify_password(stored: str, provided: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split("$")
        salt = binascii.unhexlify(salt_hex)
        dk_stored = binascii.unhexlify(dk_hex)
        dk_new = hashlib.pbkdf2_hmac("sha256", provided.encode(), salt, PBKDF2_ITER)
        return secrets.compare_digest(dk_new, dk_stored)
    except Exception:
        return False

# ----------------------- Utility helpers -----------------------
def query_df(sql, params=()):
    conn = get_conn()
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df

def run_sql(sql, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    conn.close()

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()

# ----------------------- Theme (light/dark) -----------------------
def set_theme():
    if "theme" not in st.session_state:
        st.session_state.theme = "light"
    if st.session_state.theme == "dark":
        st.markdown(
            """
            <style>
            .stApp { background-color: #0e1117; color: #d9e0e6; }
            .css-1d391kg { color: #d9e0e6; }
            .stButton>button { background-color: #1f2937; color: #d9e0e6; }
            table { color: #d9e0e6; }
            </style>
            """, unsafe_allow_html=True
        )
    else:
        st.markdown("", unsafe_allow_html=True)

# ----------------------- Authentication UI -----------------------
def login_form():
    st.subheader("🔐 Login")
    uname = st.text_input("Username")
    pw = st.text_input("Password", type="password")
    if st.button("Login"):
        df = query_df("SELECT * FROM users WHERE username = ?", (uname,))
        if df.shape[0] == 1 and verify_password(df.loc[0, "password_hash"], pw):
            st.success("Login successful")
            st.session_state.logged_in = True
            st.session_state.username = uname
            st.session_state.role = df.loc[0, "role"]
            st.experimental_rerun()
        else:
            st.error("Invalid username / password")

def logout():
    st.session_state.pop("logged_in", None)
    st.session_state.pop("username", None)
    st.session_state.pop("role", None)
    st.success("Logged out")
    st.experimental_rerun()

# ----------------------- Pages / Modules -----------------------
def admin_users_page():
    st.header("🧑‍💼 User Management (Admin)")
    df = query_df("SELECT id, username, role FROM users")
    st.dataframe(df)

    st.markdown("#### ➕ Create new user")
    col1, col2, col3 = st.columns([2,2,1])
    with col1:
        new_un = st.text_input("Username", key="new_un")
    with col2:
        new_pw = st.text_input("Password", type="password", key="new_pw")
    with col3:
        new_role = st.selectbox("Role", ["Admin", "Instructor", "Student"], key="new_role")
    if st.button("Create User"):
        if new_un.strip() == "" or new_pw.strip() == "":
            st.error("Username and password required")
        else:
            try:
                ph = hash_password(new_pw)
                run_sql("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                        (new_un.strip(), ph, new_role))
                st.success(f"User '{new_un}' created")
            except Exception as e:
                st.error(f"Error creating user: {e}")

    st.markdown("---")
    st.markdown("#### 🔁 Reset user password / delete user")
    sel = st.selectbox("Select user (by username)", df["username"].tolist() if not df.empty else [])
    if sel:
        colx, coly = st.columns(2)
        with colx:
            newpass = st.text_input("New password", type="password", key="reset_pw")
            if st.button("Reset password"):
                ph = hash_password(newpass)
                run_sql("UPDATE users SET password_hash = ? WHERE username = ?", (ph, sel))
                st.success("Password updated")
        with coly:
            if st.button("Delete user"):
                if sel == st.session_state.username:
                    st.error("You cannot delete the currently logged-in user.")
                else:
                    run_sql("DELETE FROM users WHERE username = ?", (sel,))
                    st.success("User deleted")

def students_page():
    st.header("📚 Student Management")
    df = query_df("SELECT id, student_id, name, email FROM students")
    st.dataframe(df)

    st.markdown("#### ➕ Add Student")
    sid = st.text_input("Student ID", key="sid")
    sname = st.text_input("Name", key="sname")
    semail = st.text_input("Email", key="semail")
    if st.button("Add Student"):
        if sid.strip() == "" or sname.strip() == "":
            st.error("Student ID and Name required")
        else:
            try:
                run_sql("INSERT INTO students (student_id, name, email) VALUES (?, ?, ?)",
                        (sid.strip(), sname.strip(), semail.strip()))
                st.success("Student added")
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("#### ✏️ Edit / Delete Student")
    if not df.empty:
        sel = st.selectbox("Select student", df["student_id"].tolist())
        if sel:
            rec = query_df("SELECT * FROM students WHERE student_id = ?", (sel,)).iloc[0]
            new_name = st.text_input("Name", value=rec["name"], key="edit_name")
            new_email = st.text_input("Email", value=rec["email"] or "", key="edit_email")
            if st.button("Update Student"):
                run_sql("UPDATE students SET name = ?, email = ? WHERE student_id = ?",
                        (new_name.strip(), new_email.strip(), sel))
                st.success("Updated")
            if st.button("Delete Student"):
                # also delete enrollments
                run_sql("DELETE FROM enrollments WHERE student_id = ?", (sel,))
                run_sql("DELETE FROM students WHERE student_id = ?", (sel,))
                st.success("Deleted student and their enrollments")

    st.markdown("---")
    if st.button("Export Students CSV"):
        df_export = query_df("SELECT student_id, name, email FROM students")
        b = to_csv_bytes(df_export)
        st.download_button("Download students.csv", b, file_name="students.csv", mime="text/csv")

def courses_page():
    st.header("📘 Course Management")
    df = query_df("SELECT id, code, name, capacity FROM courses")
    st.dataframe(df)

    st.markdown("#### ➕ Add Course")
    code = st.text_input("Course Code", key="c_code")
    cname = st.text_input("Course Name", key="c_name")
    cap = st.number_input("Capacity", min_value=0, step=1, key="c_cap")
    if st.button("Add Course"):
        if code.strip() == "" or cname.strip() == "":
            st.error("Course code and name required")
        else:
            try:
                run_sql("INSERT INTO courses (code, name, capacity) VALUES (?, ?, ?)",
                        (code.strip(), cname.strip(), int(cap)))
                st.success("Course added")
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("#### ✏️ Edit / Delete Course")
    if not df.empty:
        sel = st.selectbox("Select course", df["code"].tolist())
        if sel:
            rec = query_df("SELECT * FROM courses WHERE code = ?", (sel,)).iloc[0]
            new_name = st.text_input("Name", value=rec["name"], key="edit_cname")
            new_cap = st.number_input("Capacity", min_value=0, value=int(rec["capacity"]), key="edit_ccap")
            if st.button("Update Course"):
                run_sql("UPDATE courses SET name = ?, capacity = ? WHERE code = ?", (new_name.strip(), int(new_cap), sel))
                st.success("Course updated")
            if st.button("Delete Course"):
                run_sql("DELETE FROM enrollments WHERE course_code = ?", (sel,))
                run_sql("DELETE FROM courses WHERE code = ?", (sel,))
                st.success("Course deleted and enrollments removed")

    st.markdown("---")
    if st.button("Export Courses CSV"):
        df_export = query_df("SELECT code, name, capacity FROM courses")
        st.download_button("Download courses.csv", to_csv_bytes(df_export), file_name="courses.csv", mime="text/csv")

def enrollment_page():
    st.header("🧾 Enrollments & Grades")
    st.markdown("Enroll students into courses, and instructors can update grades.")

    students = query_df("SELECT student_id, name FROM students")
    courses = query_df("SELECT code, name FROM courses")

    col1, col2 = st.columns(2)
    with col1:
        sel_student = st.selectbox("Student", students["student_id"].tolist() if not students.empty else [])
    with col2:
        sel_course = st.selectbox("Course", courses["code"].tolist() if not courses.empty else [])

    if st.button("Enroll"):
        if sel_student and sel_course:
            # prevent duplicate enrollment
            exists = query_df("SELECT COUNT(*) as c FROM enrollments WHERE student_id = ? AND course_code = ?", (sel_student, sel_course)).iloc[0]["c"]
            if exists:
                st.warning("Student already enrolled in this course")
            else:
                run_sql("INSERT INTO enrollments (student_id, course_code) VALUES (?, ?)", (sel_student, sel_course))
                st.success("Enrolled")

    st.markdown("#### Current Enrollments")
    df = query_df("""
        SELECT e.id, e.student_id, s.name as student_name, e.course_code, c.name as course_name, e.grade
        FROM enrollments e
        LEFT JOIN students s ON s.student_id = e.student_id
        LEFT JOIN courses c ON c.code = e.course_code
        ORDER BY e.course_code, e.student_id
    """)
    st.dataframe(df)

    st.markdown("#### Update grade / delete enrollment")
    if not df.empty:
        sel_id = st.selectbox("Select enrollment id", df["id"].tolist())
        selected_rec = df[df["id"] == sel_id].iloc[0]
        new_grade = st.number_input("Grade (0-100)", min_value=0, max_value=100, value=int(selected_rec["grade"]) if pd.notna(selected_rec["grade"]) else 0)
        if st.button("Update Grade"):
            run_sql("UPDATE enrollments SET grade = ? WHERE id = ?", (int(new_grade), int(sel_id)))
            st.success("Grade updated")
        if st.button("Delete Enrollment"):
            run_sql("DELETE FROM enrollments WHERE id = ?", (int(sel_id),))
            st.success("Enrollment removed")

    st.markdown("---")
    if st.button("Export Enrollments CSV"):
        df_export = query_df("SELECT student_id, course_code, grade FROM enrollments")
        st.download_button("Download enrollments.csv", to_csv_bytes(df_export), file_name="enrollments.csv", mime="text/csv")

def reports_page():
    st.header("📊 Reports")
    st.markdown("Quick aggregated reports and filters.")
    # grade distribution
    df = query_df("""
        SELECT c.code AS course, c.name AS course_name, COUNT(e.id) AS enrolled, AVG(e.grade) AS avg_grade
        FROM courses c
        LEFT JOIN enrollments e ON e.course_code = c.code
        GROUP BY c.code, c.name
    """)
    st.subheader("Course summary")
    st.dataframe(df)

    # students at risk (< passing threshold)
    threshold = st.slider("At-risk threshold (grade < )", 0, 100, 50)
    at_risk = query_df("""
        SELECT s.student_id, s.name, e.course_code, e.grade
        FROM enrollments e
        JOIN students s ON s.student_id = e.student_id
        WHERE e.grade IS NOT NULL AND e.grade < ?
        ORDER BY e.grade ASC
    """, (threshold,))
    st.subheader(f"Students with grade < {threshold}")
    st.dataframe(at_risk)

    if st.button("Export summary as CSV"):
        combined = pd.concat([df, at_risk], axis=0, sort=False).fillna("")
        st.download_button("Download report.csv", to_csv_bytes(combined), file_name="report.csv", mime="text/csv")

def student_self_page(username):
    st.header("🎓 My Profile & Grades")
    # For student username, map to student_id if a student was created with the same username, else show by username
    # We'll try matching std_id == username
    df = query_df("""
        SELECT s.student_id, s.name, s.email, e.course_code, c.name as course_name, e.grade
        FROM students s
        LEFT JOIN enrollments e ON e.student_id = s.student_id
        LEFT JOIN courses c ON c.code = e.course_code
        WHERE s.student_id = ? OR s.student_id = ?
    """, (username, username))
    if df.empty:
        st.info("No student record found for your username. Contact admin.")
    else:
        st.dataframe(df)
        if st.button("Download my transcript (CSV)"):
            st.download_button("Download transcript.csv", to_csv_bytes(df), file_name="transcript.csv", mime="text/csv")

# ----------------------- App main -----------------------
def main():
    init_db()
    st.set_page_config("SDBMS (Streamlit-only)", layout="wide")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    # theme toggle UI
    with st.sidebar:
        st.title("SDBMS")
        if "theme" not in st.session_state:
            st.session_state.theme = "light"
        th = st.radio("Theme", ("light", "dark"), index=0 if st.session_state.theme == "light" else 1)
        st.session_state.theme = th
        set_theme()
        st.write("---")
        if st.session_state.logged_in:
            st.write(f"**User:** {st.session_state.username}")
            st.write(f"**Role:** {st.session_state.role}")
            if st.button("Logout"):
                logout()
        else:
            st.write("Not logged in")

    st.title("KAPE student management tool")

    if not st.session_state.logged_in:
        # show login and small info
        st.markdown("This app keeps data in a local SQLite file `sdbms.db`. A default admin account exists:")
        st.info("**username:** admin    **password:** admin123  (change it after first login)")
        login_form()
        st.markdown("---")
        st.markdown("Or use a seeded demo dataset (for testing):")
        if st.button("Seed demo data"):
            # create some demo entries
            try:
                run_sql("INSERT OR IGNORE INTO students (student_id, name, email) VALUES (?, ?, ?)", ("S1001", "Alice Kumar", "alice@uni.edu"))
                run_sql("INSERT OR IGNORE INTO students (student_id, name, email) VALUES (?, ?, ?)", ("S1002", "Ravi Patel", "ravi@uni.edu"))
                run_sql("INSERT OR IGNORE INTO courses (code, name, capacity) VALUES (?, ?, ?)", ("CS101", "Database Systems", 50))
                run_sql("INSERT OR IGNORE INTO courses (code, name, capacity) VALUES (?, ?, ?)", ("CS102", "Algorithms", 40))
                st.success("Demo data seeded. Login as 'admin' / 'admin123' to edit.")
            except Exception as e:
                st.error(f"Failed to seed demo data: {e}")

    else:
        role = st.session_state.role
        # routing menu
        if role == "Admin":
            choice = st.sidebar.selectbox("Admin Menu", ["Dashboard", "Users", "Students", "Courses", "Enrollments", "Reports"])
            if choice == "Dashboard":
                st.header("📌 Admin Dashboard")
                st.markdown("Quick stats")
                students_count = query_df("SELECT COUNT(*) as c FROM students").iloc[0]["c"]
                courses_count = query_df("SELECT COUNT(*) as c FROM courses").iloc[0]["c"]
                enroll_count = query_df("SELECT COUNT(*) as c FROM enrollments").iloc[0]["c"]
                c1, c2, c3 = st.columns(3)
                c1.metric("Students", students_count)
                c2.metric("Courses", courses_count)
                c3.metric("Enrollments", enroll_count)
            elif choice == "Users":
                admin_users_page()
            elif choice == "Students":
                students_page()
            elif choice == "Courses":
                courses_page()
            elif choice == "Enrollments":
                enrollment_page()
            elif choice == "Reports":
                reports_page()

        elif role == "Instructor":
            choice = st.sidebar.selectbox("Instructor Menu", ["My Dashboard", "Courses", "Enrollments & Grades", "Reports"])
            if choice == "My Dashboard":
                st.header("Instructor Dashboard")
                st.write("Use Enrollments & Grades to update student grades.")
            elif choice == "Courses":
                # show courses; instructors cannot create/delete (admin only) but can view
                st.header("Assigned Courses (view only)")
                st.dataframe(query_df("SELECT code, name, capacity FROM courses"))
            elif choice == "Enrollments & Grades":
                enrollment_page()
            elif choice == "Reports":
                reports_page()

        elif role == "Student":
            # student's self view
            student_self_page(st.session_state.username)

if __name__ == "__main__":
    main()
