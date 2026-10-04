"""Hackathon Management System - simple Streamlit front end for MySQL.
Run:  streamlit run app.py
"""
import os
import datetime as dt

import mysql.connector
import pandas as pd
import streamlit as st
from mysql.connector import Error

st.set_page_config(page_title="Hackathon Manager", page_icon="🏆", layout="wide")


def _cfg(key, default=""):
    """Read a setting from environment variables, then Streamlit secrets."""
    val = os.getenv(key)
    if val:
        return val
    try:
        return str(st.secrets[key])
    except Exception:
        return default


DB = dict(
    host=_cfg("DB_HOST", "localhost"),
    port=int(_cfg("DB_PORT", "3306")),
    user=_cfg("DB_USER", "root"),
    password=_cfg("DB_PASSWORD", ""),
    database=_cfg("DB_NAME", "hackathon_db"),
)
BASE = os.path.dirname(os.path.abspath(__file__))


# ---------- helpers ----------
def run(sql, params=None, fetch=False):
    conn = mysql.connector.connect(**DB)
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        if fetch:
            return cur.fetchall()
        conn.commit()
    finally:
        conn.close()


def call_proc(name, args):
    conn = mysql.connector.connect(**DB)
    try:
        cur = conn.cursor()
        cur.callproc(name, args)
        conn.commit()
    finally:
        conn.close()


def split_sql(text):
    """Split a .sql file into statements, honouring DELIMITER changes."""
    stmts, buf, delim = [], [], ";"
    for line in text.splitlines():
        if line.strip().upper().startswith("DELIMITER"):
            delim = line.split()[1]
            continue
        buf.append(line)
        stmt = "\n".join(buf).strip()
        if stmt.endswith(delim):
            stmt = stmt[: -len(delim)].strip()
            if stmt:
                stmts.append(stmt)
            buf = []
    return stmts


def run_script(filename):
    """Run a .sql file from the project folder (used by the setup button)."""
    with open(os.path.join(BASE, filename), encoding="utf-8") as f:
        stmts = split_sql(f.read())
    conn = mysql.connector.connect(host=DB["host"], port=DB["port"], user=DB["user"],
                                   password=DB["password"])
    try:
        cur = conn.cursor()
        for s in stmts:
            cur.execute(s)
            if cur.with_rows:
                cur.fetchall()
        conn.commit()
    finally:
        conn.close()


def show(sql, params=None):
    rows = run(sql, params, fetch=True)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No records found.")


def do(action, ok="Done"):
    try:
        action()
        st.success(ok)
    except Error as e:
        st.error(f"Database error: {e.msg}")


def pick(label, sql, id_col, name_col, key):
    rows = run(sql, fetch=True)
    if not rows:
        st.info(f"No options available for: {label}")
        return None
    names = {r[id_col]: r[name_col] for r in rows}
    return st.selectbox(label, list(names), format_func=names.get, key=key)


def delete_tab(tbl, pk, pick_sql, name_col, key):
    rid = pick("Select record to delete", pick_sql, pk, name_col, f"del_{key}")
    if rid and st.button("Delete", key=f"btn_{key}", type="primary"):
        do(lambda: run(f"DELETE FROM {tbl} WHERE {pk}=%s", (rid,)), "Deleted")


# ---------- pages ----------
def page_participants():
    st.header("Participants")
    v, a, u, d = st.tabs(["View", "Add", "Update", "Delete"])
    with v:
        show("SELECT * FROM participants ORDER BY participant_id")
    with a:
        with st.form("p_add", clear_on_submit=True):
            n = st.text_input("Full name")
            e = st.text_input("Email")
            c = st.text_input("College")
            if st.form_submit_button("Add"):
                do(lambda: run("INSERT INTO participants (full_name,email,college) VALUES (%s,%s,%s)",
                               (n, e, c)), "Participant added")
    with u:
        pid = pick("Participant", "SELECT participant_id, full_name FROM participants",
                   "participant_id", "full_name", "p_upd")
        if pid:
            r = run("SELECT * FROM participants WHERE participant_id=%s", (pid,), True)[0]
            with st.form(f"p_upd_{pid}"):
                n = st.text_input("Full name", r["full_name"])
                e = st.text_input("Email", r["email"])
                c = st.text_input("College", r["college"])
                if st.form_submit_button("Update"):
                    do(lambda: run("UPDATE participants SET full_name=%s,email=%s,college=%s "
                                   "WHERE participant_id=%s", (n, e, c, pid)), "Updated")
    with d:
        delete_tab("participants", "participant_id",
                   "SELECT participant_id, full_name FROM participants", "full_name", "p")


