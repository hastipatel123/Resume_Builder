import os
import json
import uuid
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

from database import get_connection
from config import FLASK_DEBUG

from werkzeug.utils import secure_filename
from pypdf import PdfReader

from nlp_engine import (
    analyze_resume,
    analyze_job,
    calculate_similarity,
    find_matching_keywords
)

from psycopg2.extras import Json


app = Flask(__name__, template_folder="../frontend")
CORS(app)

# ---------------------------------------------------------
# UPLOAD CONFIGURATION
# ---------------------------------------------------------

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# =========================================================
# FRONTEND PAGES
# =========================================================

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


@app.route("/recruiter")
def recruiter_dashboard_page():
    return render_template("recruiter_dashboard.html")


@app.route("/resume")
def resume_page():
    return render_template("resume.html")


@app.route("/jobs")
def jobs_page():
    return render_template("jobs.html")


# =========================================================
# REGISTER
# =========================================================

@app.route("/api/register", methods=["POST"])
def register():

    data = request.get_json()

    if not data:
        return jsonify({"message": "Invalid request"}), 400

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "candidate")

    if not name or not email or not password:
        return jsonify({
            "message": "All fields are required"
        }), 400

    if role not in ("candidate", "recruiter", "admin"):
        return jsonify({
            "message": "Invalid role"
        }), 400

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            "SELECT user_id FROM users WHERE email = %s",
            (email,)
        )

        if cursor.fetchone():

            return jsonify({
                "message": "Email already registered"
            }), 409

        cursor.execute(
            """
            INSERT INTO users
            (name, email, password, role)
            VALUES (%s, %s, %s, %s)
            RETURNING user_id
            """,
            (name, email, password, role)
        )

        user_id = cursor.fetchone()[0]

        connection.commit()

        return jsonify({
            "message": "Registration successful",
            "user_id": user_id
        }), 201

    except Exception as e:

        connection.rollback()

        return jsonify({
            "message": "Registration failed",
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        connection.close()


# =========================================================
# LOGIN
# =========================================================

@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json()

    if not data:
        return jsonify({
            "message": "Invalid request"
        }), 400

    email = data.get("email")
    password = data.get("password")
    role = data.get("role")

    if not email or not password or not role:
        return jsonify({
            "message": "Email, password and role are required"
        }), 400

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            SELECT user_id, name, password, role
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()

    finally:

        cursor.close()
        connection.close()

    if not user:

        return jsonify({
            "message": "Invalid email or password"
        }), 401

    if user[2] != password:

        return jsonify({
            "message": "Invalid email or password"
        }), 401

    if user[3] != role:

        return jsonify({
            "message": "Incorrect role selected"
        }), 401

    return jsonify({
        "message": "Login successful",
        "user_id": user[0],
        "name": user[1],
        "role": user[3]
    }), 200


# =========================================================
# GET USER
# =========================================================

def get_user(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            SELECT user_id, name, email, role
            FROM users
            WHERE user_id = %s
            """,
            (user_id,)
        )

        user = cursor.fetchone()

        return user

    finally:

        cursor.close()
        connection.close()


# =========================================================
# EXTRACT TEXT FROM PDF
# =========================================================

def extract_pdf_text(file_path):

    reader = PdfReader(file_path)

    text = ""

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text.strip()


# =========================================================
# RESUME UPLOAD
# =========================================================

@app.route("/api/resume/upload", methods=["POST"])
def upload_resume():

    user_id = request.form.get("user_id")
    uploaded_file = request.files.get("resume")

    # Validate user ID
    if not user_id:
        return jsonify({
            "message": "user_id is required"
        }), 400

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return jsonify({
            "message": "Invalid user_id"
        }), 400

    # Validate uploaded file
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({
            "message": "Please select a PDF resume"
        }), 400

    # Check that the user exists and is a candidate
    user = get_user(user_id)

    if not user:
        return jsonify({
            "message": "User not found"
        }), 404

    if user[3] != "candidate":
        return jsonify({
            "message": "Only candidates can upload resumes"
        }), 403

    # Validate filename and file type
    original_filename = secure_filename(uploaded_file.filename)

    if not original_filename:
        return jsonify({
            "message": "Invalid file name"
        }), 400

    if not original_filename.lower().endswith(".pdf"):
        return jsonify({
            "message": "Only PDF files are allowed"
        }), 400

    # Create a unique filename to avoid overwriting older uploads
    unique_filename = (
        f"{user_id}_{uuid.uuid4().hex}_{original_filename}"
    )

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        unique_filename
    )

    # Save and extract the PDF
    try:
        uploaded_file.save(file_path)
        extracted_text = extract_pdf_text(file_path)

        if not extracted_text.strip():
            os.remove(file_path)

            return jsonify({
                "message": "No readable text found in PDF"
            }), 400

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)

        return jsonify({
            "message": "Unable to read PDF",
            "error": str(e)
        }), 400

    # Analyze the resume
    try:
        analysis = analyze_resume(extracted_text)

        skills = analysis.get("skills", [])
        keywords = analysis.get("keywords", [])
        education = analysis.get("education", "")
        experience = analysis.get("experience", "")
        projects = analysis.get("projects", "")

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)

        return jsonify({
            "message": "Resume analysis failed",
            "error": str(e)
        }), 500

    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Save resume details
        cursor.execute(
            """
            INSERT INTO resumes
                (user_id, filename, file_path, extracted_text)
            VALUES (%s, %s, %s, %s)
            RETURNING resume_id
            """,
            (
                user_id,
                original_filename,
                file_path,
                extracted_text
            )
        )

        resume_id = cursor.fetchone()[0]

        # Save NLP results
        cursor.execute(
            """
            INSERT INTO resume_nlp
                (
                    resume_id,
                    skills,
                    keywords,
                    education,
                    experience,
                    projects
                )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                resume_id,
                Json(skills),
                Json(keywords),
                education,
                experience,
                projects
            )
        )

        connection.commit()

    except Exception as e:
        connection.rollback()

        if os.path.exists(file_path):
            os.remove(file_path)

        return jsonify({
            "message": "Failed to save resume",
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        connection.close()

    # Match the newly saved resume against jobs
    matches = match_resume_with_jobs(
        resume_id,
        extracted_text
    )

    # Return the new analysis to the browser immediately
    return jsonify({
        "message": "Resume uploaded and analyzed successfully",
        "resume_id": resume_id,
        "filename": original_filename,
        "skills": skills,
        "keywords": keywords,
        "education": education,
        "experience": experience,
        "projects": projects,
        "matches": matches
    }), 201

# =========================================================
# MATCH RESUME WITH ALL JOBS
# =========================================================

def match_resume_with_jobs(resume_id, resume_text):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                job_id,
                title,
                company,
                description
            FROM jobs
            ORDER BY created_at DESC
            """
        )

        jobs = cursor.fetchall()

        # Analyze resume only once
        resume_analysis = analyze_resume(resume_text)

        resume_skills = set(
            resume_analysis["skills"]
        )

        matches = []

        for job in jobs:

            job_id = job[0]
            title = job[1]
            company = job[2]
            description = job[3]

            # ---------------------------------------------
            # Analyze Job
            # ---------------------------------------------

            job_analysis = analyze_job(description)

            job_skills = set(
                job_analysis["skills"]
            )

            # ---------------------------------------------
            # Skill Matching
            # ---------------------------------------------

            common_skills = sorted(
                resume_skills.intersection(job_skills)
            )

            if job_skills:

                skill_score = (
                    len(common_skills) /
                    len(job_skills)
                ) * 100

            else:

                skill_score = 0

            # ---------------------------------------------
            # TF-IDF similarity
            # ---------------------------------------------

            similarity_score = calculate_similarity(
                resume_text,
                description
            )

            # ---------------------------------------------
            # Final Score
            # ---------------------------------------------

            final_score = (
                (similarity_score * 0.70)
                +
                (skill_score * 0.30)
            )

            final_score = round(
                final_score,
                2
            )

            # ---------------------------------------------
            # Matching Keywords
            # ---------------------------------------------

            matching_keywords = (
                find_matching_keywords(
                    resume_text,
                    description
                )
            )

            # ---------------------------------------------
            # Save Job NLP
            # ---------------------------------------------

            cursor.execute(
                """
                INSERT INTO job_nlp
                (
                    job_id,
                    skills,
                    keywords
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (job_id)
                DO UPDATE SET
                    skills = EXCLUDED.skills,
                    keywords = EXCLUDED.keywords
                """,
                (
                    job_id,
                    Json(job_analysis["skills"]),
                    Json(job_analysis["keywords"])
                )
            )

            # ---------------------------------------------
            # Save Match
            # ---------------------------------------------

            cursor.execute(
                """
                INSERT INTO job_matches
                (
                    resume_id,
                    job_id,
                    match_score,
                    matched_keywords
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (resume_id, job_id)
                DO UPDATE SET
                    match_score = EXCLUDED.match_score,
                    matched_keywords = EXCLUDED.matched_keywords
                """,
                (
                    resume_id,
                    job_id,
                    final_score,
                    Json(matching_keywords)
                )
            )

            matches.append({

                "job_id": job_id,

                "title": title,

                "company": company,

                "match_score": final_score,

                "matched_keywords":
                    matching_keywords,

                "matched_skills":
                    common_skills

            })

        connection.commit()

        # Highest score first
        matches.sort(
            key=lambda x: x["match_score"],
            reverse=True
        )

        return matches[:5]

    except Exception:

        connection.rollback()

        return []

    finally:

        cursor.close()
        connection.close()


# =========================================================
# GET RESUME NLP RESULT
# =========================================================

@app.route("/api/resume/<int:resume_id>", methods=["GET"])
def get_resume(resume_id):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                r.resume_id,
                r.user_id,
                r.filename,
                r.created_at,
                n.skills,
                n.keywords,
                n.education,
                n.experience,
                n.projects
            FROM resumes r
            JOIN resume_nlp n
                ON r.resume_id = n.resume_id
            WHERE r.resume_id = %s
            """,
            (resume_id,)
        )

        row = cursor.fetchone()

    finally:

        cursor.close()
        connection.close()

    if not row:

        return jsonify({
            "message": "Resume not found"
        }), 404

    return jsonify({

        "resume_id": row[0],

        "user_id": row[1],

        "filename": row[2],

        "created_at": row[3],

        "skills": row[4],

        "keywords": row[5],

        "education": row[6],

        "experience": row[7],

        "projects": row[8]

    }), 200


# =========================================================
# GET CANDIDATE'S LATEST RESUME
# =========================================================

@app.route(
    "/api/resume/candidate/<int:user_id>",
    methods=["GET"]
)
def get_candidate_resume(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                r.resume_id,
                r.filename,
                r.created_at,
                n.skills,
                n.keywords,
                n.education,
                n.experience,
                n.projects
            FROM resumes r
            JOIN resume_nlp n
                ON r.resume_id = n.resume_id
            WHERE r.user_id = %s
            ORDER BY r.created_at DESC, r.resume_id DESC
            LIMIT 1
            """,
            (user_id,)
        )

        row = cursor.fetchone()

    except Exception as e:
        return jsonify({
            "message": "Failed to retrieve resume",
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        connection.close()

    if not row:
        return jsonify({
            "message": "No resume found"
        }), 404

    return jsonify({
        "resume_id": row[0],
        "filename": row[1],
        "created_at": row[2],
        "skills": row[3] or [],
        "keywords": row[4] or [],
        "education": row[5] or "",
        "experience": row[6] or "",
        "projects": row[7] or ""
    }), 200

# =========================================================
# DASHBOARD
# =========================================================

@app.route(
    "/api/dashboard/<int:user_id>",
    methods=["GET"]
)
def get_dashboard(user_id):

    user = get_user(user_id)

    if not user:

        return jsonify({
            "message": "User not found"
        }), 404

    if user[3] != "candidate":

        return jsonify({
            "message": "Dashboard is available for candidates"
        }), 403

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # -------------------------------------------------
        # Number of resumes
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM resumes
            WHERE user_id = %s
            """,
            (user_id,)
        )

        resume_count = cursor.fetchone()[0]

        # -------------------------------------------------
        # Available jobs
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM jobs
            """
        )

        job_count = cursor.fetchone()[0]

        # -------------------------------------------------
        # Job matches
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM job_matches jm
            JOIN resumes r
                ON jm.resume_id = r.resume_id
            WHERE r.user_id = %s
            """,
            (user_id,)
        )

        match_count = cursor.fetchone()[0]

        # -------------------------------------------------
        # Best score
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT MAX(jm.match_score)
            FROM job_matches jm
            JOIN resumes r
                ON jm.resume_id = r.resume_id
            WHERE r.user_id = %s
            """,
            (user_id,)
        )

        best_score = cursor.fetchone()[0]

        if best_score is None:
            best_score = 0

        # -------------------------------------------------
        # Latest resume
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                r.resume_id,
                r.filename,
                r.created_at
            FROM resumes r
            WHERE r.user_id = %s
            ORDER BY r.created_at DESC
            LIMIT 1
            """,
            (user_id,)
        )

        latest = cursor.fetchone()

        latest_resume = None
        skills_found = []

        if latest:

            cursor.execute(
                """
                SELECT skills
                FROM resume_nlp
                WHERE resume_id = %s
                """,
                (latest[0],)
            )

            nlp_row = cursor.fetchone()

            if nlp_row and nlp_row[0]:

                skills_found = nlp_row[0]

            latest_resume = {

                "resume_id": latest[0],

                "filename": latest[1],

                "created_at": latest[2],

                "skills": skills_found

            }

        # -------------------------------------------------
        # Top matches
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                j.job_id,
                j.title,
                j.company,
                jm.match_score,
                jm.matched_keywords
            FROM job_matches jm

            JOIN resumes r
                ON jm.resume_id = r.resume_id

            JOIN jobs j
                ON jm.job_id = j.job_id

            WHERE r.user_id = %s

            ORDER BY jm.match_score DESC

            LIMIT 5
            """,
            (user_id,)
        )

        rows = cursor.fetchall()

        top_matches = []

        for row in rows:

            top_matches.append({

                "job_id": row[0],

                "title": row[1],

                "company": row[2],

                "match_score":
                    round(float(row[3]), 2),

                "matched_keywords":
                    row[4]

            })

        return jsonify({

            "resume_count": resume_count,

            "job_count": job_count,

            "match_count": match_count,

            "best_score":
                round(float(best_score), 2),

            "skills_found":
                skills_found,

            "latest_resume":
                latest_resume,

            "top_matches":
                top_matches

        }), 200

    finally:

        cursor.close()
        connection.close()


# =========================================================
# GET ALL JOBS FOR CANDIDATE (with match scores)
# =========================================================

@app.route("/api/jobs/candidate/<int:user_id>", methods=["GET"])
def get_jobs_for_candidate(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # Check if candidate has a resume
        cursor.execute(
            "SELECT resume_id FROM resumes WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        )
        resume_row = cursor.fetchone()
        has_resume = resume_row is not None
        resume_id  = resume_row[0] if resume_row else None

        # Fetch all jobs with match data if resume exists
        if resume_id:
            cursor.execute(
                """
                SELECT
                    j.job_id, j.title, j.company,
                    j.description, j.created_at,
                    jm.match_score, jm.matched_keywords, jm.status,
                    rn.skills AS resume_skills,
                    jn.skills AS job_skills
                FROM jobs j
                LEFT JOIN job_matches jm
                    ON j.job_id = jm.job_id AND jm.resume_id = %s
                LEFT JOIN resume_nlp rn ON rn.resume_id = %s
                LEFT JOIN job_nlp jn    ON jn.job_id = j.job_id
                ORDER BY j.created_at DESC
                """,
                (resume_id, resume_id)
            )
        else:
            cursor.execute(
                """
                SELECT
                    job_id, title, company,
                    description, created_at,
                    NULL, NULL, NULL, NULL, NULL
                FROM jobs
                ORDER BY created_at DESC
                """
            )

        rows = cursor.fetchall()

        jobs = []
        for r in rows:

            # Compute matched skills from resume_skills ∩ job_skills
            resume_skills = r[8] or []
            job_skills    = r[9] or []
            matched_skills = sorted(
                set(s.lower() for s in resume_skills)
                &
                set(s.lower() for s in job_skills)
            )

            jobs.append({
                "job_id":           r[0],
                "title":            r[1],
                "company":          r[2],
                "description":      r[3],
                "created_at":       r[4],
                "match_score":      round(float(r[5]), 2) if r[5] is not None else None,
                "matched_keywords": r[6] or [],
                "status":           r[7] or "none",
                "matched_skills":   matched_skills
            })

        return jsonify({"jobs": jobs, "has_resume": has_resume}), 200

    finally:
        cursor.close()
        connection.close()


# =========================================================
# GET ALL JOBS
# =========================================================

@app.route("/api/jobs", methods=["GET"])
def get_jobs():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                job_id,
                recruiter_id,
                title,
                company,
                description,
                created_at
            FROM jobs
            ORDER BY created_at DESC
            """
        )

        rows = cursor.fetchall()

        jobs = []

        for row in rows:

            jobs.append({

                "job_id": row[0],

                "recruiter_id": row[1],

                "title": row[2],

                "company": row[3],

                "description": row[4],

                "created_at": row[5]

            })

        return jsonify(jobs), 200

    finally:

        cursor.close()
        connection.close()


# =========================================================
# CREATE JOB
# =========================================================

@app.route("/api/jobs", methods=["POST"])
def create_job():

    data = request.get_json()

    if not data:

        return jsonify({
            "message": "Invalid request"
        }), 400

    recruiter_id = data.get("recruiter_id")
    title = data.get("title")
    company = data.get("company")
    description = data.get("description")

    if not recruiter_id or not title or not description:

        return jsonify({
            "message":
                "recruiter_id, title and description are required"
        }), 400

    try:

        recruiter_id = int(recruiter_id)

    except ValueError:

        return jsonify({
            "message": "Invalid recruiter_id"
        }), 400

    recruiter = get_user(recruiter_id)

    if not recruiter:

        return jsonify({
            "message": "Recruiter not found"
        }), 404

    if recruiter[3] != "recruiter":

        return jsonify({
            "message":
                "Only recruiters can create jobs"
        }), 403

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # -------------------------------------------------
        # Insert Job
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO jobs
            (
                recruiter_id,
                title,
                company,
                description
            )
            VALUES (%s, %s, %s, %s)
            RETURNING job_id
            """,
            (
                recruiter_id,
                title,
                company,
                description
            )
        )

        job_id = cursor.fetchone()[0]

        # -------------------------------------------------
        # NLP for Job
        # -------------------------------------------------

        job_analysis = analyze_job(description)

        cursor.execute(
            """
            INSERT INTO job_nlp
            (
                job_id,
                skills,
                keywords
            )
            VALUES (%s, %s, %s)
            """,
            (
                job_id,
                Json(job_analysis["skills"]),
                Json(job_analysis["keywords"])
            )
        )

        connection.commit()

    except Exception as e:

        connection.rollback()

        return jsonify({
            "message": "Unable to create job",
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        connection.close()

    # -----------------------------------------------------
    # Match new job with existing resumes
    # -----------------------------------------------------

    match_job_with_resumes(
        job_id,
        description
    )

    return jsonify({

        "message": "Job created successfully",

        "job_id": job_id,

        "title": title,

        "company": company

    }), 201


# =========================================================
# MATCH ONE JOB WITH ALL EXISTING RESUMES
# =========================================================

def match_job_with_resumes(job_id, job_description):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                resume_id,
                extracted_text
            FROM resumes
            WHERE extracted_text IS NOT NULL
            """
        )

        resumes = cursor.fetchall()

        job_analysis = analyze_job(
            job_description
        )

        job_skills = set(
            job_analysis["skills"]
        )

        for resume in resumes:

            resume_id = resume[0]
            resume_text = resume[1]

            resume_analysis = analyze_resume(
                resume_text
            )

            resume_skills = set(
                resume_analysis["skills"]
            )

            common_skills = sorted(
                resume_skills.intersection(
                    job_skills
                )
            )

            if job_skills:

                skill_score = (
                    len(common_skills)
                    /
                    len(job_skills)
                ) * 100

            else:

                skill_score = 0

            similarity_score = calculate_similarity(
                resume_text,
                job_description
            )

            final_score = (
                similarity_score * 0.70
                +
                skill_score * 0.30
            )

            final_score = round(
                final_score,
                2
            )

            matching_keywords = (
                find_matching_keywords(
                    resume_text,
                    job_description
                )
            )

            cursor.execute(
                """
                INSERT INTO job_matches
                (
                    resume_id,
                    job_id,
                    match_score,
                    matched_keywords
                )
                VALUES (%s, %s, %s, %s)

                ON CONFLICT (resume_id, job_id)
                DO UPDATE SET
                    match_score =
                        EXCLUDED.match_score,

                    matched_keywords =
                        EXCLUDED.matched_keywords
                """,
                (
                    resume_id,
                    job_id,
                    final_score,
                    Json(matching_keywords)
                )
            )

        connection.commit()

    except Exception:

        connection.rollback()

    finally:

        cursor.close()
        connection.close()


