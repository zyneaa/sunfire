"""
Feed Ranking System – Parameter Configuration

This file defines all tunable parameters used in the ranking pipeline.
Each section corresponds to a major component of the scoring system.

All values are designed to be independently adjustable for experimentation.
"""

# =========================================================
# 1. RELEVANCE (Implicit & Explicit Signals)
# =========================================================

# Maximum weight for implicit (behavioral) signals.
# Prevents historical behavior from fully overriding explicit preferences.
BETA_MAX = 0.8

# Number of interactions required for implicit signals to reach near-max influence.
# Controls how quickly the system adapts to user behavior.
K_INTERACTIONS = 50

# Gaussian radius (in km) for distance-based relevance.
# Smaller values = stricter location matching.
R_RADIUS_KM = 5.0

# Base multiplier for explicit signals (filters, selected location, etc.).
EXPLICIT_WEIGHT = 1.0


# =========================================================
# 2. FRESHNESS (Time Decay)
# =========================================================

# Base exponential decay rate for content over time.
LAMBDA_BASE = 0.05

LAMBDA_SESSION = 0.1

# Reduces decay for highly active users (power users).
# Effective decay = max(LAMBDA_BASE - LAMBDA_USER_OFFSET, FRESHNESS_FLOOR)
LAMBDA_USER_OFFSET = 0.002

# Minimum freshness value to prevent older content from becoming invisible.
FRESHNESS_FLOOR = 0.001

# Time window (in hours) where new posts receive extra exposure.
T_NEW_POST = 48

# Additive boost applied to new posts within T_NEW_POST.
NEW_POST_BONUS = 2


# =========================================================
# 3. TRUST SCORE
# =========================================================

# Default baseline trust score for new or unrated entities.
TRUST_SIGMA = 0.5

# Bonus applied to verified users/listings.
VERIFIED_BONUS = 0.2

# Multiplier for user ratings.
# Example: 5-star rating → +0.5 (5 * 0.1)
RATING_MULTIPLIER = 0.1


# =========================================================
# 4. BOOST MECHANISM
# =========================================================

# Duration (in hours) where boost remains at full strength.
BOOST_HOLD_HOURS = 72

# Exponential decay rate for boost after hold period expires.
LAMBDA_BOOST = 0.05

# Maximum allowed boost multiplier (prevents abuse).
BOOST_CAP = 8.0

# =========================================================
# 5. EXPLORATION (ANTI-BUBBLE)
# =========================================================

# Exploration rate for new users.
# Higher = more randomness to learn preferences quickly.
EPSILON_NEW_USER = 0.2

# Exploration rate for experienced users.
# Lower = more stable, personalized feed.
EPSILON_OLD_USER = 0.005


# =========================================================
# 6. DIVERSITY CONTROL
# =========================================================

# Penalty factor for repeated categories in feed.
# Applied as: penalty = GAMMA_DIVERSITY ** n
# where n = number of items from same category already shown.
GAMMA_DIVERSITY = 0.5

GAMMA_PENALTY = 0.3

# 6.0 INTERACTION WEIGHTS (Generator + Simulator)
INTERACTIONS = {
    "view":    {"weight": 0.1, "chance": 0.6, "dwell_range": (5, 30)},
    "click":   {"weight": 0.5, "chance": 0.3, "dwell_range": (30, 120)},
    "like":    {"weight": 1.5, "chance": 0.08, "dwell_range": (60, 300)},
    "share":   {"weight": 3.0, "chance": 0.02, "dwell_range": (120, 600)},
    "contact": {"weight": 5.0, "chance": 0.005, "dwell_range": (200, 600)}
}

# Misc
DAYTIME_ACTIVENESS = 0.1
MORNING_AND_NIGHT_ACTIVENESS = 0.3
DISTRACTION_CHANCE = 0.1
LAST_N_EVENT = 20

USER_TIME_SPENT = 480