def page_hackathons():
    st.header("Hackathons")
    v, a, u, d = st.tabs(["View", "Add", "Update", "Delete"])
    with v:
        show("SELECT * FROM hackathons")
    with a:
        with st.form("h_add", clear_on_submit=True):
            title = st.text_input("Title")
            s = st.date_input("Start date", dt.date.today())
            e = st.date_input("End date", dt.date.today() + dt.timedelta(days=2))
            m = st.number_input("Max team size", 1, 6, 4)
            if st.form_submit_button("Add"):
                do(lambda: run("INSERT INTO hackathons (title,start_date,end_date,max_team_size) "
                               "VALUES (%s,%s,%s,%s)", (title, s, e, m)), "Hackathon added")
    with u:
        hid = pick("Hackathon", "SELECT hackathon_id, title FROM hackathons",
                   "hackathon_id", "title", "h_upd")
        if hid:
            r = run("SELECT * FROM hackathons WHERE hackathon_id=%s", (hid,), True)[0]
            with st.form(f"h_upd_{hid}"):
                title = st.text_input("Title", r["title"])
                s = st.date_input("Start date", r["start_date"])
                e = st.date_input("End date", r["end_date"])
                m = st.number_input("Max team size", 1, 6, int(r["max_team_size"]))
                if st.form_submit_button("Update"):
                    do(lambda: run("UPDATE hackathons SET title=%s,start_date=%s,end_date=%s,"
                                   "max_team_size=%s WHERE hackathon_id=%s",
                                   (title, s, e, m, hid)), "Updated")
    with d:
        delete_tab("hackathons", "hackathon_id",
                   "SELECT hackathon_id, title FROM hackathons", "title", "h")


def page_teams():
    st.header("Teams")
    v, r, m, d = st.tabs(["View", "Register team", "Add member", "Delete"])
    with v:
        st.caption("Team sizes (view v_team_sizes)")
        show("SELECT * FROM v_team_sizes")
        st.caption("Members")
        show("SELECT t.team_name, p.full_name, p.college, tm.role "
             "FROM team_members tm JOIN teams t ON t.team_id=tm.team_id "
             "JOIN participants p ON p.participant_id=tm.participant_id "
             "ORDER BY t.team_name, tm.role")
    with r:
        st.caption("Uses stored procedure register_team (team + leader saved in one transaction)")
        hid = pick("Hackathon", "SELECT hackathon_id, title FROM hackathons",
                   "hackathon_id", "title", "tr_h")
        leader = pick("Team leader", "SELECT participant_id, full_name FROM participants",
                      "participant_id", "full_name", "tr_l")
        name = st.text_input("Team name")
        if hid and leader and st.button("Register team", type="primary"):
            do(lambda: call_proc("register_team", (hid, name, leader)), "Team registered")
    with m:
        team = pick("Team", "SELECT t.team_id, CONCAT(t.team_name,' (',h.title,')') AS label "
                            "FROM teams t JOIN hackathons h ON h.hackathon_id=t.hackathon_id",
                    "team_id", "label", "tm_t")
        part = pick("Participant", "SELECT participant_id, full_name FROM participants",
                    "participant_id", "full_name", "tm_p")
        if team and part and st.button("Add to team"):
            do(lambda: run("INSERT INTO team_members (team_id,participant_id) VALUES (%s,%s)",
                           (team, part)), "Member added")
    with d:
        delete_tab("teams", "team_id", "SELECT team_id, team_name FROM teams", "team_name", "t")