# =========================================================
# RECRUITER DASHBOARD STATS
# =========================================================

@app.route(
    "/api/recruiter/dashboard/<int:recruiter_id>",
    methods=["GET"]
)
def recruiter_dashboard(recruiter_id):
    user = get_user(recruiter_id)

    if not user or user[3] != "recruiter":
        return jsonify({"message": "Access denied"}), 403

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT COUNT(*)
            FROM jobs
            WHERE recruiter_id = %s
        """, (recruiter_id,))

        jobs_posted = cursor.fetchone()[0]

        cursor.execute("""
            SELECT
                COUNT(*) FILTER (
                    WHERE jm.applied_at IS NOT NULL
                ) AS total_applicants,
                COUNT(*) FILTER (
                    WHERE jm.applied_at IS NOT NULL
                    AND jm.status = 'approved'
                ) AS approved_count,
                COUNT(*) FILTER (
                    WHERE jm.applied_at IS NOT NULL
                    AND jm.status = 'rejected'
                ) AS rejected_count,
                COUNT(*) FILTER (
                    WHERE jm.applied_at IS NOT NULL
                    AND jm.status = 'pending'
                ) AS pending_count
            FROM job_matches jm
            JOIN jobs j ON j.job_id = jm.job_id
            WHERE j.recruiter_id = %s
        """, (recruiter_id,))

        row = cursor.fetchone()

        return jsonify({
            "jobs_posted": jobs_posted,
            "total_applicants": row[0],
            "approved_count": row[1],
            "rejected_count": row[2],
            "pending_count": row[3]
        }), 200

    finally:
        cursor.close()
        connection.close()


# =========================================================
# GET RECRUITER'S JOBS WITH APPLICANT COUNT
# =========================================================

@app.route(
    "/api/recruiter/<int:recruiter_id>/jobs",
    methods=["GET"]
)
def get_recruiter_jobs(recruiter_id):
    user = get_user(recruiter_id)

    if not user or user[3] != "recruiter":
        return jsonify({"message": "Access denied"}), 403

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                j.job_id,
                j.title,
                j.company,
                j.created_at,
                COUNT(jm.match_id) FILTER (
                    WHERE jm.applied_at IS NOT NULL
                ) AS applicant_count
            FROM jobs j
            LEFT JOIN job_matches jm ON j.job_id = jm.job_id
            WHERE j.recruiter_id = %s
            GROUP BY
                j.job_id, j.title, j.company, j.created_at
            ORDER BY j.created_at DESC
        """, (recruiter_id,))

        rows = cursor.fetchall()

        return jsonify([
            {
                "job_id": r[0],
                "title": r[1],
                "company": r[2],
                "created_at": r[3].isoformat() if r[3] else None,
                "applicant_count": r[4]
            }
            for r in rows
        ]), 200

    finally:
        cursor.close()
        connection.close()


