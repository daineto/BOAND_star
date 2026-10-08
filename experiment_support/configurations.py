"""Compatibility exports for the original ICAPS-specific entry points.

New papers define their own Campaign in campaigns/<id>/campaign.py.
"""
from experiment_support.models import Configuration, REPOSITORY_ROOT
from campaigns.icaps2025.campaign import (
    CAMPAIGN, DOMAIN_DIRECTORIES, MINI_CONFIGURATIONS, MINI_DOMAINS,
    PAPER_CONFIGURATIONS, PAPER_DOMAINS,
)

TIMEOUT_SECONDS = CAMPAIGN.timeout_seconds
MEMORY_KB = CAMPAIGN.memory_kb
PARALLEL_RUNS = CAMPAIGN.default_workers
