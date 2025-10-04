"""
Audit Trail Module - Comprehensive logging and tracking of safety decisions.

This module implements audit trail functionality to track all safety-related decisions,
user actions, and system events for accountability and debugging purposes.
"""

import json
import hashlib
import threading
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import logging

from .security.secure_file_ops import (
    SecureFileOperations, SecurityLevel, FileOperationError,
    write_json_secure, read_json_secure
)


class SafetyDecision(Enum):
    """Safety decision types."""
    PROTECTED = "protected"
    SAFE_TO_DELETE = "safe_to_delete"
    MANUAL_REVIEW = "manual_review"
    REQUIRES_CONFIRMATION = "requires_confirmation"


class AuditLogEntry:
    """Single audit log entry."""

    def __init__(
        self,
        file_path: str,
        decision: SafetyDecision,
        reason: str,
        confidence: float,
        timestamp: Optional[datetime] = None,
        user_action: Optional[str] = None,
        user_comment: Optional[str] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        operation: Optional[str] = None,
        processing_time: Optional[float] = None,
        file_count: Optional[int] = None,
        memory_usage: Optional[str] = None
    ):
        self.file_path = file_path
        self.decision = decision
        self.reason = reason
        self.confidence = confidence
        self.timestamp = timestamp or datetime.now()
        self.user_action = user_action
        self.user_comment = user_comment
        self.error_type = error_type
        self.error_message = error_message
        self.operation = operation
        self.processing_time = processing_time
        self.file_count = file_count
        self.memory_usage = memory_usage

        # Generate unique ID for this entry
        self.id = self._generate_id()

    def _generate_id(self) -> str:
        """Generate unique ID for this log entry."""
        content = f"{self.file_path}{self.timestamp.isoformat()}{self.decision.value}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "decision": self.decision.value,
            "reason": self.reason,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "user_action": self.user_action,
            "user_comment": self.user_comment,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "operation": self.operation,
            "processing_time": self.processing_time,
            "file_count": self.file_count,
            "memory_usage": self.memory_usage
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditLogEntry":
        """Create from dictionary."""
        entry = cls(
            file_path=data["file_path"],
            decision=SafetyDecision(data["decision"]),
            reason=data["reason"],
            confidence=data["confidence"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            user_action=data.get("user_action"),
            user_comment=data.get("user_comment"),
            error_type=data.get("error_type"),
            error_message=data.get("error_message"),
            operation=data.get("operation"),
            processing_time=data.get("processing_time"),
            file_count=data.get("file_count"),
            memory_usage=data.get("memory_usage")
        )
        entry.id = data["id"]
        return entry


class IntegrityCheck:
    """Result of audit log integrity check."""

    def __init__(self, is_valid: bool, entry_count: int, checksum: Optional[str] = None, issues: List[str] = None):
        self.is_valid = is_valid
        self.entry_count = entry_count
        self.checksum = checksum
        self.issues = issues or []


class AuditTrail:
    """
    Comprehensive audit trail system for tracking safety decisions.

    This class provides complete audit logging for all safety-related operations,
    ensuring accountability and providing debugging capabilities.
    """

    def __init__(self, log_file_path: Optional[str] = None):
        self.log_file_path = log_file_path or "audit_trail.json"
        self.logs: List[AuditLogEntry] = []
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

        # Initialize secure file operations
        self.secure_ops = SecureFileOperations(self.logger)

        # Load existing logs if file exists
        self.load_logs()

    def log_safety_decision(
        self,
        file_path: str,
        decision: SafetyDecision,
        reason: str,
        confidence: float
    ):
        """Log a safety decision for a file."""
        with self.lock:
            entry = AuditLogEntry(
                file_path=file_path,
                decision=decision,
                reason=reason,
                confidence=confidence
            )
            self.logs.append(entry)

            # Log to application logger as well
            self.logger.info(
                f"Safety decision for {file_path}: {decision.value} "
                f"(confidence: {confidence:.2f}, reason: {reason})"
            )

    def log_user_action(
        self,
        file_path: str,
        action: str,
        comment: Optional[str] = None
    ):
        """Log a user action."""
        with self.lock:
            entry = AuditLogEntry(
                file_path=file_path,
                decision=SafetyDecision.MANUAL_REVIEW,  # Default decision for user actions
                reason=f"User action: {action}",
                confidence=1.0,  # User actions have full confidence
                user_action=action,
                user_comment=comment
            )
            self.logs.append(entry)

            self.logger.info(f"User action for {file_path}: {action}")

    def log_error(
        self,
        file_path: str,
        error_type: str,
        error_message: str
    ):
        """Log an error that occurred during safety assessment."""
        with self.lock:
            entry = AuditLogEntry(
                file_path=file_path,
                decision=SafetyDecision.PROTECTED,  # Default to protected on error
                reason=f"Error: {error_type}",
                confidence=0.0,  # No confidence on error
                error_type=error_type,
                error_message=error_message
            )
            self.logs.append(entry)

            self.logger.error(f"Error processing {file_path}: {error_type} - {error_message}")

    def log_threshold_application(
        self,
        file_path: str,
        confidence: float,
        threshold: float,
        decision: SafetyDecision
    ):
        """Log confidence threshold application."""
        with self.lock:
            entry = AuditLogEntry(
                file_path=file_path,
                decision=decision,
                reason=f"Confidence threshold applied: {confidence:.2f} vs {threshold:.2f}",
                confidence=confidence
            )
            self.logs.append(entry)

            self.logger.info(
                f"Threshold application for {file_path}: {confidence:.2f} vs {threshold:.2f} -> {decision.value}"
            )

    def log_performance_metrics(
        self,
        operation: str,
        processing_time: float,
        file_count: int,
        memory_usage: Optional[str] = None
    ):
        """Log performance metrics for an operation."""
        with self.lock:
            entry = AuditLogEntry(
                file_path="",  # Not file-specific
                decision=SafetyDecision.SAFE_TO_DELETE,  # Placeholder
                reason=f"Performance metrics for {operation}",
                confidence=1.0,
                operation=operation,
                processing_time=processing_time,
                file_count=file_count,
                memory_usage=memory_usage
            )
            self.logs.append(entry)

            self.logger.info(
                f"Performance: {operation} - {processing_time:.3f}s for {file_count} files "
                f"(memory: {memory_usage or 'unknown'})"
            )

    def get_recent_logs(self, limit: int = 100) -> List[AuditLogEntry]:
        """Get the most recent log entries."""
        with self.lock:
            return sorted(self.logs, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_all_logs(self) -> List[AuditLogEntry]:
        """Get all log entries."""
        with self.lock:
            return self.logs.copy()

    def filter_logs_by_decision(self, decision: SafetyDecision) -> List[AuditLogEntry]:
        """Filter logs by decision type."""
        with self.lock:
            return [log for log in self.logs if log.decision == decision]

    def filter_logs_by_file_pattern(self, pattern: str) -> List[AuditLogEntry]:
        """Filter logs by file path pattern."""
        import fnmatch
        with self.lock:
            return [log for log in self.logs if fnmatch.fnmatch(log.file_path, pattern)]

    def filter_logs_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[AuditLogEntry]:
        """Filter logs by time range."""
        with self.lock:
            return [
                log for log in self.logs
                if start_time <= log.timestamp <= end_time
            ]

    def save_logs(self):
        """Save logs to persistent storage with secure file operations."""
        try:
            with self.lock:
                logs_data = [log.to_dict() for log in self.logs]

                # Use secure file operations with SENSITIVE level for audit logs
                # Audit logs may contain sensitive file paths and user information
                self.secure_ops.write_json_secure(
                    self.log_file_path,
                    {"audit_logs": logs_data, "metadata": {
                        "version": "1.0",
                        "created_at": datetime.now().isoformat(),
                        "total_entries": len(logs_data)
                    }},
                    security_level=SecurityLevel.SENSITIVE,
                    redact_sensitive_fields=False  # Keep all data for audit purposes
                )

                self.logger.info(f"Securely saved {len(logs_data)} log entries to {self.log_file_path}")

        except FileOperationError as e:
            self.logger.error(f"Failed to save logs securely: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error saving logs: {e}")

    def load_logs(self):
        """Load logs from persistent storage with secure file operations."""
        try:
            if Path(self.log_file_path).exists():
                # Use secure file operations to read logs
                audit_data = self.secure_ops.read_json_secure(
                    self.log_file_path,
                    verify_integrity=True
                )

                # Handle both old format (direct array) and new format (with metadata)
                if isinstance(audit_data, dict) and "audit_logs" in audit_data:
                    logs_data = audit_data["audit_logs"]
                    metadata = audit_data.get("metadata", {})
                    self.logger.info(f"Loading audit logs v{metadata.get('version', 'unknown')}")
                elif isinstance(audit_data, list):
                    # Legacy format - direct array of logs
                    logs_data = audit_data
                    self.logger.info("Loading legacy audit log format")
                else:
                    raise ValueError("Invalid audit log file format")

                with self.lock:
                    self.logs = [AuditLogEntry.from_dict(data) for data in logs_data]

                self.logger.info(f"Securely loaded {len(self.logs)} log entries from {self.log_file_path}")

        except (FileOperationError, FileIntegrityError) as e:
            self.logger.error(f"Failed to load logs securely: {e}")
            self.logs = []
        except (ValueError, KeyError) as e:
            self.logger.error(f"Invalid audit log format in {self.log_file_path}: {e}")
            self.logs = []
        except Exception as e:
            self.logger.error(f"Unexpected error loading logs: {e}")
            self.logs = []

    def verify_integrity(self) -> IntegrityCheck:
        """Verify the integrity of the audit logs."""
        with self.lock:
            issues = []

            # Check for duplicate IDs
            ids = [log.id for log in self.logs]
            duplicate_ids = [id for id in ids if ids.count(id) > 1]
            if duplicate_ids:
                issues.append(f"Duplicate log IDs found: {duplicate_ids}")

            # Check for missing required fields
            for i, log in enumerate(self.logs):
                if not log.file_path:
                    issues.append(f"Log {i}: Missing file path")
                if not log.decision:
                    issues.append(f"Log {i}: Missing decision")
                if not log.reason:
                    issues.append(f"Log {i}: Missing reason")
                if log.confidence < 0 or log.confidence > 1:
                    issues.append(f"Log {i}: Invalid confidence value: {log.confidence}")

            # Generate checksum and verify it matches stored checksum if available
            checksum = self._generate_checksum()

            # For test purposes, check if the logs have been modified by comparing current state
            # This is a simple check - in production, you'd want to store checksums separately
            for i, log in enumerate(self.logs):
                # Recalculate the ID to detect tampering
                original_id = log.id
                content = f"{log.file_path}{log.timestamp.isoformat()}{log.decision.value}"
                calculated_id = hashlib.sha256(content.encode()).hexdigest()[:16]

                if original_id != calculated_id:
                    issues.append(f"Log {i}: Tampering detected - ID mismatch")

            is_valid = len(issues) == 0
            return IntegrityCheck(
                is_valid=is_valid,
                entry_count=len(self.logs),
                checksum=checksum,
                issues=issues
            )

    def _generate_checksum(self) -> str:
        """Generate checksum for all log entries."""
        content = json.dumps([log.to_dict() for log in self.logs], sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def clear_logs(self):
        """Clear all log entries."""
        with self.lock:
            self.logs.clear()
            self.logger.info("Cleared all audit log entries")

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the audit logs."""
        with self.lock:
            if not self.logs:
                return {
                    "total_entries": 0,
                    "decision_counts": {},
                    "error_count": 0,
                    "date_range": None
                }

            # Count decisions
            decision_counts = {}
            for decision in SafetyDecision:
                decision_counts[decision.value] = len(self.filter_logs_by_decision(decision))

            # Count errors
            error_count = len([log for log in self.logs if log.error_type])

            # Date range
            timestamps = [log.timestamp for log in self.logs]
            date_range = {
                "earliest": min(timestamps).isoformat(),
                "latest": max(timestamps).isoformat()
            }

            return {
                "total_entries": len(self.logs),
                "decision_counts": decision_counts,
                "error_count": error_count,
                "date_range": date_range
            }

    def export_logs(
        self,
        output_path: str,
        format_type: str = "json",
        filters: Optional[Dict[str, Any]] = None,
        security_level: SecurityLevel = SecurityLevel.PUBLIC
    ):
        """Export logs to file with optional filters using secure file operations."""
        # Apply filters if provided
        if filters:
            filtered_logs = self.logs.copy()

            if "decision" in filters:
                filtered_logs = [log for log in filtered_logs if log.decision.value == filters["decision"]]

            if "start_time" in filters:
                start_time = datetime.fromisoformat(filters["start_time"])
                filtered_logs = [log for log in filtered_logs if log.timestamp >= start_time]

            if "end_time" in filters:
                end_time = datetime.fromisoformat(filters["end_time"])
                filtered_logs = [log for log in filtered_logs if log.timestamp <= end_time]

            if "file_pattern" in filters:
                import fnmatch
                pattern = filters["file_pattern"]
                filtered_logs = [log for log in filtered_logs if fnmatch.fnmatch(log.file_path, pattern)]
        else:
            filtered_logs = self.logs

        try:
            # Export based on format using secure operations
            if format_type.lower() == "json":
                export_data = {
                    "exported_logs": [log.to_dict() for log in filtered_logs],
                    "metadata": {
                        "exported_at": datetime.now().isoformat(),
                        "total_entries": len(filtered_logs),
                        "filters": filters or {},
                        "format": "json",
                        "version": "1.0"
                    }
                }

                self.secure_ops.write_json_secure(
                    output_path,
                    export_data,
                    security_level=security_level,
                    redact_sensitive_fields=(security_level == SecurityLevel.PUBLIC)
                )

            elif format_type.lower() == "csv":
                # For CSV export, we need to handle it differently since it's not JSON
                with self.secure_ops.secure_open(output_path, 'w', security_level) as f:
                    if filtered_logs:
                        import csv
                        writer = csv.DictWriter(f, fieldnames=filtered_logs[0].to_dict().keys())
                        writer.writeheader()
                        for log in filtered_logs:
                            log_dict = log.to_dict()
                            # Redact sensitive data for public exports
                            if security_level == SecurityLevel.PUBLIC:
                                log_dict = self._redact_sensitive_log_data(log_dict)
                            writer.writerow(log_dict)

            else:
                raise ValueError(f"Unsupported export format: {format_type}")

            self.logger.info(f"Securely exported {len(filtered_logs)} log entries to {output_path} (level: {security_level.name})")

        except FileOperationError as e:
            self.logger.error(f"Failed to export logs securely: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during export: {e}")
            raise

    def _redact_sensitive_log_data(self, log_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive information from log data for public exports."""
        redacted = log_dict.copy()

        # Redact potentially sensitive file paths
        if 'file_path' in redacted:
            path_parts = redacted['file_path'].split('/')
            if len(path_parts) > 2:
                # Keep only the last two parts of the path
                redacted['file_path'] = '.../' + '/'.join(path_parts[-2:])

        # Redact user comments if they might contain sensitive info
        if 'user_comment' in redacted and redacted['user_comment']:
            redacted['user_comment'] = '[REDACTED]'

        # Redact detailed error messages that might contain paths
        if 'error_message' in redacted and redacted['error_message']:
            if '/' in redacted['error_message'] or '\\' in redacted['error_message']:
                redacted['error_message'] = '[PATH_REDACTED]'

        return redacted

    def search_logs(self, query: str) -> List[AuditLogEntry]:
        """Search logs for specific text."""
        query_lower = query.lower()
        with self.lock:
            return [
                log for log in self.logs
                if (query_lower in log.file_path.lower() or
                    query_lower in log.reason.lower() or
                    (log.user_comment and query_lower in log.user_comment.lower()) or
                    (log.error_message and query_lower in log.error_message.lower()))
            ]