# =========================================================
# GET CANDIDATES MATCHED TO A JOB
# =========================================================


@app.route(
    "/api/recruiter/jobs/<int:job_id>/candidates",
    methods=["GET"]
)
def get_job_candidates(job_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                jm.match_id,
                jm.match_score,
                jm.matched_keywords,
                jm.status,
                u.user_id,
                u.name AS candidate_name,
                u.email AS candidate_email,
                r.filename,
                rn.skills
            FROM job_matches jm
            LEFT JOIN resumes r
                ON r.resume_id = jm.resume_id
            LEFT JOIN users u
                ON u.user_id = r.user_id
            LEFT JOIN resume_nlp rn
                ON rn.resume_id = jm.resume_id
            WHERE jm.job_id = %s
              AND jm.applied_at IS NOT NULL
            ORDER BY jm.applied_at DESC, jm.match_id DESC
        """, (job_id,))

        rows = cursor.fetchall()

        candidates = []

        for r in rows:
            skills = r[8] or []

            # Handle PostgreSQL JSON values and strings safely.
            if isinstance(skills, str):
                try:
                    skills = json.loads(skills)
                except (ValueError, TypeError):
                    skills = []

            if not isinstance(skills, list):
                skills = []

            keywords = r[2] or []

            if isinstance(keywords, str):
                try:
                    keywords = json.loads(keywords)
                except (ValueError, TypeError):
                    keywords = []

            if not isinstance(keywords, list):
                keywords = []

            candidates.append({
                "match_id": r[0],
                "match_score": round(float(r[1] or 0), 2),
                "matched_keywords": keywords,
                "status": (r[3] or "pending").lower(),
                "user_id": r[4],
                "candidate_name": r[5] or "Candidate",
                "candidate_email": r[6] or "",
                "filename": r[7] or "N/A",
                "skills": skills
            })

        return jsonify(candidates), 200

    except Exception:
        app.logger.exception("Failed to load job candidates")
        return jsonify({
            "message": "Failed to load candidates. Check the Flask console."
        }), 500

    finally:
        cursor.close()
        connection.close()



# =========================================================
# APPROVE / REJECT CANDIDATE
# =========================================================

@app.route(
    "/api/recruiter/matches/<int:match_id>/status",
    methods=["PATCH"]
)
def update_match_status(match_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")

    if status not in ("pending", "approved", "rejected"):
        return jsonify({"message": "Invalid status"}), 400

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE job_matches
            SET status = %s
            WHERE match_id = %s
              AND applied_at IS NOT NULL
            RETURNING match_id
        """, (status, match_id))

        updated = cursor.fetchone()

        if not updated:
            connection.rollback()
            return jsonify({
                "message": "Application not found"
            }), 404

        connection.commit()

        return jsonify({
            "message": f"Candidate status updated to {status}.",
            "match_id": match_id,
            "status": status
        }), 200

    except Exception:
        connection.rollback()
        app.logger.exception("Candidate status update failed")

        return jsonify({
            "message": "Unable to update candidate status."
        }), 500

    finally:
        cursor.close()
        connection.close()



