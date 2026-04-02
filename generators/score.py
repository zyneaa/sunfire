import json
from datetime import datetime
from parameters import *
import random
import numpy as np
from haversine import haversine

def distance_score(d):
    return np.exp(-(d**2) / (2 * R_RADIUS_KM**2))

def build_user_vector(interactions, properties):
    prop_map = {p['id']: p for p in properties}

    # [Condo_Score, House_Score, Rent_Score, Buy_Score]
    user_vec = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    for event in interactions:
        p = prop_map.get(event['listing_id'])
        if not p: continue

        w = event['weight']

        # 1. Property Mapping
        if p['property_type'] == 'condo':     user_vec[0] += w
        if p['property_type'] == 'house':     user_vec[1] += w
        if p['property_type'] == 'apartment': user_vec[2] += w
        if p['property_type'] == 'land':      user_vec[3] += w

        # 2. Transaction Type Mapping transaction_type
        if p['transaction_type'] == 'rent':   user_vec[4] += w
        if p['transaction_type'] == 'buy':    user_vec[5] += w

    # Return normalized vector (magnitude of 1)
    norm = np.linalg.norm(user_vec)
    return user_vec / norm if norm > 0 else user_vec

def build_property_vector(p):
    vec = np.array([
        1.0 if p['property_type'] == 'condo'     else 0.0,
        1.0 if p['property_type'] == 'house'     else 0.0,
        1.0 if p['property_type'] == 'apartment' else 0.0,
        1.0 if p['property_type'] == 'land'      else 0.0,
        1.0 if p['transaction_type'] == 'rent'   else 0.0,
        1.0 if p['transaction_type'] == 'buy'    else 0.0
    ])
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec

def get_cosine_preference(user_vector, property_vector):
    return np.dot(user_vector, property_vector)

def build_session_context(interactions):
    last_session = interactions[-1]["session_number"]
    recent = [e for e in interactions if e["session_number"] == last_session]

    type_counts = {}
    trans_counts = {}

    for e in recent:
        type_counts[e["property_type"]] = type_counts.get(e["property_type"], 0) + 1
        trans_counts[e["transaction_type"]] = trans_counts.get(e["transaction_type"], 0) + 1

    dominant_type = max(type_counts, key=lambda k: type_counts[k], default=None)
    dominant_trans = max(trans_counts, key=lambda k: trans_counts[k], default=None)

    return {
        "dominant_type": dominant_type,
        "dominant_trans": dominant_trans
    }


def compute_D_i(event, activity):
    return np.log(np.e + event["dwell_time_sec"] * activity)

def compute_match_score(event, session_ctx):
    score = 0.0
    weight_sum = 0.0

    # 1. Match dominant property type
    weight = 0.5
    if event["property_type"] == session_ctx["dominant_type"]:
        score += weight
    weight_sum += weight

    # 2. Match dominant transaction type
    weight = 0.3
    if event["transaction_type"] == session_ctx["dominant_trans"]:
        score += weight
    weight_sum += weight

    # 3. (Optional) recency boost later
    weight = 0.2
    score += weight * 0.5  # fallback neutral
    weight_sum += weight

    return score / weight_sum

# 1.1 EXPLICIT MATCHING (The Vibe & Location)
def compute_distance_score(t_lat, t_lng, p_lat, p_lng):
    """Distance Score = e^(-d^2 / 2r^2)"""
    d = haversine((t_lat, t_lng), (p_lat, p_lng))
    return np.exp(-(d**2) / (2 * R_RADIUS_KM**2))

def compute_explicit(user_vector, property_vector, t_lat, t_lng, p_lat, p_lng):
    """Explicit = Cosine Similarity * Gaussian Distance Score"""
    cosine_sim = np.dot(user_vector, property_vector) # Normalized 6D vectors
    dist_score = compute_distance_score(t_lat, t_lng, p_lat, p_lng)
    return cosine_sim * dist_score


# 1.2 IMPLICIT MATCHING (The Behavior Tracking)
def compute_di(dwell_time, activity_factor):
    """D_i = ln(e + dwell_time_sec * activity_factor)"""
    return np.log(np.e + (dwell_time * max(0.1, activity_factor)))

