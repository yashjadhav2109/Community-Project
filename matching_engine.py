"""
Matching Engine for Local Skill & Job Exchange Platform.
Implements the Multi-Factor Skill-to-Job Proximity & Compatibility Algorithm.
Community Engineering Project (BIT42304) - TGPCET Nagpur
"""

import math
import re


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees) in kilometers.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 5.0  # default fallback radius

    R = 6371.0  # Radius of earth in kilometers
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (math.sin(dLat / 2) * math.sin(dLat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dLon / 2) * math.sin(dLon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


def tokenize(text):
    """Tokenize and clean words for text matching."""
    if not text:
        return set()
    words = re.findall(r'\b[a-zA-Z0-9_]{2,}\b', text.lower())
    # remove common stop words
    stopwords = {'the', 'and', 'for', 'with', 'need', 'require', 'looking', 'work', 'job', 'skill', 'please', 'help'}
    return {w for w in words if w not in stopwords}


def calculate_match_score(job, skill, provider):
    """
    Calculate a comprehensive match score (0-100%) between a Job post and a Skill provider.

    Breakdown:
    1. Category & Skill Keyword Relevance: 35 points
    2. Proximity & Geographic Neighborhood: 30 points
    3. Budget vs Rate Compatibility: 15 points
    4. Provider Rating & Reputation: 20 points
    """
    breakdown = {}
    reasons = []

    # 1. Category & Keyword Relevance (Max: 35)
    category_score = 0.0
    job_cat = (job.get('category') or '').lower().strip()
    skill_cat = (skill.get('category') or '').lower().strip()

    if job_cat == skill_cat:
        category_score += 20.0
        reasons.append("Exact category match")
    elif job_cat in skill_cat or skill_cat in job_cat:
        category_score += 12.0
        reasons.append("Related category")

    # Text / Tag keywords similarity (Jaccard-like bonus)
    job_tokens = tokenize(f"{job.get('title', '')} {job.get('description', '')}")
    skill_tokens = tokenize(f"{skill.get('title', '')} {skill.get('description', '')} {skill.get('tags', '')}")
    common_tokens = job_tokens.intersection(skill_tokens)
    if common_tokens:
        overlap_ratio = min(len(common_tokens) / max(len(job_tokens), 1), 1.0)
        kw_score = min(15.0, overlap_ratio * 20.0)
        category_score += kw_score
        reasons.append(f"Keyword match ({len(common_tokens)} terms)")
    else:
        category_score += 5.0  # base baseline

    category_score = min(35.0, category_score)
    breakdown['category_keyword'] = round(category_score, 1)

    # 2. Proximity & Radius (Max: 30)
    job_lat = job.get('lat') or 21.1458
    job_lng = job.get('lng') or 79.0882
    skill_lat = skill.get('lat') or 21.1458
    skill_lng = skill.get('lng') or 79.0882
    max_radius = float(job.get('max_distance_km') or 15.0)

    distance = haversine_distance(job_lat, job_lng, skill_lat, skill_lng)

    # Check same neighborhood
    same_neighborhood = (job.get('neighborhood', '').lower().strip() ==
                         skill.get('neighborhood', '').lower().strip())

    if same_neighborhood:
        proximity_score = 30.0
        reasons.append(f"Same neighborhood ({job.get('neighborhood')})")
    elif distance <= 2.0:
        proximity_score = 28.0
        reasons.append(f"Very close (~{distance} km)")
    elif distance <= 5.0:
        proximity_score = 24.0
        reasons.append(f"Within 5 km (~{distance} km)")
    elif distance <= max_radius:
        # linear decay within radius
        factor = 1.0 - (distance / max_radius)
        proximity_score = 10.0 + (factor * 12.0)
        reasons.append(f"Within search radius (~{distance} km)")
    else:
        proximity_score = max(2.0, 10.0 - (distance - max_radius))
        reasons.append(f"Outside preferred radius (~{distance} km)")

    proximity_score = min(30.0, max(0.0, proximity_score))
    breakdown['proximity'] = round(proximity_score, 1)
    breakdown['distance_km'] = distance

    # 3. Budget vs Rate Compatibility (Max: 15)
    budget = float(job.get('budget') or 0.0)
    rate = float(skill.get('hourly_rate') or 0.0)
    # If budget is >= rate or within reasonable estimate
    if budget <= 0 or rate <= 0:
        rate_score = 10.0
    elif rate <= budget:
        rate_score = 15.0
        reasons.append("Rate within requested budget")
    elif rate <= budget * 1.25:
        rate_score = 10.0
        reasons.append("Rate close to budget")
    else:
        rate_score = 4.0
        reasons.append("Rate exceeds budget")

    breakdown['budget_fit'] = round(rate_score, 1)

    # 4. Provider Experience & Rating (Max: 20)
    rating = float(provider.get('rating') or 5.0)
    exp = int(skill.get('experience_years') or 1)
    is_verified = bool(provider.get('is_verified', 1))

    rating_component = (rating / 5.0) * 12.0
    exp_component = min(5.0, (exp / 10.0) * 5.0)
    verification_component = 3.0 if is_verified else 0.0

    rep_score = min(20.0, rating_component + exp_component + verification_component)
    breakdown['reputation'] = round(rep_score, 1)
    if rating >= 4.5:
        reasons.append(f"Top-rated provider ({rating} ★)")
    if is_verified:
        reasons.append("Verified community member")

    # Total Match Score
    total_score = round(category_score + proximity_score + rate_score + rep_score, 1)
    total_score = max(10.0, min(99.5, total_score))  # clamp between 10% and 99.5%

    return {
        'total_score': total_score,
        'breakdown': breakdown,
        'reasons': reasons,
        'distance_km': distance
    }


def find_top_matches_for_job(job_dict, skills_list, users_dict, top_k=10):
    """
    Rank all available skills for a given job and return sorted matches.
    """
    matches = []
    for skill in skills_list:
        provider = users_dict.get(skill['user_id'])
        if not provider:
            continue
        # Don't match user to their own job
        if skill['user_id'] == job_dict.get('user_id'):
            continue

        match_result = calculate_match_score(job_dict, skill, provider)
        matches.append({
            'skill': skill,
            'provider': provider,
            'score': match_result['total_score'],
            'distance_km': match_result['distance_km'],
            'breakdown': match_result['breakdown'],
            'reasons': match_result['reasons']
        })

    matches.sort(key=lambda m: m['score'], reverse=True)
    return matches[:top_k]