# =========================================================
# CANDIDATE APPLIES FOR A JOB
# =========================================================


@app.route("/api/jobs/<int:job_id>/apply", methods=["POST"])
def apply_for_job(job_id):
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"message": "user_id is required"}), 400

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid user_id"}), 400

    user = get_user(user_id)

    if not user:
        return jsonify({"message": "User not found"}), 404

    if user[3] != "candidate":
        return jsonify({"message": "Only candidates can apply"}), 403

    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Get the candidate's latest resume.
        cursor.execute("""
            SELECT resume_id, extracted_text
            FROM resumes
            WHERE user_id = %s
            ORDER BY created_at DESC, resume_id DESC
            LIMIT 1
        """, (user_id,))

        resume = cursor.fetchone()

        if not resume:
            return jsonify({
                "message": "Please upload your resume first."
            }), 400

        resume_id = resume[0]
        resume_text = resume[1] or ""

        # Check that the job exists.
        cursor.execute("""
            SELECT description
            FROM jobs
            WHERE job_id = %s
        """, (job_id,))

        job = cursor.fetchone()

        if not job:
            return jsonify({"message": "Job not found"}), 404

        job_description = job[0] or ""

        # Check whether a match/application row already exists.
        cursor.execute("""
            SELECT match_id, status, applied_at
            FROM job_matches
            WHERE resume_id = %s AND job_id = %s
            ORDER BY match_id DESC
            LIMIT 1
        """, (resume_id, job_id))

        existing = cursor.fetchone()

        if existing:
            match_id, current_status, applied_at = existing

            # A non-null applied_at means the candidate already applied.
            if applied_at is not None:
                return jsonify({
                    "message": "You have already applied for this job.",
                    "status": current_status
                }), 409

            # Convert an automatically generated match into an application.
            cursor.execute("""
                UPDATE job_matches
                SET status = 'pending',
                    applied_at = CURRENT_TIMESTAMP
                WHERE match_id = %s
            """, (match_id,))

        else:
            # Calculate a match score for a new application.
            resume_analysis = analyze_resume(resume_text)
            job_analysis = analyze_job(job_description)

            resume_skills = set(resume_analysis["skills"])
            job_skills = set(job_analysis["skills"])
            common_skills = resume_skills.intersection(job_skills)

            skill_score = (
                len(common_skills) / len(job_skills) * 100
                if job_skills else 0
            )

            similarity_score = calculate_similarity(
                resume_text, job_description
            )

            final_score = float(round(
                similarity_score * 0.70 + skill_score * 0.30, 2
            ))

            matching_keywords = find_matching_keywords(
                resume_text, job_description
            )

            cursor.execute("""
                INSERT INTO job_matches
                    (resume_id, job_id, match_score,
                     matched_keywords, status, applied_at)
                VALUES (%s, %s, %s, %s, 'pending', CURRENT_TIMESTAMP)
                RETURNING match_id
            """, (
                resume_id,
                job_id,
                final_score,
                Json(matching_keywords)
            ))

            match_id = cursor.fetchone()[0]

        connection.commit()

        return jsonify({
            "message": "Application submitted successfully!",
            "job_id": job_id,
            "match_id": match_id,
            "status": "pending"
        }), 200

    except Exception:
        connection.rollback()
        app.logger.exception("Apply for job failed")

        return jsonify({
            "message": "Unable to submit application. Check the Flask console."
        }), 500

    finally:
        cursor.close()
        connection.close()



# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/api/health")
def health():

    return jsonify({
        "status": "Backend is running"
    })


# =========================================================
# START FLASK
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=FLASK_DEBUG,
        port=5000
    )