"""
FIR Service

This module provides business logic for FIR operations and integrates
with background tasks for non-critical operations like email notifications,
report generation, and analytics processing.

Requirements: 4.1
Task: 6.6 Move non-critical operations to background tasks
"""

from typing import Dict, Any, Optional
from infrastructure.logging import get_logger
from infrastructure.background_task_manager import BackgroundTaskManager, TaskType

logger = get_logger(__name__)


class FIRService:
    """
    Service class for FIR operations.
    
    Handles FIR completion workflows and triggers background tasks for:
    - Email notifications
    - Report generation
    - Analytics processing
    
    Requirements: 4.1
    """
    
    def __init__(self, task_manager: BackgroundTaskManager):
        """
        Initialize FIR service.
        
        Args:
            task_manager: Background task manager instance
        """
        self.task_manager = task_manager
        logger.info("FIRService initialized")
    
    def on_fir_completed(
        self,
        fir_number: str,
        session_id: str,
        recipient_email: Optional[str] = None,
        generate_report: bool = True,
        update_analytics: bool = True
    ) -> Dict[str, str]:
        """
        Handle FIR completion by triggering background tasks.
        
        This method is called when a FIR is successfully completed and triggers
        non-critical background operations:
        1. Send confirmation email to user (if email provided)
        2. Generate PDF report asynchronously
        3. Update analytics dashboard
        
        All operations are non-blocking and execute asynchronously.
        
        Args:
            fir_number: FIR record identifier
            session_id: Session ID associated with the FIR
            recipient_email: Email address to send confirmation (optional)
            generate_report: Whether to generate PDF report (default: True)
            update_analytics: Whether to update analytics (default: True)
            
        Returns:
            Dictionary with task IDs for each triggered background task
            
        Requirements: 4.1
        """
        task_ids = {}
        
        # 1. Send email notification (if email provided)
        if recipient_email:
            try:
                email_task_id = self.task_manager.enqueue_task(
                    task_name="afirgen_tasks.email.send_fir_confirmation",
                    task_type=TaskType.EMAIL,
                    params={
                        "fir_id": fir_number,
                        "recipient_email": recipient_email
                    },
                    priority=3  # Low priority
                )
                task_ids["email"] = email_task_id
                logger.info("Email notification task enqueued", task_id=email_task_id, fir_number=fir_number)
            except Exception as e:
                logger.error("Failed to enqueue email task", error=str(e), fir_number=fir_number)
                # Don't fail the request if email task fails to enqueue
        
        # 2. Generate PDF report
        if generate_report:
            try:
                report_task_id = self.task_manager.enqueue_task(
                    task_name="afirgen_tasks.reports.generate_pdf",
                    task_type=TaskType.REPORT,
                    params={
                        "fir_id": fir_number,
                        "report_type": "standard"
                    },
                    priority=5  # Medium priority
                )
                task_ids["report"] = report_task_id
                logger.info("Report generation task enqueued", task_id=report_task_id, fir_number=fir_number)
            except Exception as e:
                logger.error("Failed to enqueue report task", error=str(e), fir_number=fir_number)
                # Don't fail the request if report task fails to enqueue
        
        # 3. Update analytics dashboard
        if update_analytics:
            try:
                analytics_task_id = self.task_manager.enqueue_task(
                    task_name="afirgen_tasks.analytics.update_dashboard",
                    task_type=TaskType.ANALYTICS,
                    params={},
                    priority=2  # Low priority
                )
                task_ids["analytics"] = analytics_task_id
                logger.info("Analytics update task enqueued", task_id=analytics_task_id, fir_number=fir_number)
            except Exception as e:
                logger.error("Failed to enqueue analytics task", error=str(e), fir_number=fir_number)
                # Don't fail the request if analytics task fails to enqueue
        
        logger.info(
            "FIR completion tasks triggered",
            fir_number=fir_number,
            tasks_enqueued=len(task_ids),
            task_ids=task_ids
        )
        
        return task_ids
    
    def on_fir_finalized(
        self,
        fir_number: str,
        recipient_email: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Handle FIR finalization by triggering notification tasks.
        
        This method is called when a FIR is authenticated and finalized.
        It sends a finalization confirmation email if an email address is provided.
        
        Args:
            fir_number: FIR record identifier
            recipient_email: Email address to send finalization confirmation (optional)
            
        Returns:
            Dictionary with task IDs for triggered background tasks
            
        Requirements: 4.1
        """
        task_ids = {}
        
        # Send finalization notification email
        if recipient_email:
            try:
                email_task_id = self.task_manager.enqueue_task(
                    task_name="afirgen_tasks.email.send_notification",
                    task_type=TaskType.EMAIL,
                    params={
                        "recipient_email": recipient_email,
                        "subject": f"FIR {fir_number} Finalized",
                        "body": f"Your FIR {fir_number} has been successfully finalized and authenticated.",
                        "priority": 3
                    },
                    priority=3  # Low priority
                )
                task_ids["email"] = email_task_id
                logger.info("Finalization email task enqueued", task_id=email_task_id, fir_number=fir_number)
            except Exception as e:
                logger.error("Failed to enqueue finalization email task", error=str(e), fir_number=fir_number)
                # Don't fail the request if email task fails to enqueue
        
        return task_ids
    
    def generate_bulk_report(
        self,
        fir_ids: list,
        report_name: str = "fir_report",
        priority: int = 5
    ) -> str:
        """
        Generate bulk Excel report for multiple FIRs.
        
        Args:
            fir_ids: List of FIR record identifiers
            report_name: Name for the generated report file
            priority: Task priority (1-10, default: 5)
            
        Returns:
            Task ID for the report generation task
            
        Requirements: 4.1
        """
        task_id = self.task_manager.enqueue_task(
            task_name="afirgen_tasks.reports.generate_excel",
            task_type=TaskType.REPORT,
            params={
                "fir_ids": fir_ids,
                "report_name": report_name
            },
            priority=priority
        )
        
        logger.info("Bulk report generation task enqueued", task_id=task_id, fir_count=len(fir_ids), report_name=report_name)
        return task_id
    
    def process_analytics(
        self,
        data_type: str,
        date_range: Dict[str, str],
        priority: int = 2
    ) -> str:
        """
        Process analytics data for specified date range.
        
        Args:
            data_type: Type of analytics data to process
            date_range: Dict with 'start_date' and 'end_date' keys
            priority: Task priority (1-10, default: 2)
            
        Returns:
            Task ID for the analytics processing task
            
        Requirements: 4.1
        """
        task_id = self.task_manager.enqueue_task(
            task_name="afirgen_tasks.analytics.process_data",
            task_type=TaskType.ANALYTICS,
            params={
                "data_type": data_type,
                "date_range": date_range
            },
            priority=priority
        )
        
        logger.info("Analytics processing task enqueued", task_id=task_id, data_type=data_type, date_range=date_range)
        return task_id
