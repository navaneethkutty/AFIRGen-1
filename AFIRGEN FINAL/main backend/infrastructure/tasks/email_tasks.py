"""
Email notification tasks.

These tasks handle sending email notifications asynchronously.
Routed to: email queue (priority 3 - low)

Requirements: 4.1, 4.4
"""

from infrastructure.celery_app import celery_app
from infrastructure.tasks.base_task import DatabaseTask
from typing import Dict, Any
from infrastructure.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(
    name="afirgen_tasks.email.send_fir_confirmation",
    bind=True,
    base=DatabaseTask,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # 10 minutes max delay
    retry_jitter=True
)
def send_fir_confirmation_email(self, fir_id: str, recipient_email: str) -> Dict[str, Any]:
    """
    Send FIR confirmation email to user.
    
    Retry Strategy:
    - Max retries: 3
    - Exponential backoff with jitter
    - Max delay: 10 minutes
    - Only retries on retryable errors (network, timeout, etc.)
    
    Args:
        fir_id: FIR record identifier
        recipient_email: Email address to send confirmation to
        
    Returns:
        Dict with status and message
        
    Raises:
        Exception: If email sending fails after retries
        
    Requirements: 4.3
    """
    try:
        logger.info("Sending FIR confirmation email", fir_id=fir_id, recipient=recipient_email)
        
        # TODO: Implement actual email sending logic
        # Example: use SMTP, SendGrid, AWS SES, etc.
        
        return {
            "status": "success",
            "fir_id": fir_id,
            "recipient": recipient_email,
            "message": "FIR confirmation email sent successfully"
        }
    except Exception as exc:
        # Check if error is retryable
        if self.is_retryable_error(exc):
            logger.warning("Retryable error sending FIR confirmation email", error=str(exc), fir_id=fir_id)
            # Use enhanced retry with exponential backoff
            self.retry_with_backoff(
                exc=exc,
                base_delay=1.0,
                max_delay=600.0,
                exponential_base=2.0,
                jitter=True
            )
        else:
            # Non-retryable error, fail immediately
            logger.error("Non-retryable error sending FIR confirmation email", error=str(exc), fir_id=fir_id)
            raise


@celery_app.task(
    name="afirgen_tasks.email.send_notification",
    bind=True,
    base=DatabaseTask,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def send_notification_email(
    self,
    recipient_email: str,
    subject: str,
    body: str,
    priority: int = 3
) -> Dict[str, Any]:
    """
    Send generic notification email.
    
    Retry Strategy:
    - Max retries: 3
    - Exponential backoff with jitter
    - Max delay: 10 minutes
    
    Args:
        recipient_email: Email address to send notification to
        subject: Email subject line
        body: Email body content
        priority: Task priority (1-10, higher = more important)
        
    Returns:
        Dict with status and message
        
    Raises:
        Exception: If email sending fails after retries
        
    Requirements: 4.3
    """
    try:
        logger.info("Sending notification email", recipient=recipient_email, subject=subject)
        
        # TODO: Implement actual email sending logic
        
        return {
            "status": "success",
            "recipient": recipient_email,
            "subject": subject,
            "message": "Notification email sent successfully"
        }
    except Exception as exc:
        if self.is_retryable_error(exc):
            logger.warning("Retryable error sending notification email", error=str(exc), recipient=recipient_email)
            self.retry_with_backoff(exc=exc)
        else:
            logger.error("Non-retryable error sending notification email", error=str(exc), recipient=recipient_email)
            raise
