"""
PhoneTrace — Evidence Generator Package
=========================================

Synthetic Android forensic evidence generator for Phase 1.
"""

from evidence_generator.generate_calls import generate_call_log
from evidence_generator.generate_sms import generate_sms_log
from evidence_generator.generate_browser import generate_browser_history
from evidence_generator.generate_gps import generate_gps_log
from evidence_generator.generate_app_usage import generate_app_usage
from evidence_generator.generate_file_metadata import generate_file_metadata

__all__ = [
    "generate_call_log",
    "generate_sms_log",
    "generate_browser_history",
    "generate_gps_log",
    "generate_app_usage",
    "generate_file_metadata",
]
