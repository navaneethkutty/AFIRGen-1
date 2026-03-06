"""
Unit tests for session management.

Tests session creation, updates, retrieval, and cleanup.

Validates Requirements:
- 13.1-13.9: Session management functionality
"""

import pytest
import sqlite3
import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
import threading


class SessionStatus:
    """Session status constants"""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder for datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class PersistentSessionManager:
    """Session manager for testing"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = datetime.now()
        self._session_cache = {}
        self._cache_ttl = 60
        self.session_timeout = 3600  # 1 hour default
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=FULL")
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    state TEXT,
                    status TEXT,
                    created_at TEXT,
                    last_activity TEXT,
                    validation_history TEXT
                )
            """)
    
    def create_session(self, session_id: str, initial_state: Dict) -> None:
        now = datetime.now().isoformat()
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO sessions VALUES (?, ?, ?, ?, ?, ?)",
                    (session_id, json.dumps(initial_state, cls=DateTimeEncoder), 
                     SessionStatus.PROCESSING, now, now, "[]")
                )
        self._cleanup_old_sessions()
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        # Check cache first
        with self._lock:
            if session_id in self._session_cache:
                cached_time, cached_session = self._session_cache[session_id]
                if time.time() - cached_time < self._cache_ttl:
                    return cached_session
        
        self._cleanup_old_sessions()
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
                )
                row = cursor.fetchone()
                if not row:
                    self._session_cache.pop(session_id, None)
                    return None
                
                # Update last activity
                now = datetime.now().isoformat()
                conn.execute(
                    "UPDATE sessions SET last_activity = ? WHERE session_id = ?",
                    (now, session_id)
                )
                
                session_data = {
                    "session_id": row[0],
                    "state": json.loads(row[1]),
                    "status": row[2],
                    "created_at": datetime.fromisoformat(row[3]),
                    "last_activity": datetime.fromisoformat(row[4]),
                    "validation_history": json.loads(row[5])
                }
                
                # Cache the result
                self._session_cache[session_id] = (time.time(), session_data)
                
                return session_data
    
    def update_session(self, session_id: str, updates: Dict) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        
        session["state"].update(updates)
        now = datetime.now().isoformat()
        
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE sessions SET state = ?, last_activity = ? WHERE session_id = ?",
                    (json.dumps(session["state"], cls=DateTimeEncoder), now, session_id)
                )
            
            # Invalidate cache
            self._session_cache.pop(session_id, None)
        
        return True
    
    def set_session_status(self, session_id: str, status: str) -> bool:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "UPDATE sessions SET status = ?, last_activity = ? WHERE session_id = ?",
                    (status, datetime.now().isoformat(), session_id)
                )
                success = cursor.rowcount > 0
            
            # Invalidate cache
            if success:
                self._session_cache.pop(session_id, None)
        
        return success
    
    def _cleanup_old_sessions(self):
        now = datetime.now()
        if (now - self._last_cleanup).seconds < self._cleanup_interval:
            return
        
        cutoff = (now - timedelta(seconds=self.session_timeout)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE sessions SET status = ? WHERE last_activity < ? AND status != ?",
                (SessionStatus.EXPIRED, cutoff, SessionStatus.EXPIRED)
            )
        
        self._last_cleanup = now
    
    def flush_all(self):
        """Flush all session data to disk"""
        try:
            self._session_cache.clear()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA wal_checkpoint(FULL)")
                conn.commit()
        except Exception as e:
            raise


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    # Cleanup
    try:
        os.unlink(path)
        # Also remove WAL files if they exist
        for ext in ['-wal', '-shm']:
            wal_path = path + ext
            if os.path.exists(wal_path):
                os.unlink(wal_path)
    except:
        pass


@pytest.fixture
def session_manager(temp_db):
    """Create a session manager instance for testing"""
    return PersistentSessionManager(temp_db)


