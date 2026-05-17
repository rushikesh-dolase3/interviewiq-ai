from flask import Flask, render_template, request, session, redirect
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from flask_bcrypt import Bcrypt
import os
import psycopg2
import PyPDF2
import requests
import json
import re
from flask import flash


app = Flask(__name__)

bcrypt = Bcrypt(app)

# MySQL Connection

db = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)


cursor = db.cursor()
app.secret_key = "ai_interview_secret"
app.config['SESSION_TYPE'] = 'filesystem'

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Create uploads folder
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ================= HOME PAGE =================

@app.route('/')
def home():


# USER LOGIN CHECK
    if 'user' not in session:
        return redirect('/login')

    return render_template(
    "home.html",
    user=session['user']
)


# ================= RESUME ANALYZER PAGE =================

@app.route('/resume-analyzer')
def resume_analyzer():


# USER LOGIN CHECK
    if 'user' not in session:
        return redirect('/login')

    return render_template(
    "index.html",
    user=session['user'],
    result=session.get("result"),
    resume_score=session.get("resume_score"),
    ats_score=session.get("ats_score"),
    skills=session.get("skills"),
    questions=session.get("questions"),
    suggestions=session.get("suggestions"),
    strengths=session.get("strengths"),
    weaknesses=session.get("weaknesses"),
    missing_keywords=session.get("missing_keywords")
)



# ================= JOB MATCH PAGE =================

@app.route('/job-match')
def job_match():

    return render_template(
        "job_match.html",
        result=session.get("job_result"),
        match_score=session.get("match_score"),
        matched_skills=session.get("matched_skills"),
        missing_skills=session.get("missing_skills"),
        suggestions=session.get("job_suggestions")
    )


# ================= RESUME ANALYZER =================

@app.route('/upload', methods=['POST'])
def upload_file():

    # Check file
    if 'resume' not in request.files:
        return "No file uploaded"

    file = request.files['resume']

    if file.filename == '':
        return "No selected file"

    # Save file
    filepath = os.path.join(
        app.config['UPLOAD_FOLDER'],
        file.filename
    )

    file.save(filepath)

    # Read PDF
    text = ""

    with open(filepath, 'rb') as pdf_file:

        reader = PyPDF2.PdfReader(pdf_file)

        for page in reader.pages:

            extracted = page.extract_text()

            if extracted:
                text += extracted


    os.remove(filepath)

    # ================= AI PROMPT =================

    prompt = f"""
    You are a professional AI Resume Analyzer and Technical Interview Expert.

    Analyze the candidate resume deeply and carefully.

    IMPORTANT RULES:
    - Generate REALISTIC and PROFESSIONAL interview questions
    - Questions MUST be based on candidate projects, skills, technologies, tools, internships, and experience
    - DO NOT generate generic questions
    - Questions should sound like real software engineering interviews
    - Include Python, Flask, APIs, Database, Projects, Problem Solving, OOP, Deployment, GitHub related questions if found in resume
    - Generate 12 to 15 high-quality questions
    - ATS score should depend on resume quality
    - Suggestions should be professional and resume-specific

    Return ONLY VALID JSON.

    JSON FORMAT:

    {{
      "resume_score": 85,
      "ats_score": 80,
      "skills": [
        "Python",
        "Flask"
      ],
      "questions": [
        "Explain how you used Flask in your AI Interview Assistant project.",
        "How did you integrate APIs in your project?"
      ],
      "suggestions": [
        "Add measurable achievements in projects."
      ],
      "strengths": [
        "Strong backend development skills"
      ],
      "weaknesses": [
        "Missing cloud deployment experience"
      ],
      "missing_keywords": [
        "Docker",
        "AWS"
      ]
    }}

    Resume Content:
    {text}
    """

    # ================= API REQUEST =================

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data
        )

        result = response.json()

        print(result)

        ai_text = result['choices'][0]['message']['content']

        # Clean markdown
        ai_text = ai_text.replace("```json", "")
        ai_text = ai_text.replace("```", "")
        ai_text = ai_text.strip()

        # Convert JSON
        ai_json = json.loads(ai_text)

        # Scores
        resume_score = int(ai_json.get("resume_score", 75))
        ats_score = int(ai_json.get("ats_score", 70))

        # Data
        skills = ai_json.get("skills", [])
        questions = ai_json.get("questions", [])
        suggestions = ai_json.get("suggestions", [])
        strengths = ai_json.get("strengths", [])
        weaknesses = ai_json.get("weaknesses", [])
        missing_keywords = ai_json.get("missing_keywords", [])

    except Exception as e:

        print("ERROR:", e)

        # Fallback Data
        resume_score = 75
        ats_score = 70

        skills = [
            "Python",
            "Flask",
            "SQL",
            "GitHub",
            "REST API"
        ]

        questions = [
            "Explain the architecture of your AI Interview Assistant project.",
            "How did you handle PDF resume extraction in your Flask application?",
            "What challenges did you face while integrating OpenRouter API?",
            "How does REST API integration work in your project?",
            "Why did you choose Flask instead of Django?",
            "Explain how session management works in Flask.",
            "How would you improve the ATS score calculation system?",
            "How did you structure your backend routes in Flask?",
            "What security improvements would you add to your application?",
            "How would you deploy this project to Render or Railway?",
            "Explain the database design used in your projects.",
            "How do you debug API-related issues?",
            "What are the advantages of using Git and GitHub in development?",
            "How would you scale this application for multiple users?",
            "Explain your biggest technical challenge in this project."
        ]

        suggestions = [
            "Add quantified achievements in projects.",
            "Include deployment links and GitHub repositories.",
            "Add certifications and internship experience."
        ]

        strengths = [
            "Strong backend development skills",
            "Good API integration knowledge",
            "Practical project experience"
        ]

        weaknesses = [
            "Missing cloud deployment technologies",
            "Limited production-level experience",
            "Few measurable achievements"
        ]

        missing_keywords = [
            "Docker",
            "AWS",
            "CI/CD",
            "Redis",
            "System Design"
        ]

    # ================= SAVE SESSION =================

    session["result"] = True
    session["resume_score"] = resume_score
    session["ats_score"] = ats_score
    session["skills"] = skills
    session["questions"] = questions
    session["suggestions"] = suggestions
    session["strengths"] = strengths
    session["weaknesses"] = weaknesses
    session["missing_keywords"] = missing_keywords

    # ================= RENDER PAGE =================

    return render_template(
        "index.html",
        result=True,
        resume_score=resume_score,
        ats_score=ats_score,
        skills=skills,
        questions=questions,
        suggestions=suggestions,
        strengths=strengths,
        weaknesses=weaknesses,
        missing_keywords=missing_keywords
    )


