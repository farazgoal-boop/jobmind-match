from collections import Counter
from typing import Dict, List

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


BOOST_SKILLS = {
    "python": 0.08,
    "flask": 0.07,
    "django": 0.08,
    "fastapi": 0.06,
    "api": 0.04,
    "sql": 0.04,
    "sqlalchemy": 0.04,
    "docker": 0.03,
    "javascript": 0.03,
}

NEGATIVE_SIGNALS = {
    "senior": 0.08,
    "staff": 0.08,
    "principal": 0.08,
    "lead": 0.06,
    "manager": 0.08,
    "react": 0.05,
    "frontend": 0.05,
    "android": 0.05,
    "ios": 0.05,
    "devops": 0.07,
    "qa": 0.06,
}

POSITIVE_SIGNALS = {
    "junior": 0.06,
    "entry": 0.06,
    "associate": 0.04,
    "backend": 0.04,
    "full stack": 0.03,
    "full-stack": 0.03,
    "remote": 0.02,
}


def rank_jobs(candidate_text: str, jobs: List[Dict], top_k: int = 5) -> List[Dict]:
    if not jobs:
        return []

    if HAS_SKLEARN:
        return _rank_jobs_sklearn(candidate_text, jobs, top_k)
    return _rank_jobs_light(candidate_text, jobs, top_k)


def _rank_jobs_sklearn(candidate_text: str, jobs: List[Dict], top_k: int) -> List[Dict]:
    normalized_candidate = candidate_text.lower()
    candidate_skill_hits = _extract_candidate_skills(normalized_candidate)
    job_docs = [f"{j['title']} {j['description']}" for j in jobs]
    corpus = [candidate_text] + job_docs

    vectorizer = TfidfVectorizer(stop_words="english", max_features=3000)
    matrix = vectorizer.fit_transform(corpus)

    candidate_vec = matrix[0:1]
    jobs_vec = matrix[1:]
    base_scores = cosine_similarity(candidate_vec, jobs_vec).flatten()

    ranked = []
    for idx, job in enumerate(jobs):
        boosted, diagnostics = _score_job(base_scores[idx], candidate_skill_hits, job)
        ranked.append(
            {
                "job": job,
                "score": round(float(boosted), 4),
                "reason": _build_reason(job, boosted, diagnostics),
                "matched_skills": diagnostics["matched_skills"],
                "missing_skills": diagnostics["missing_skills"],
            }
        )

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:top_k]


def _rank_jobs_light(candidate_text: str, jobs: List[Dict], top_k: int) -> List[Dict]:
    normalized_candidate = candidate_text.lower()
    candidate_skill_hits = _extract_candidate_skills(normalized_candidate)
    candidate_tokens = set(normalized_candidate.split())

    ranked = []
    for job in jobs:
        job_text = f"{job['title']} {job['description']}".lower()
        job_tokens = set(job_text.split())
        overlap = len(candidate_tokens & job_tokens)
        base = min(overlap / max(len(candidate_tokens), 1), 0.65)
        boosted, diagnostics = _score_job(base, candidate_skill_hits, job)
        ranked.append(
            {
                "job": job,
                "score": round(float(boosted), 4),
                "reason": _build_reason(job, boosted, diagnostics),
                "matched_skills": diagnostics["matched_skills"],
                "missing_skills": diagnostics["missing_skills"],
            }
        )

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:top_k]


def _apply_keyword_boost(score: float, candidate_text: str, job: Dict) -> float:
    text = f"{candidate_text} {job['title']} {job['description']}".lower()
    bonus = sum(weight for key, weight in BOOST_SKILLS.items() if key in text)
    return min(score + bonus, 1.0)


def _extract_candidate_skills(candidate_text: str) -> Counter:
    return Counter(skill for skill in BOOST_SKILLS if skill in candidate_text)


def _score_job(score: float, candidate_skill_hits: Counter, job: Dict) -> tuple[float, Dict]:
    job_text = f"{job['title']} {job['description']} {job.get('location', '')}".lower()

    matched_skills = [skill for skill in candidate_skill_hits if skill in job_text]
    missing_skills = [skill for skill in candidate_skill_hits if skill not in job_text]

    boost = sum(BOOST_SKILLS[skill] for skill in matched_skills)
    positive = sum(weight for signal, weight in POSITIVE_SIGNALS.items() if signal in job_text)
    negative = sum(weight for signal, weight in NEGATIVE_SIGNALS.items() if signal in job_text)

    if matched_skills:
        boost += min(len(matched_skills) * 0.015, 0.08)

    adjusted = max(0.0, min(score + boost + positive - negative, 1.0))
    return adjusted, {
        "matched_skills": matched_skills,
        "missing_skills": missing_skills[:4],
        "positive": round(positive, 3),
        "negative": round(negative, 3),
    }


def _build_reason(job: Dict, score: float, diagnostics: Dict) -> str:
    matched = diagnostics["matched_skills"]
    if matched:
        matched_label = ", ".join(skill.upper() for skill in matched[:3])
    else:
        matched_label = "no direct stack overlap"

    if score >= 0.7:
        return f"High match: aligned with {matched_label}"
    if score >= 0.45:
        return f"Moderate match: partial fit via {matched_label}"
    return f"Low match: limited fit, {matched_label}"
