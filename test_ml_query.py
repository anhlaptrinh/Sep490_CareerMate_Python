"""
Test content-based recommendation with "Python + Machine Learning" query
Should prioritize ML Engineer jobs over generic Python jobs
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Careermate.settings')
django.setup()

import asyncio
from apps.recommendation_agent.services.recommendation_system import get_content_based_recommendations

async def test_ml_query():
    print("=" * 80)
    print("TEST: Python + Machine Learning Query")
    print("=" * 80)

    query_item = {
        "skills": ["Python"],
        "title": "Machine Learning Engineer",
        "description": ""
    }

    print(f"\n📋 Query:")
    print(f"   Skills: {query_item['skills']}")
    print(f"   Title: {query_item['title']}")

    print(f"\n🔍 Getting recommendations...")
    results = await get_content_based_recommendations(query_item, top_n=10)

    print(f"\n✅ Got {len(results)} high-quality recommendations:\n")
    print("=" * 80)

    for idx, job in enumerate(results, 1):
        print(f"\n{idx}. [{job['similarity']:.4f}] Job {job['job_id']}: {job['title']}")
        print(f"   {'─'*76}")
        print(f"   Skills: {job['skills']}")
        print(f"   Breakdown:")
        print(f"      • Semantic Similarity: {job.get('semantic_similarity', 0):.4f}")
        print(f"      • Skill Overlap: {job.get('skill_overlap', 0):.4f}")
        print(f"      • Title Boost: {job.get('title_boost', 0):.4f}")
        print(f"      • Final Score: {job['similarity']:.4f}")

        # Check if this is ML/Data Science related
        title_lower = job['title'].lower()
        is_ml_related = any(term in title_lower for term in ['machine learning', 'ml', 'data science', 'ai'])
        if is_ml_related:
            print(f"   ✅ ML/AI RELATED JOB")

    print("\n" + "=" * 80)
    print("\n🎯 EXPECTED BEHAVIOR:")
    print("   - ML Engineer jobs should rank HIGHEST (semantic + title boost)")
    print("   - Data Science jobs should rank high (related context)")
    print("   - Generic Python jobs should rank lower")
    print("   - All scores should be ≥ 0.15 (minimum threshold)")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_ml_query())

