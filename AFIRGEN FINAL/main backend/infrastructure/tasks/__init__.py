"""
Background tasks module for AFIRGen backend.

This module contains all Celery tasks organized by category:
- email: Email notification tasks
- reports: Report generation tasks
- analytics: Analytics processing tasks
- cleanup: Cleanup and maintenance tasks
"""

from .email_tasks import *
from .report_tasks import *
from .analytics_tasks import *
from .cleanup_tasks import *

__all__ = [
    # Email tasks
    "send_fir_confirmation_email",
    "send_notification_email",
    
    # Report tasks
    "generate_pdf_report",
    "generate_excel_report",
    
    # Analytics tasks
    "update_dashboard_stats",
    "process_analytics_data",
    
    # Cleanup tasks
    "archive_old_records",
    "clear_expired_cache",
]