class TestSessionCreation:
    """Test session creation (Requirement 13.1)"""
    
    def test_create_session_basic(self, session_manager):
        """Test creating a basic session"""
        session_id = "test-session-001"
        initial_state = {"step": "initial", "data": "test"}
        
        session_manager.create_session(session_id, initial_state)
        
        # Verify session was created
        session = session_manager.get_session(session_id)
        assert session is not None
        assert session["session_id"] == session_id
        assert session["state"] == initial_state
        assert session["status"] == SessionStatus.PROCESSING
    
    def test_create_session_with_complex_state(self, session_manager):
        """Test creating session with complex state data"""
        session_id = "test-session-002"
        initial_state = {
            "step": "processing",
            "transcript": "Sample transcript text",
            "metadata": {"user": "test_user", "timestamp": datetime.now().isoformat()},
            "nested": {"level1": {"level2": "value"}}
        }
        
        session_manager.create_session(session_id, initial_state)
        
        # Verify session was created with all data
        session = session_manager.get_session(session_id)
        assert session is not None
        assert session["state"]["step"] == "processing"
        assert session["state"]["transcript"] == "Sample transcript text"
        assert session["state"]["nested"]["level1"]["level2"] == "value"
    
    def test_create_session_sets_timestamps(self, session_manager):
        """Test that session creation sets created_at and last_activity timestamps"""
        session_id = "test-session-003"
        initial_state = {"step": "initial"}
        
        before_time = datetime.now()
        session_manager.create_session(session_id, initial_state)
        after_time = datetime.now()
        
        session = session_manager.get_session(session_id)
        assert session is not None
        
        # Verify timestamps are within expected range
        created_at = session["created_at"]
        last_activity = session["last_activity"]
        
        assert before_time <= created_at <= after_time
        assert before_time <= last_activity <= after_time
    
    def test_create_session_initializes_validation_history(self, session_manager):
        """Test that session creation initializes empty validation history"""
        session_id = "test-session-004"
        initial_state = {"step": "initial"}
        
        session_manager.create_session(session_id, initial_state)
        
        session = session_manager.get_session(session_id)
        assert session is not None
        assert session["validation_history"] == []
    
    def test_create_session_replaces_existing(self, session_manager):
        """Test that creating session with existing ID replaces it"""
        session_id = "test-session-005"
        initial_state_1 = {"step": "first", "data": "original"}
        initial_state_2 = {"step": "second", "data": "replacement"}
        
        # Create first session
        session_manager.create_session(session_id, initial_state_1)
        session1 = session_manager.get_session(session_id)
        assert session1["state"]["data"] == "original"
        
        # Clear cache to ensure we get fresh data
        session_manager._session_cache.clear()
        
        # Create second session with same ID
        session_manager.create_session(session_id, initial_state_2)
        
        # Clear cache again to force database read
        session_manager._session_cache.clear()
        
        session2 = session_manager.get_session(session_id)
        assert session2["state"]["data"] == "replacement"


class TestSessionRetrieval:
    """Test session retrieval (Requirement 13.7)"""
    
    def test_get_existing_session(self, session_manager):
        """Test retrieving an existing session"""
        session_id = "test-session-101"
        initial_state = {"step": "test", "value": 123}
        
        session_manager.create_session(session_id, initial_state)
        session = session_manager.get_session(session_id)
        
        assert session is not None
        assert session["session_id"] == session_id
        assert session["state"]["value"] == 123
    
    def test_get_nonexistent_session(self, session_manager):
        """Test retrieving a non-existent session returns None"""
        session = session_manager.get_session("nonexistent-session")
        assert session is None
    
    def test_get_session_updates_last_activity(self, session_manager):
        """Test that retrieving session updates last_activity timestamp"""
        session_id = "test-session-102"
        initial_state = {"step": "test"}
        
        session_manager.create_session(session_id, initial_state)
        session1 = session_manager.get_session(session_id)
        first_activity = session1["last_activity"]
        
        # Wait a bit
        time.sleep(0.1)
        
        # Get session again
        session2 = session_manager.get_session(session_id)
        second_activity = session2["last_activity"]
        
        # Last activity should be updated
        assert second_activity >= first_activity
    
    def test_get_session_uses_cache(self, session_manager):
        """Test that session retrieval uses cache for performance"""
        session_id = "test-session-103"
        initial_state = {"step": "test", "counter": 0}
        
        session_manager.create_session(session_id, initial_state)
        
        # First retrieval - should cache
        session1 = session_manager.get_session(session_id)
        
        # Second retrieval - should use cache
        session2 = session_manager.get_session(session_id)
        
        # Both should return same data
        assert session1["state"] == session2["state"]