# ================= JOB MATCH ANALYZER =================

@app.route('/job-match-analyze', methods=['POST'])
def job_match_analyze():

    file = request.files['resume']

    job_description = request.form['job_description']

    filepath = os.path.join(
        app.config['UPLOAD_FOLDER'],
        file.filename
    )

    file.save(filepath)

    # Read PDF
    text = ""

    with open(filepath, 'rb') as pdf_file:

        reader = PyPDF2.PdfReader(pdf_file)

        for page in reader.pages:

            extracted = page.extract_text()

            if extracted:
                text += extracted

    # ================= JOB MATCH PROMPT =================

    prompt = f"""
    You are an expert ATS Job Match Analyzer AI.

    Compare the resume with the job description carefully.

    IMPORTANT:
    - Match score MUST depend on actual skill matching
    - Different job descriptions MUST produce different results
    - Analyze technologies, frameworks, experience, tools, databases, cloud, backend, frontend, AI skills etc.
    - Missing skills should come from job description
    - Suggestions should help improve match score

    Return ONLY VALID JSON.

    JSON FORMAT:

    {{
      "match_score": 82,
      "matched_skills": [
        "Python",
        "Flask"
      ],
      "missing_skills": [
        "Docker",
        "AWS"
      ],
      "suggestions": [
        "Add Docker projects",
        "Learn AWS deployment"
      ]
    }}

    RESUME:
    {text}

    JOB DESCRIPTION:
    {job_description}
    """

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data
        )

        result = response.json()

        print(result)

        ai_text = result['choices'][0]['message']['content']

        ai_text = ai_text.replace("```json", "")
        ai_text = ai_text.replace("```", "")
        ai_text = ai_text.strip()

        ai_json = json.loads(ai_text)

        match_score = int(ai_json.get("match_score", 75))

        matched_skills = ai_json.get(
            "matched_skills",
            []
        )

        missing_skills = ai_json.get(
            "missing_skills",
            []
        )

        suggestions = ai_json.get(
            "suggestions",
            []
        )

    except Exception as e:

        print("ERROR:", e)

        match_score = 75

        matched_skills = [
            "Python",
            "Flask",
            "SQL"
        ]

        missing_skills = [
            "Docker",
            "AWS",
            "CI/CD"
        ]

        suggestions = [
            "Add cloud deployment projects",
            "Improve ATS keywords",
            "Mention team collaboration experience"
        ]

    # ================= SAVE SESSION =================

    session["job_result"] = True
    session["match_score"] = match_score
    session["matched_skills"] = matched_skills
    session["missing_skills"] = missing_skills
    session["job_suggestions"] = suggestions

    # ================= RENDER PAGE =================

    return render_template(
        "job_match.html",
        result=True,
        match_score=match_score,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        suggestions=suggestions
    )

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Email Validation
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'

        if not re.match(email_pattern, email):

            flash("Invalid Email Address", "error")

            return redirect('/register')

        # Password Validation
        if len(password) < 8:

            flash("Password must be at least 8 characters", "error")

            return redirect('/register')

        # Check Existing Email
        sql = "SELECT * FROM users WHERE email=%s"

        cursor.execute(sql, (email,))

        existing_user = cursor.fetchone()

        if existing_user:

            flash("Email already registered", "error")

            return redirect('/register')

        # Hash Password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Insert User
        sql = "INSERT INTO users(name, email, password) VALUES(%s,%s,%s)"

        values = (name, email, hashed_password)

        cursor.execute(sql, values)

        db.commit()

        flash("Registration Successful! Please Login", "success")

        return redirect('/login')

    return render_template("register.html")


# ================= LOGIN =================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        sql = "SELECT * FROM users WHERE email=%s"

        cursor.execute(sql, (email,))

        user = cursor.fetchone()

        if user:

            if bcrypt.check_password_hash(user['password'], password):

                session['user'] = user['name']

                return redirect('/')

        flash("Invalid Email or Password", "error")

        return redirect('/login')

    return render_template("login.html")


# ================= LOGOUT =================

@app.route('/logout')
def logout():

    # PURE SESSION CLEAR
    session.clear()

    return redirect('/login')

# ================= RUN APP =================

if __name__ == "__main__":
    app.run(debug=True)