def compute_alpha_beta(interaction_count):
    """β = min(β_max, Count/K), α = 1 - β"""
    beta = min(BETA_MAX, interaction_count / K_INTERACTIONS)
    alpha = 1.0 - beta
    return alpha, beta

def compute_relevance_final(explicit, implicit, session_intent, alpha, beta, gamma=0.5):
    """
    Relevance = (α * Explicit) + (β * Implicit)
    Relevance_final = Relevance * (1 - γ) + Session Intent * γ
    """
    base_relevance = (alpha * explicit) + (beta * implicit)
    return (base_relevance * (1 - gamma)) + (session_intent * gamma)


# 2. FRESHNESS
def compute_freshness(post_age_hours):
    """
    λ_effective = max(λ_base - λ_user, ϴ)
    Freshness = e^(-λ_effective * t)
    """
    lam_eff = max(LAMBDA_BASE - LAMBDA_USER_OFFSET, FRESHNESS_FLOOR)
    return np.exp(-lam_eff * post_age_hours)


# 3. TRUST SCORE
def compute_trust_score(trust_data):
    """Trust Score = 𝛔 + (Rating * 0.1) + Verified_Bonus"""
    score = TRUST_SIGMA + (trust_data["rating"] * RATING_MULTIPLIER)
    if trust_data.get("verified", False):
        score += VERIFIED_BONUS
    return score


# 4. BOOST MODIFIER
def compute_boost_modifier(boost_data, now):
    # Guard clause against 'null' start_time and inactive boosts
    if not boost_data.get("active", False) or not boost_data.get("start_time"):
        return 1.0

    tokens_spent = boost_data.get("tokens", 0) # Fixed key from 'tokens_spent'

    boost_raw = 1.0 + np.log10(1.0 + tokens_spent)
    boost_capped = min(boost_raw, BOOST_CAP)

    start_time = datetime.fromisoformat(boost_data["start_time"])
    t_boost = (now - start_time).total_seconds() / 3600

    if t_boost <= BOOST_HOLD_HOURS:
        return boost_capped
    else:
        decay = np.exp(-LAMBDA_BOOST * (t_boost - BOOST_HOLD_HOURS))
        return 1.0 + (boost_capped - 1.0) * decay

# 5, 7, & BASE RANKING
def compute_rank_score(relevance_final, freshness, trust, boost):
    """Rank_Score = (Relevance_final * Freshness) + (Trust + Boost)"""
    return (relevance_final * freshness) + (trust + boost)

def apply_anti_bubble(rank_score, epsilon):
    """Final_Score = Rank_Score * (1 - ε) + Exploration_Score * ε"""
    exploration_score = random.uniform(0, 1)
    return (rank_score * (1.0 - epsilon)) + (exploration_score * epsilon)

def apply_cold_start(score, post_age_hours):
    """if PostAge < T_new: Score += NewPostBonus"""
    if post_age_hours < T_NEW_POST:
        return score + NEW_POST_BONUS
    return score


# 6 & NORMALIZATION (Post-Processing)
def apply_diversity_penalty(results):
    """Final_Score = Final_Score * γ^n (applied top-to-bottom)"""
    seen_categories = {}
    for res in results:
        cat = res["property_type"]
        n = seen_categories.get(cat, 0)
        res["final_score"] = res["final_score"] * (GAMMA_PENALTY ** n)
        seen_categories[cat] = n + 1

    # Re-sort after penalties
    return sorted(results, key=lambda x: x["final_score"], reverse=True)

def normalize_scores(results):
    """Normalized = (Score - Min) / (Max - Min)"""
    if not results: return results
    scores = [r["final_score"] for r in results]
    s_min, s_max = min(scores), max(scores)

    if s_max == s_min:
        for r in results: r["norm_score"] = 1.0
        return results

    for r in results:
        r["norm_score"] = (r["final_score"] - s_min) / (s_max - s_min)
    return results

