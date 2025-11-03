import os
import sys

import django
import numpy as np
import pandas as pd
from asgiref.sync import sync_to_async
from dotenv import load_dotenv
from google import genai
from sqlalchemy import create_engine

from apps.recommendation_agent.services.overlap_skill import calculate_skill_overlap_for_job_recommendation
from apps.recommendation_agent.services.weaviate_service import query_weaviate_async

load_dotenv()

# Setup Django environment FIRST before importing models
django_base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(django_base_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Careermate.settings')
django.setup()

# NOW import Django models after setup
from django.conf import settings
from apps.recommendation_agent.models import JobPostings

# Create SQLAlchemy engine from Django database settings
def get_sqlalchemy_engine():
    """Create SQLAlchemy engine from Django database settings"""
    db_settings = settings.DATABASES['default']
    engine = db_settings.get('ENGINE', '')

    if 'postgresql' in engine:
        db_url = f"postgresql://{db_settings['USER']}:{db_settings['PASSWORD']}@{db_settings['HOST']}:{db_settings.get('PORT', 5432)}/{db_settings['NAME']}"
    elif 'mysql' in engine:
        db_url = f"mysql+pymysql://{db_settings['USER']}:{db_settings['PASSWORD']}@{db_settings['HOST']}:{db_settings.get('PORT', 3306)}/{db_settings['NAME']}"
    else:
        # SQLite or other
        db_url = f"sqlite:///{db_settings['NAME']}"

    return create_engine(db_url)

# Get the correct path to the CSV file
csv_path = os.path.join(settings.BASE_DIR, 'agent_core', 'data', 'job_postings.csv')
data_jp = pd.read_csv(csv_path, encoding='latin-1')

#get data from postgres by candidateId

#init weaviate
# Initialize Gemini client
gemini_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def get_gemini_embedding(text: str):
    """Tạo vector embedding bằng Gemini (models/embedding-001)"""
    text = (text or "").strip()
    if not text:
        return None

    response = gemini_client.models.embed_content(
        model="models/embedding-001",
        contents=text
    )

    # Trả về list[float] (Weaviate yêu cầu dạng này)
    return np.array(response.embeddings[0].values, dtype=np.float32).tolist()


#Content-Based Recommendation with Skill Overlap Weighting
async def get_content_based_recommendations(query_item, top_n=5, weights=None, skill_weight=0.3, min_threshold=0.15):
    """
    Content-based recommendation with balanced scoring
    Args:
        query_item: Dict with skills, title, description
        top_n: Number of recommendations to return
        weights: Field weights for embedding (skills, title, description)
        skill_weight: Weight for skill overlap (default 0.3 - reduced to prioritize semantic)
        min_threshold: Minimum similarity score to include (default 0.15)
    """
    if weights is None:
        # Increase title weight to capture context like "Machine Learning"
        weights = {"skills": 0.4, "title": 0.4, "description": 0.2}

    # 1️⃣ Combine all fields into weighted text
    def to_text(v):
        if isinstance(v, list):
            return ", ".join(str(x) for x in v)
        return str(v or "")

    # Create weighted combined text (repeat important fields to increase their weight)
    skills_text = to_text(query_item.get("skills", ""))
    title_text = to_text(query_item.get("title", ""))
    description_text = to_text(query_item.get("description", ""))

    # Combine with weights - TITLE is now more important for context
    combined_parts = []
    if skills_text:
        combined_parts.extend([skills_text] * int(weights.get("skills", 0.4) * 10))
    if title_text:
        combined_parts.extend([title_text] * int(weights.get("title", 0.4) * 10))
    if description_text:
        combined_parts.extend([description_text] * int(weights.get("description", 0.2) * 10))

    combined_text = " ".join(combined_parts)

    # 2️⃣ Create single embedding
    vector = get_gemini_embedding(combined_text)

    # 3️⃣ Query Weaviate with more results for filtering
    results = await query_weaviate_async(vector, limit=top_n * 5)  # Get 5x more for filtering

    # 4️⃣ Calculate hybrid scores with balanced approach
    query_skills = query_item.get("skills", [])
    if isinstance(query_skills, str):
        query_skills = [s.strip() for s in query_skills.split(",")]

    query_title = query_item.get("title", "").lower()

    formatted_results = []
    for job in results:
        # Parse job skills
        job_skills_text = job["skills"]
        if isinstance(job_skills_text, str):
            job_skills = [s.strip() for s in job_skills_text.split(",") if s.strip()]
        else:
            job_skills = []

        # Calculate semantic similarity (from vector distance)
        semantic_similarity = 1 - job["distance"]

        # Calculate skill overlap score
        skill_overlap_score = calculate_skill_overlap_for_job_recommendation(query_skills, job_skills)

        # 🔥 Title context boost - if query title matches job title/description
        title_context_boost = 0.0
        if query_title:
            job_title_lower = job["title"].lower()
            job_desc_lower = job.get("description", "").lower()

            # Check for key terms from query title in job
            query_title_terms = set(query_title.split())
            job_title_terms = set(job_title_lower.split())

            # Boost if there's overlap in title terms
            common_title_terms = query_title_terms.intersection(job_title_terms)
            if common_title_terms:
                title_context_boost = 0.1 * len(common_title_terms)  # 10% per common term
                title_context_boost = min(title_context_boost, 0.2)  # Cap at 20%

        # 🎯 BALANCED hybrid score: semantic > skill overlap
        # Semantic similarity is PRIMARY (70%), skill overlap is SECONDARY (30%)
        base_score = (1 - skill_weight) * semantic_similarity + skill_weight * skill_overlap_score
        hybrid_score = base_score + title_context_boost

        # ⚠️ Only include jobs above minimum threshold
        if hybrid_score >= min_threshold:
            formatted_results.append({
                "job_id": job["job_id"],
                "title": job["title"],
                "skills": job["skills"],
                "description": job.get("description", ""),
                "semantic_similarity": round(semantic_similarity, 4),
                "skill_overlap": round(skill_overlap_score, 4),
                "title_boost": round(title_context_boost, 4),
                "similarity": round(hybrid_score, 4)
            })

    # 5️⃣ Sort by hybrid score and return top N
    formatted_results.sort(key=lambda x: x["similarity"], reverse=True)

    return formatted_results[:top_n]


#Collaborative Filtering Recommendation can be added here similarly
def _collaborative_filtering_sync(candidate_id, job_ids, n=5):
    """
    Improved User-Based Collaborative Filtering with Feedback Weighting
    - Calculates user similarity based on common interactions
    - Weights feedback by type: apply (1.0) > like (0.7)
    - Uses actual score values when available
    - Provides meaningful scores based on similarity weights
    """
    from apps.recommendation_agent.models import JobFeedback
    from collections import defaultdict

    print(f"\n🔍 CF Recommendation for Candidate {candidate_id}")

    # Define feedback weights (apply is stronger signal than like)
    FEEDBACK_WEIGHTS = {
        'apply': 1.0,   # Strongest signal - user actually applied
        'like': 0.7,    # Medium signal - user saved/liked
    }

    # 1. Build user-job interaction matrix with weighted scores
    all_feedbacks = JobFeedback.objects.all()
    user_jobs = defaultdict(set)  # user_id -> set of job_ids
    job_users = defaultdict(dict)  # job_id -> {user_id: weighted_score}
    user_job_weights = defaultdict(dict)  # user_id -> {job_id: weighted_score}

    for fb in all_feedbacks:
        # Calculate weighted score based on feedback type
        feedback_weight = FEEDBACK_WEIGHTS.get(fb.feedback_type, 0.5)

        # If score exists, use it; otherwise use feedback_weight
        if fb.score is not None and fb.score > 0:
            weighted_score = fb.score * feedback_weight
        else:
            weighted_score = feedback_weight

        user_jobs[fb.candidate_id].add(fb.job_id)
        job_users[fb.job_id][fb.candidate_id] = weighted_score
        user_job_weights[fb.candidate_id][fb.job_id] = weighted_score

    # 2. Get target user's interactions
    target_user_jobs = user_jobs.get(candidate_id, set())

    if not target_user_jobs:
        print(f"  ⚠️  Candidate {candidate_id} has no interaction history")
        return []

    print(f"  Target user interacted with {len(target_user_jobs)} jobs: {sorted(target_user_jobs)}")

    # 3. Calculate weighted Jaccard similarity with other users
    user_similarities = {}
    for other_user_id, other_user_jobs in user_jobs.items():
        if other_user_id == candidate_id:
            continue

        # Find common jobs
        common_jobs = target_user_jobs.intersection(other_user_jobs)

        if not common_jobs:
            continue

        # Calculate weighted similarity
        # Sum of min weights for common jobs / Sum of max weights for all jobs
        common_weight_sum = 0.0
        for job_id in common_jobs:
            target_weight = user_job_weights[candidate_id].get(job_id, 0.5)
            other_weight = user_job_weights[other_user_id].get(job_id, 0.5)
            common_weight_sum += min(target_weight, other_weight)

        # Calculate union and max weights
        all_jobs = target_user_jobs.union(other_user_jobs)
        all_weight_sum = 0.0
        for job_id in all_jobs:
            target_weight = user_job_weights[candidate_id].get(job_id, 0.0)
            other_weight = user_job_weights[other_user_id].get(job_id, 0.0)
            all_weight_sum += max(target_weight, other_weight)

        if all_weight_sum > 0:
            similarity = common_weight_sum / all_weight_sum
            user_similarities[other_user_id] = similarity
            print(f"  Similarity with User {other_user_id}: {similarity:.4f} (common: {sorted(common_jobs)}, weighted)")

    if not user_similarities:
        print(f"  ⚠️  No similar users found")
        return []

    # 4. Filter candidate jobs (not yet interacted)
    candidate_jobs = [job_id for job_id in job_ids if job_id not in target_user_jobs]

    if not candidate_jobs:
        print(f"  ⚠️  User has interacted with all available jobs")
        return []

    print(f"  Candidate jobs (not interacted): {len(candidate_jobs)}")

    # 5. Calculate weighted score for each candidate job
    job_scores = {}
    job_supporters = {}  # Track which users liked each job and their weights

    for job_id in candidate_jobs:
        score = 0.0
        supporters = []

        # Check which similar users liked this job
        users_with_weights = job_users.get(job_id, {})

        for user_id, job_weight in users_with_weights.items():
            if user_id in user_similarities:
                # Weight by BOTH user similarity AND feedback strength
                contribution = user_similarities[user_id] * job_weight
                score += contribution
                supporters.append((user_id, job_weight))

        if score > 0:
            job_scores[job_id] = score
            job_supporters[job_id] = supporters

    # 6. Sort by score
    sorted_jobs = sorted(job_scores.items(), key=lambda x: x[1], reverse=True)[:n]

    if not sorted_jobs:
        print(f"  ⚠️  No recommendations found")
        return []

    print(f"  Top {len(sorted_jobs)} recommendations:")
    for job_id, score in sorted_jobs:
        supporters = job_supporters.get(job_id, [])
        supporters_info = ', '.join([f"User {uid} (weight={w:.2f})" for uid, w in supporters])
        print(f"    Job {job_id}: score={score:.4f} (liked by: {supporters_info})")

    # 7. Get job details from database
    predicted_job_ids = [job_id for job_id, _ in sorted_jobs]
    jobs = JobPostings.objects.filter(id__in=predicted_job_ids).values(
        'id', 'title', 'description', 'address'
    )

    job_details_map = {job['id']: job for job in jobs}

    # 8. Normalize scores to 0-1 range and format results
    max_raw_score = sorted_jobs[0][1] if sorted_jobs else 1.0

    detailed_results = []
    for job_id, raw_score in sorted_jobs:
        job_info = job_details_map.get(job_id, {})

        # Normalize score (scale to 0-1 based on max score in this result set)
        normalized_score = raw_score / max_raw_score if max_raw_score > 0 else 0

        # Get skills from CSV data
        skills = "N/A"
        try:
            job_row = data_jp[data_jp['id'] == job_id]
            if not job_row.empty:
                skills = job_row.iloc[0].get('skills', 'N/A')
        except Exception:
            pass

        detailed_results.append({
            "job_id": job_id,
            "title": job_info.get('title', 'Unknown'),
            "description": job_info.get('description', '')[:200] + '...' if job_info.get('description', '') else '',
            "skills": skills,
            "similarity": round(normalized_score, 4),
            "raw_cf_score": round(raw_score, 4)  # Include raw score for debugging
        })

    return detailed_results

async def get_collaborative_filtering_recommendations(candidate_id, job_ids, model, n=5):
    """Async wrapper for collaborative filtering"""
    return await sync_to_async(_collaborative_filtering_sync)(candidate_id, job_ids, n)


#Hybrid Recommendation can be added here similarly

async def get_hybrid_job_recommendations(candidate_id: int, query_item: dict, job_ids: list, top_n: int = 5):
    # 1️⃣ Get Content-Based recommendations (semantic + skill overlap)
    content_results = await get_content_based_recommendations(query_item, top_n=top_n * 2)
    content_scores = {r["job_id"]: r["similarity"] for r in content_results}

    # 2️⃣ Try Collaborative Filtering (fallback to None if data too small)
    try:
        cf_results = await get_collaborative_filtering_recommendations(candidate_id, job_ids, model=None, n=top_n * 2)
        # CF results now return detailed dictionaries with job info (using 'similarity' key)
        cf_scores = {job["job_id"]: job["similarity"] for job in cf_results}
        has_cf_data = True
    except Exception as e:
        print(f"[⚠️ CF skipped: {e}]")
        cf_results = []  # Initialize to empty list when exception occurs
        cf_scores = {}
        has_cf_data = False

    # 3️⃣ Set dynamic weights
    # New system → content weight high, CF low
    if not has_cf_data:
        content_weight = 1.0
        cf_weight = 0.0
    else:
        content_weight = 0.8  # tune dynamically when more feedback grows
        cf_weight = 0.2

    # 4️⃣ Combine both scores
    hybrid_combined = {}
    for job_id, c_score in content_scores.items():
        cf_score = cf_scores.get(job_id, 0)
        hybrid_score = (content_weight * c_score) + (cf_weight * cf_score)
        hybrid_combined[job_id] = round(hybrid_score, 4)

    # 5️⃣ Merge metadata from content results
    hybrid_ranked = sorted(content_results, key=lambda x: hybrid_combined.get(x["job_id"], 0), reverse=True)[:top_n]

    # 6️⃣ Attach hybrid score to results
    for r in hybrid_ranked:
        r["final_score"] = hybrid_combined.get(r["job_id"], r["similarity"])
        r["source_weight"] = {"content": content_weight, "cf": cf_weight}

    return  {
        "content_based": content_results[:top_n],
        "collaborative": cf_results[:top_n],  # Now returns detailed job info with title, description, skills
        "hybrid_top": hybrid_ranked
    }


def _query_all_jobs_sync():
    """
    Synchronous function to get ACTIVE jobs from PostgreSQL (ORM)
    """
    jobs = JobPostings.objects.filter(status="ACTIVE").values(
        "id", "title", "description", "address"
    )

    # Chuẩn hóa về định dạng mà hybrid model dùng
    job_list = [{"job_id": job["id"], "title": job["title"],
                 "description": job["description"], "address": job["address"]}
                for job in jobs]
    return job_list

def query_all_jobs():
    """
    Lấy danh sách job đang ACTIVE từ PostgreSQL (ORM)
    Wrapper for sync context (still synchronous for backward compatibility)
    """
    return _query_all_jobs_sync()

async def query_all_jobs_async():
    """
    Async wrapper for query_all_jobs
    """
    return await sync_to_async(_query_all_jobs_sync)()
