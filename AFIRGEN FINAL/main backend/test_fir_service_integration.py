"""
Unit tests for FIR service integration with background tasks.

Tests verify that non-critical operations (email, reports, analytics)
are properly moved to background tasks.

Requirements: 4.1
Task: 6.6 Move non-critical operations to background tasks
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from services.fir_service import FIRService
from infrastructure.background_task_manager import BackgroundTaskManager, TaskType


class TestFIRServiceIntegration:
    """Test FIR service integration with background tasks"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Mock database pool
        self.mock_db_pool = Mock()
        
        # Create task manager with mocked pool
        self.task_manager = BackgroundTaskManager(self.mock_db_pool)
        
        # Create FIR service
        self.fir_service = FIRService(self.task_manager)
    
    def test_on_fir_completed_triggers_all_tasks(self):
        """Test that FIR completion triggers email, report, and analytics tasks"""
        # Mock the enqueue_task method
        self.task_manager.enqueue_task = Mock(side_effect=["task-1", "task-2", "task-3"])
        
        # Call on_fir_completed with all options enabled
        result = self.fir_service.on_fir_completed(
            fir_number="FIR-12345",
            session_id="session-abc",
            recipient_email="user@example.com",
            generate_report=True,
            update_analytics=True
        )
        
        # Verify all three tasks were enqueued
        assert self.task_manager.enqueue_task.call_count == 3
        
        # Verify task IDs returned
        assert "email" in result
        assert "report" in result
        assert "analytics" in result
        assert result["email"] == "task-1"
        assert result["report"] == "task-2"
        assert result["analytics"] == "task-3"
        
        # Verify email task parameters
        email_call = self.task_manager.enqueue_task.call_args_list[0]
        assert email_call[1]["task_name"] == "afirgen_tasks.email.send_fir_confirmation"
        assert email_call[1]["task_type"] == TaskType.EMAIL
        assert email_call[1]["params"]["fir_id"] == "FIR-12345"
        assert email_call[1]["params"]["recipient_email"] == "user@example.com"
        assert email_call[1]["priority"] == 3  # Low priority
        
        # Verify report task parameters
        report_call = self.task_manager.enqueue_task.call_args_list[1]
        assert report_call[1]["task_name"] == "afirgen_tasks.reports.generate_pdf"
        assert report_call[1]["task_type"] == TaskType.REPORT
        assert report_call[1]["params"]["fir_id"] == "FIR-12345"
        assert report_call[1]["priority"] == 5  # Medium priority
        
        # Verify analytics task parameters
        analytics_call = self.task_manager.enqueue_task.call_args_list[2]
        assert analytics_call[1]["task_name"] == "afirgen_tasks.analytics.update_dashboard"
        assert analytics_call[1]["task_type"] == TaskType.ANALYTICS
        assert analytics_call[1]["priority"] == 2  # Low priority
    
    def test_on_fir_completed_without_email(self):
        """Test FIR completion without email notification"""
        self.task_manager.enqueue_task = Mock(side_effect=["task-1", "task-2"])
        
        result = self.fir_service.on_fir_completed(
            fir_number="FIR-12345",
            session_id="session-abc",
            recipient_email=None,  # No email
            generate_report=True,
            update_analytics=True
        )
        
        # Only 2 tasks should be enqueued (report and analytics)
        assert self.task_manager.enqueue_task.call_count == 2
        assert "email" not in result
        assert "report" in result
        assert "analytics" in result
    
    def test_on_fir_completed_minimal(self):
        """Test FIR completion with minimal options"""
        self.task_manager.enqueue_task = Mock(return_value="task-1")
        
        result = self.fir_service.on_fir_completed(
            fir_number="FIR-12345",
            session_id="session-abc",
            recipient_email=None,
            generate_report=False,
            update_analytics=False
        )
        
        # No tasks should be enqueued
        assert self.task_manager.enqueue_task.call_count == 0
        assert len(result) == 0
    
    def test_on_fir_completed_handles_task_failure(self):
        """Test that FIR completion continues even if task enqueueing fails"""
        # Mock enqueue_task to fail for email but succeed for others
        def mock_enqueue(task_name, **kwargs):
            if "email" in task_name:
                raise Exception("Email service unavailable")
            return "task-success"
        
        self.task_manager.enqueue_task = Mock(side_effect=mock_enqueue)
        
        # Should not raise exception
        result = self.fir_service.on_fir_completed(
            fir_number="FIR-12345",
            session_id="session-abc",
            recipient_email="user@example.com",
            generate_report=True,
            update_analytics=True
        )
        
        # Email task should fail but others should succeed
        assert "email" not in result
        assert "report" in result
        assert "analytics" in result
    
    def test_on_fir_finalized_triggers_notification(self):
        """Test that FIR finalization triggers notification email"""
        self.task_manager.enqueue_task = Mock(return_value="task-1")
        
        result = self.fir_service.on_fir_finalized(
            fir_number="FIR-12345",
            recipient_email="user@example.com"
        )
        
        # Verify notification email was enqueued
        assert self.task_manager.enqueue_task.call_count == 1
        assert "email" in result
        
        # Verify task parameters
        call_args = self.task_manager.enqueue_task.call_args[1]
        assert call_args["task_name"] == "afirgen_tasks.email.send_notification"
        assert call_args["task_type"] == TaskType.EMAIL
        assert call_args["params"]["recipient_email"] == "user@example.com"
        assert "FIR-12345" in call_args["params"]["subject"]
        assert call_args["priority"] == 3
    
    def test_on_fir_finalized_without_email(self):
        """Test FIR finalization without email"""
        self.task_manager.enqueue_task = Mock()
        
        result = self.fir_service.on_fir_finalized(
            fir_number="FIR-12345",
            recipient_email=None
        )
        
        # No tasks should be enqueued
        assert self.task_manager.enqueue_task.call_count == 0
        assert len(result) == 0
    
    def test_generate_bulk_report(self):
        """Test bulk report generation"""
        self.task_manager.enqueue_task = Mock(return_value="task-bulk-report")
        
        fir_ids = ["FIR-001", "FIR-002", "FIR-003"]
        task_id = self.fir_service.generate_bulk_report(
            fir_ids=fir_ids,
            report_name="monthly_report",
            priority=7
        )
        
        assert task_id == "task-bulk-report"
        
        # Verify task parameters
        call_args = self.task_manager.enqueue_task.call_args[1]
        assert call_args["task_name"] == "afirgen_tasks.reports.generate_excel"
        assert call_args["task_type"] == TaskType.REPORT
        assert call_args["params"]["fir_ids"] == fir_ids
        assert call_args["params"]["report_name"] == "monthly_report"
        assert call_args["priority"] == 7
    
    def test_process_analytics(self):
        """Test analytics processing"""
        self.task_manager.enqueue_task = Mock(return_value="task-analytics")
        
        date_range = {"start_date": "2024-01-01", "end_date": "2024-01-31"}
        task_id = self.fir_service.process_analytics(
            data_type="fir_trends",
            date_range=date_range,
            priority=4
        )
        
        assert task_id == "task-analytics"
        
        # Verify task parameters
        call_args = self.task_manager.enqueue_task.call_args[1]
        assert call_args["task_name"] == "afirgen_tasks.analytics.process_data"
        assert call_args["task_type"] == TaskType.ANALYTICS
        assert call_args["params"]["data_type"] == "fir_trends"
        assert call_args["params"]["date_range"] == date_range
        assert call_args["priority"] == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