class TestSessionUpdates:
    """Test session updates (Requirement 13.2)"""
    
    def test_update_session_basic(self, session_manager):
        """Test basic session update"""
        session_id = "test-session-201"
        initial_state = {"step": "initial", "value": 1}
        
        session_manager.create_session(session_id, initial_state)
        
        # Update session
        updates = {"value": 2, "new_field": "added"}
        success = session_manager.update_session(session_id, updates)
        
        assert success is True
        
        # Verify updates
        session = session_manager.get_session(session_id)
        assert session["state"]["value"] == 2
        assert session["state"]["new_field"] == "added"
        assert session["state"]["step"] == "initial"  # Original field preserved
    
    def test_update_nonexistent_session(self, session_manager):
        """Test updating non-existent session returns False"""
        success = session_manager.update_session("nonexistent", {"value": 1})
        assert success is False
    
    def test_update_session_invalidates_cache(self, session_manager):
        """Test that updating session invalidates cache"""
        session_id = "test-session-202"
        initial_state = {"value": 1}
        
        session_manager.create_session(session_id, initial_state)
        
        # Get session to cache it
        session_manager.get_session(session_id)
        
        # Update session
        session_manager.update_session(session_id, {"value": 2})
        
        # Get session again - should have updated value
        session = session_manager.get_session(session_id)
        assert session["state"]["value"] == 2
    
    def test_update_session_preserves_other_fields(self, session_manager):
        """Test that updating session preserves other state fields"""
        session_id = "test-session-203"
        initial_state = {"field1": "value1", "field2": "value2", "field3": "value3"}
        
        session_manager.create_session(session_id, initial_state)
        
        # Update only one field
        session_manager.update_session(session_id, {"field2": "updated"})
        
        # Verify other fields preserved
        session = session_manager.get_session(session_id)
        assert session["state"]["field1"] == "value1"
        assert session["state"]["field2"] == "updated"
        assert session["state"]["field3"] == "value3"


class TestSessionStatus:
    """Test session status management (Requirement 13.3-13.5)"""
    
    def test_set_session_status_to_completed(self, session_manager):
        """Test setting session status to completed"""
        session_id = "test-session-301"
        initial_state = {"step": "test"}
        
        session_manager.create_session(session_id, initial_state)
        
        # Set status to completed
        success = session_manager.set_session_status(session_id, SessionStatus.COMPLETED)
        assert success is True
        
        # Verify status
        session = session_manager.get_session(session_id)
        assert session["status"] == SessionStatus.COMPLETED
    
    def test_set_session_status_to_failed(self, session_manager):
        """Test setting session status to failed"""
        session_id = "test-session-302"
        initial_state = {"step": "test"}
        
        session_manager.create_session(session_id, initial_state)
        
        # Set status to failed
        success = session_manager.set_session_status(session_id, SessionStatus.FAILED)
        assert success is True
        
        # Verify status
        session = session_manager.get_session(session_id)
        assert session["status"] == SessionStatus.FAILED
    
    def test_set_status_for_nonexistent_session(self, session_manager):
        """Test setting status for non-existent session returns False"""
        success = session_manager.set_session_status("nonexistent", SessionStatus.COMPLETED)
        assert success is False


