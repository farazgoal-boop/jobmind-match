from typing import Dict, List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


BOOST_SKILLS = {
    "python": 0.08,
    "django": 0.08,
    "fastapi": 0.06,
    "api": 0.04,
    "docker": 0.03,
}


def rank_jobs(candidate_text: str, jobs: List[Dict], top_k: int = 5) -> List[Dict]:
    if not jobs:
        return []

    job_docs = [f"{j['title']} {j['description']}" for j in jobs]
    corpus = [candidate_text] + job_docs

    vectorizer = TfidfVectorizer(stop_words="english", max_features=3000)
    matrix = vectorizer.fit_transform(corpus)

    candidate_vec = matrix[0:1]
    jobs_vec = matrix[1:]
    base_scores = cosine_similarity(candidate_vec, jobs_vec).flatten()

    ranked = []
    for idx, job in enumerate(jobs):
        boosted = _apply_keyword_boost(base_scores[idx], candidate_text, job)
        ranked.append(
            {
                "job": job,
                "score": round(float(boosted), 4),
                "reason": _build_reason(job, boosted),
            }
        )

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:top_k]


def _apply_keyword_boost(score: float, candidate_text: str, job: Dict) -> float:
    text = f"{candidate_text} {job['title']} {job['description']}".lower()
    bonus = sum(weight for key, weight in BOOST_SKILLS.items() if key in text)
    return min(score + bonus, 1.0)


def _build_reason(job: Dict, score: float) -> str:
    if score >= 0.7:
        return f"High match: strong skill overlap for {job['title']}"
    if score >= 0.45:
        return f"Moderate match: partial overlap for {job['title']}"
    return f"Low match: limited overlap for {job['title']}"
