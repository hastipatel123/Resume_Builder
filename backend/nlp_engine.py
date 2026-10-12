import re
import spacy

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# Load spaCy English model
nlp = spacy.load("en_core_web_sm")


# Skill vocabulary used by NLP
SKILL_TERMS = [
    "python",
    "java",
    "javascript",
    "typescript",
    "c",
    "c++",
    "c#",
    "php",
    "ruby",
    "kotlin",
    "swift",

    "html",
    "css",
    "bootstrap",
    "react",
    "react.js",
    "angular",
    "vue",
    "node",
    "node.js",

    "flask",
    "django",
    "spring",
    "spring boot",
    ".net",
    "asp.net",

    "sql",
    "mysql",
    "postgresql",
    "postgres",
    "oracle",
    "mongodb",

    "git",
    "github",
    "gitlab",

    "docker",
    "kubernetes",

    "aws",
    "azure",

    "tensorflow",
    "keras",
    "pytorch",
    "scikit-learn",

    "machine learning",
    "deep learning",
    "artificial intelligence",
    "natural language processing",
    "nlp",

    "pandas",
    "numpy",

    "rest api",
    "restful api",

    "microservices",

    "linux",
    "ubuntu",

    "power bi",
    "tableau",
    "excel",

    "postman",
    "jira",

    "agile",
    "scrum"
]


def clean_text(text):

    if not text:
        return ""

    text = text.lower()

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ------------------------------------------------
# SKILL EXTRACTION
# ------------------------------------------------

def extract_skills(text):

    text = clean_text(text)

    skills = set()

    for skill in SKILL_TERMS:

        pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"

        if re.search(pattern, text):

            skills.add(skill)

    return sorted(list(skills))


# ------------------------------------------------
# KEYWORD EXTRACTION
# ------------------------------------------------

def extract_keywords(text):

    text = clean_text(text)

    if not text:
        return []

    doc = nlp(text)

    keywords = set()

    for token in doc:

        if token.is_stop:
            continue

        if token.is_punct:
            continue

        if token.like_num:
            continue

        if not token.is_alpha:
            continue

        if len(token.text) < 2:
            continue

        lemma = token.lemma_.lower()

        keywords.add(lemma)

    return sorted(list(keywords))


# ------------------------------------------------
# SECTION EXTRACTION
# ------------------------------------------------

def extract_section(text, section_names, next_sections):

    if not text:
        return ""

    start_pattern = "|".join(
        re.escape(x) for x in section_names
    )

    end_pattern = "|".join(
        re.escape(x) for x in next_sections
    )

    pattern = rf"""
        (?:{start_pattern})
        \s*
        (.*?)
        (?:
            {end_pattern}
            |
            $
        )
    """

    match = re.search(
        pattern,
        text,
        re.IGNORECASE | re.DOTALL | re.VERBOSE
    )

    if match:

        return match.group(1).strip()

    return ""


def extract_sections(text):

    education = extract_section(
        text,

        [
            "education",
            "academic background",
            "educational qualification",
            "qualifications"
        ],

        [
            "experience",
            "work experience",
            "employment",
            "skills",
            "technical skills",
            "projects",
            "certifications",
            "achievements"
        ]
    )


    experience = extract_section(
        text,

        [
            "experience",
            "work experience",
            "employment",
            "professional experience"
        ],

        [
            "education",
            "skills",
            "technical skills",
            "projects",
            "certifications",
            "achievements"
        ]
    )


    projects = extract_section(
        text,

        [
            "projects",
            "academic projects",
            "personal projects"
        ],

        [
            "education",
            "experience",
            "work experience",
            "skills",
            "certifications",
            "achievements"
        ]
    )


    return {
        "education": education,
        "experience": experience,
        "projects": projects
    }


# ------------------------------------------------
# COMPLETE RESUME ANALYSIS
# ------------------------------------------------

def analyze_resume(text):

    sections = extract_sections(text)

    return {

        "skills": extract_skills(text),

        "keywords": extract_keywords(text),

        "education": sections["education"],

        "experience": sections["experience"],

        "projects": sections["projects"]
    }


# ------------------------------------------------
# JOB ANALYSIS
# ------------------------------------------------

def analyze_job(text):

    return {

        "skills": extract_skills(text),

        "keywords": extract_keywords(text)
    }


# ------------------------------------------------
# TF-IDF SIMILARITY
# ------------------------------------------------

def calculate_similarity(resume_text, job_text):

    resume_text = clean_text(resume_text)

    job_text = clean_text(job_text)

    if not resume_text or not job_text:

        return 0.0

    documents = [
        resume_text,
        job_text
    ]

    vectorizer = TfidfVectorizer(
        stop_words="english"
    )

    try:

        vectors = vectorizer.fit_transform(documents)

        score = cosine_similarity(
            vectors[0:1],
            vectors[1:2]
        )[0][0]

        return round(score * 100, 2)

    except ValueError:

        return 0.0


# ------------------------------------------------
# MATCHING KEYWORDS
# ------------------------------------------------

def find_matching_keywords(
    resume_text,
    job_text
):

    resume_keywords = set(
        extract_keywords(resume_text)
    )

    job_keywords = set(
        extract_keywords(job_text)
    )

    return sorted(
        list(
            resume_keywords.intersection(
                job_keywords
            )
        )
    )