def run_sunfire_pipeline(log_path, property_path):
    # 1. Load Data
    with open(log_path, "r") as f:
        data = json.load(f)
        profile = data["user_profile"]
        interactions = data["interactions"]
    with open(property_path, "r") as f:
        properties = json.load(f)

    now = datetime.now()
    prop_map = {p["id"]: p for p in properties}

    # 2. Pre-compute Global/User states
    interaction_count = len(interactions)
    alpha, beta = compute_alpha_beta(interaction_count)
    t_lat, t_lng = profile["target_lat"], profile["target_lng"]
    user_vec = build_user_vector(interactions, properties) # Using your existing 6D function
    session_ctx = build_session_context(interactions) # Using your existing function

    # 3. Pre-calculate Implicit & Session Intent for all properties
    implicit_map = {p["id"]: 0.0 for p in properties}
    session_map = {p["id"]: 0.0 for p in properties}

    for event in interactions:
        pid = event["listing_id"]
        if pid not in prop_map: continue

        dt = (now - datetime.fromisoformat(event["timestamp"])).total_seconds() / 3600
        d_i = compute_di(event["dwell_time_sec"], event["activity_factor"])

        # Implicit
        implicit_map[pid] += event["weight"] * d_i * np.exp(-LAMBDA_BASE * dt)

        # Session Intent
        match_score = compute_match_score(event, session_ctx) 
        session_map[pid] += event["weight"] * match_score * d_i * np.exp(-LAMBDA_SESSION * dt) # Session decay

    # 4. The Main Loop
    results = []
    epsilon = EPSILON_NEW_USER if interaction_count < 10 else EPSILON_OLD_USER # Anti-bubble logic

    for p in properties:
        pid = p["id"]
        p_vec = build_property_vector(p)
        post_age = (now - datetime.fromisoformat(p["created_at"])).total_seconds() / 3600

        # Step-by-step Execution
        explicit = compute_explicit(user_vec, p_vec, t_lat, t_lng, p["lat"], p["lng"])
        rel_final = compute_relevance_final(explicit, implicit_map[pid], session_map[pid], alpha, beta, GAMMA_DIVERSITY)

        freshness = compute_freshness(post_age)
        trust = compute_trust_score(p["trust"])
        boost = compute_boost_modifier(p["boost"], now)

        rank_score = compute_rank_score(rel_final, freshness, trust, boost)

        final_score = apply_anti_bubble(rank_score, epsilon)
        final_score = apply_cold_start(final_score, post_age)

        results.append({
            "id": pid,
            "property_type": p["property_type"],
            "final_score": final_score,
            "breakdown": {
                "explicit": explicit, "implicit": implicit_map[pid], 
                "freshness": freshness, "trust": trust, "boost": boost
            }
        })

    # 5. Post-Processing
    results.sort(key=lambda x: x["final_score"], reverse=True)
    results = apply_diversity_penalty(results)
    results = normalize_scores(results)

    return results

import csv

def export_sunfire_to_csv(results, filename="sunfire_detailed_audit.csv"):
    """
    Takes the list of dicts from run_sunfire_pipeline and 
    flattens the 'breakdown' for a deep-dive CSV audit.
    """
    if not results:
        print("[-] No results to export. Pipeline might have returned empty.")
        return

    base_headers = ["id", "property_type", "final_score", "norm_score"]
    breakdown_headers = list(results[0]["breakdown"].keys())
    all_headers = base_headers + breakdown_headers

    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=all_headers)
            writer.writeheader()

            for item in results:
                row = {
                    "id": item["id"],
                    "property_type": item["property_type"],
                    "final_score": round(item["final_score"], 6),
                    "norm_score": round(item.get("norm_score", 0), 4),
                }

                row.update(item["breakdown"])

                writer.writerow(row)
        print(f"Audit Complete: Detailed scores exported to {filename}")
    except IOError as e:
        print(f"[-] Failed to write CSV: {e}")

# --- EXECUTION ---
if __name__ == "__main__":
    res = run_sunfire_pipeline("./data/user_interaction_log.json", "./data/dummy_listings.json")
    export_sunfire_to_csv(res, "sunfire_score.csv")

