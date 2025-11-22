"""
Configuration and tuning parameters for the MMA simulation engine.

All values here are deliberately simple defaults and are expected to be tuned
over time for the Fax MMA world (finish rates, KO probabilities, etc.).
"""

DEFAULT_DECISION_FINISH_RATIO = 0.6  # fraction of fights that go to decision
DEFAULT_KO_BASE_RATE = 0.15
DEFAULT_SUB_BASE_RATE = 0.10

DEFAULT_RANDOM_SEED = None  # let callers pass an explicit seed if needed