def page_judges():
    st.header("Judges")
    v, a, u, d = st.tabs(["View", "Add", "Update", "Delete"])
    with v:
        show("SELECT * FROM judges")
    with a:
        with st.form("j_add", clear_on_submit=True):
            n = st.text_input("Name")
            e = st.text_input("Email")
            x = st.text_input("Expertise")
            if st.form_submit_button("Add"):
                do(lambda: run("INSERT INTO judges (judge_name,email,expertise) VALUES (%s,%s,%s)",
                               (n, e, x)), "Judge added")
    with u:
        jid = pick("Judge", "SELECT judge_id, judge_name FROM judges", "judge_id", "judge_name", "j_upd")
        if jid:
            r = run("SELECT * FROM judges WHERE judge_id=%s", (jid,), True)[0]
            with st.form(f"j_upd_{jid}"):
                n = st.text_input("Name", r["judge_name"])
                e = st.text_input("Email", r["email"])
                x = st.text_input("Expertise", r["expertise"] or "")
                if st.form_submit_button("Update"):
                    do(lambda: run("UPDATE judges SET judge_name=%s,email=%s,expertise=%s "
                                   "WHERE judge_id=%s", (n, e, x, jid)), "Updated")
    with d:
        delete_tab("judges", "judge_id", "SELECT judge_id, judge_name FROM judges", "judge_name", "j")


def page_submissions():
    st.header("Submissions")
    v, a, u, d = st.tabs(["View", "Submit project", "Update", "Delete"])
    with v:
        show("SELECT s.submission_id, t.team_name, s.project_title, s.repo_url "
             "FROM submissions s JOIN teams t ON t.team_id=s.team_id")
    with a:
        team = pick("Team (without submission)",
                    "SELECT team_id, team_name FROM teams WHERE team_id NOT IN "
                    "(SELECT team_id FROM submissions)", "team_id", "team_name", "s_t")
        title = st.text_input("Project title")
        url = st.text_input("Repository URL")
        if team and st.button("Submit", type="primary"):
            do(lambda: run("INSERT INTO submissions (team_id,project_title,repo_url) "
                           "VALUES (%s,%s,%s)", (team, title, url)), "Submitted")
    with u:
        sid = pick("Submission", "SELECT submission_id, project_title FROM submissions",
                   "submission_id", "project_title", "s_upd")
        if sid:
            r = run("SELECT * FROM submissions WHERE submission_id=%s", (sid,), True)[0]
            with st.form(f"s_upd_{sid}"):
                title = st.text_input("Project title", r["project_title"])
                url = st.text_input("Repository URL", r["repo_url"])
                if st.form_submit_button("Update"):
                    do(lambda: run("UPDATE submissions SET project_title=%s, repo_url=%s "
                                   "WHERE submission_id=%s", (title, url, sid)), "Updated")
    with d:
        delete_tab("submissions", "submission_id",
                   "SELECT submission_id, project_title FROM submissions", "project_title", "s")


def page_scoring():
    st.header("Scoring")
    v, a, d = st.tabs(["View", "Add / Update score", "Delete"])
    with v:
        show("SELECT sc.score_id, t.team_name, j.judge_name, sc.innovation, sc.technical, sc.presentation "
             "FROM scores sc JOIN submissions s ON s.submission_id=sc.submission_id "
             "JOIN teams t ON t.team_id=s.team_id JOIN judges j ON j.judge_id=sc.judge_id "
             "ORDER BY t.team_name")
    with a:
        sub = pick("Submission", "SELECT s.submission_id, CONCAT(t.team_name,' - ',s.project_title) "
                                 "AS label FROM submissions s JOIN teams t ON t.team_id=s.team_id",
                   "submission_id", "label", "sc_s")
        judge = pick("Judge", "SELECT judge_id, judge_name FROM judges", "judge_id", "judge_name", "sc_j")
        i = st.slider("Innovation", 0, 10, 5)
        tc = st.slider("Technical", 0, 10, 5)
        p = st.slider("Presentation", 0, 10, 5)
        if sub and judge and st.button("Save score", type="primary"):
            do(lambda: run(
                "INSERT INTO scores (submission_id,judge_id,innovation,technical,presentation) "
                "VALUES (%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE innovation=VALUES(innovation), "
                "technical=VALUES(technical), presentation=VALUES(presentation)",
                (sub, judge, i, tc, p)), "Score saved")
    with d:
        delete_tab("scores", "score_id",
                   "SELECT sc.score_id, CONCAT(t.team_name,' / ',j.judge_name) AS label "
                   "FROM scores sc JOIN submissions s ON s.submission_id=sc.submission_id "
                   "JOIN teams t ON t.team_id=s.team_id JOIN judges j ON j.judge_id=sc.judge_id",
                   "label", "sc")