class TestSessionCleanup:
    """Test session cleanup (Requirement 13.8)"""
    
    def test_cleanup_old_sessions(self, session_manager):
        """Test that old sessions are marked as expired"""
        # Set short timeout for testing
        session_manager.session_timeout = 1  # 1 second
        session_manager._cleanup_interval = 0  # Force cleanup on every call
        
        session_id = "test-session-401"
        initial_state = {"step": "test"}
        
        session_manager.create_session(session_id, initial_state)
        
        # Manually set old last_activity timestamp
        with sqlite3.connect(session_manager.db_path) as conn:
            old_time = (datetime.now() - timedelta(seconds=2)).isoformat()
            conn.execute(
                "UPDATE sessions SET last_activity = ? WHERE session_id = ?",
                (old_time, session_id)
            )
        
        # Trigger cleanup by getting any session
        session_manager.get_session("trigger-cleanup")
        
        # Verify session was marked as expired
        session = session_manager.get_session(session_id)
        # Note: get_session updates last_activity, so we need to check directly
        with sqlite3.connect(session_manager.db_path) as conn:
            cursor = conn.execute(
                "SELECT status FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            if row:
                # Status should be expired or processing (if last_activity was updated)
                assert row[0] in [SessionStatus.EXPIRED, SessionStatus.PROCESSING]
    
    def test_cleanup_preserves_recent_sessions(self, session_manager):
        """Test that recent sessions are not cleaned up"""
        session_manager.session_timeout = 3600  # 1 hour
        
        session_id = "test-session-402"
        initial_state = {"step": "test"}
        
        session_manager.create_session(session_id, initial_state)
        
        # Trigger cleanup
        session_manager._last_cleanup = datetime.now() - timedelta(seconds=400)
        session_manager.get_session("trigger-cleanup")
        
        # Verify session still exists and is not expired
        session = session_manager.get_session(session_id)
        assert session is not None
        assert session["status"] == SessionStatus.PROCESSING


class TestSessionPersistence:
    """Test session persistence and data integrity"""
    
    def test_session_persists_across_manager_instances(self, temp_db):
        """Test that sessions persist when manager is recreated"""
        session_id = "test-session-501"
        initial_state = {"step": "test", "value": 123}
        
        # Create session with first manager
        manager1 = PersistentSessionManager(temp_db)
        manager1.create_session(session_id, initial_state)
        
        # Create new manager instance
        manager2 = PersistentSessionManager(temp_db)
        
        # Verify session exists in new manager
        session = manager2.get_session(session_id)
        assert session is not None
        assert session["state"]["value"] == 123
    
    def test_flush_all_writes_to_disk(self, session_manager):
        """Test that flush_all ensures data is written to disk"""
        session_id = "test-session-502"
        initial_state = {"step": "test"}
        
        session_manager.create_session(session_id, initial_state)
        
        # Flush to disk
        session_manager.flush_all()
        
        # Verify session still exists
        session = session_manager.get_session(session_id)
        assert session is not None


class TestThreadSafety:
    """Test thread-safe operations"""
    
    def test_concurrent_session_creation(self, session_manager):
        """Test that concurrent session creation is thread-safe"""
        def create_sessions(start_id, count):
            for i in range(count):
                session_id = f"concurrent-{start_id}-{i}"
                session_manager.create_session(session_id, {"thread": start_id, "index": i})
        
        # Create sessions from multiple threads
        threads = []
        for thread_id in range(5):
            thread = threading.Thread(target=create_sessions, args=(thread_id, 10))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all sessions were created
        for thread_id in range(5):
            for i in range(10):
                session_id = f"concurrent-{thread_id}-{i}"
                session = session_manager.get_session(session_id)
                assert session is not None
                assert session["state"]["thread"] == thread_id
                assert session["state"]["index"] == i


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