def page_leaderboard():
    st.header("🥇 Leaderboard")
    hid = pick("Hackathon", "SELECT hackathon_id, title FROM hackathons",
               "hackathon_id", "title", "lb_h")
    if hid:
        show("SELECT team_rank, team_name, project_title, judges_count, avg_total FROM v_leaderboard "
             "WHERE hackathon_id=%s ORDER BY team_rank", (hid,))


REPORTS = {
    "Team members (JOIN)":
        "SELECT h.title, t.team_name, p.full_name, tm.role\n"
        "FROM team_members tm\n"
        "JOIN teams t ON t.team_id = tm.team_id\n"
        "JOIN hackathons h ON h.hackathon_id = t.hackathon_id\n"
        "JOIN participants p ON p.participant_id = tm.participant_id\n"
        "ORDER BY h.title, t.team_name",
    "Participants per college (GROUP BY)":
        "SELECT college, COUNT(*) AS participants\n"
        "FROM participants\nGROUP BY college\nORDER BY participants DESC",
    "Teams without a submission (LEFT JOIN)":
        "SELECT t.team_name\nFROM teams t\n"
        "LEFT JOIN submissions s ON s.team_id = t.team_id\nWHERE s.submission_id IS NULL",
    "Teams scoring above average (subquery)":
        "SELECT team_name, avg_total FROM v_leaderboard\n"
        "WHERE avg_total > (SELECT AVG(avg_total) FROM v_leaderboard)",
    "Judge strictness (average given)":
        "SELECT j.judge_name,\n"
        "       ROUND(AVG(sc.innovation + sc.technical + sc.presentation), 2) AS avg_given\n"
        "FROM judges j JOIN scores sc ON sc.judge_id = j.judge_id\n"
        "GROUP BY j.judge_name ORDER BY avg_given",
}


def page_reports():
    st.header("SQL Reports")
    name = st.selectbox("Choose a query", list(REPORTS))
    st.code(REPORTS[name], language="sql")
    if st.button("Run query"):
        try:
            show(REPORTS[name])
        except Error as e:
            st.error(f"Database error: {e.msg}")


def page_dashboard():
    st.title("🏆 Hackathon Management System")
    items = {"Participants": "participants", "Hackathons": "hackathons", "Teams": "teams",
             "Submissions": "submissions", "Judges": "judges", "Scores": "scores"}
    for col, (label, tbl) in zip(st.columns(len(items)), items.items()):
        col.metric(label, run(f"SELECT COUNT(*) AS c FROM {tbl}", fetch=True)[0]["c"])
    st.subheader("Top teams")
    show("SELECT team_rank, team_name, project_title, avg_total FROM v_leaderboard "
         "ORDER BY hackathon_id, team_rank LIMIT 5")


PAGES = {
    "Dashboard": page_dashboard, "Participants": page_participants,
    "Hackathons": page_hackathons, "Teams": page_teams,
    "Submissions": page_submissions, "Judges": page_judges, "Scoring": page_scoring,
    "Leaderboard": page_leaderboard,
    "SQL Reports": page_reports,
}
choice = st.sidebar.radio("Menu", list(PAGES))

with st.sidebar.expander("⚙️ First-time setup"):
    st.caption("Creates the tables, views, triggers and procedure. "
               "Warning: this DROPS and recreates the database hackathon_db.")
    with_sample = st.checkbox("Also load sample data", value=True)
    if st.button("Create database"):
        try:
            run_script("schema.sql")
            if with_sample:
                run_script("sample_data.sql")
            st.success("Database ready. Open any page from the menu.")
        except Error as e:
            st.error(f"Setup failed: {e.msg}")

try:
    PAGES[choice]()
except Error as e:
    st.error(f"Could not reach the database: {e.msg}. Check DB_* settings, then use 'First-time setup' in the sidebar.")
