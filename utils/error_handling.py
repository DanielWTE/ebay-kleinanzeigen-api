"""
Comprehensive error handling and warnings system for the Kleinanzeigen API.

This module provides structured error categorization, warning management,
and detailed logging capabilities to handle partial failures gracefully
while maintaining comprehensive debugging information.
"""

import logging
import time
import traceback
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from contextlib import contextmanager


class ErrorCategory(Enum):
    """
    Categorization of errors for proper handling and recovery strategies.

    RECOVERABLE: Errors that can be retried with a reasonable chance of success
    NON_RECOVERABLE: Permanent errors that won't be resolved by retrying
    RESOURCE: Errors related to system resource limitations
    NETWORK: Network-related errors (timeouts, connection issues)
    PARSING: Data parsing or extraction errors
    VALIDATION: Input validation errors
    BROWSER: Browser-specific errors (context issues, page load failures)
    """

    RECOVERABLE = "recoverable"
    NON_RECOVERABLE = "non_recoverable"
    RESOURCE = "resource"
    NETWORK = "network"
    PARSING = "parsing"
    VALIDATION = "validation"
    BROWSER = "browser"


class ErrorSeverity(Enum):
    """
    Severity levels for errors and warnings.

    LOW: Minor issues that don't significantly impact functionality
    MEDIUM: Issues that cause partial failures but allow operation to continue
    HIGH: Serious issues that significantly impact functionality
    CRITICAL: Critical errors that prevent operation completion
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """
    Detailed context information for debugging and error analysis.
    """

    operation: str  # The operation being performed when error occurred
    page_number: Optional[int] = None
    url: Optional[str] = None
    listing_id: Optional[str] = None
    retry_attempt: int = 0
    timestamp: float = field(default_factory=time.time)
    browser_context_id: Optional[str] = None
    concurrent_operations: int = 0
    memory_usage: Optional[Dict[str, Any]] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging and API responses."""
        return {
            "operation": self.operation,
            "page_number": self.page_number,
            "url": self.url,
            "listing_id": self.listing_id,
            "retry_attempt": self.retry_attempt,
            "timestamp": self.timestamp,
            "browser_context_id": self.browser_context_id,
            "concurrent_operations": self.concurrent_operations,
            "memory_usage": self.memory_usage,
            "additional_data": self.additional_data,
        }


@dataclass
class StructuredError:
    """
    Structured error representation with categorization and context.
    """

    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    context: ErrorContext
    original_exception: Optional[Exception] = None
    stack_trace: Optional[str] = None
    recovery_suggestions: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Capture stack trace if original exception is provided."""
        if self.original_exception and not self.stack_trace:
            self.stack_trace = traceback.format_exception(
                type(self.original_exception),
                self.original_exception,
                self.original_exception.__traceback__,
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging and API responses."""
        return {
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": self.context.to_dict(),
            "recovery_suggestions": self.recovery_suggestions,
            "stack_trace": self.stack_trace if self.stack_trace else None,
        }

    def is_recoverable(self) -> bool:
        """Check if this error is potentially recoverable through retry."""
        return self.category in [
            ErrorCategory.RECOVERABLE,
            ErrorCategory.NETWORK,
            ErrorCategory.RESOURCE,
        ]

    def should_retry(self, max_retries: int = 3) -> bool:
        """Determine if this error should trigger a retry attempt."""
        return (
            self.is_recoverable()
            and self.context.retry_attempt < max_retries
            and self.severity != ErrorSeverity.CRITICAL
        )


@dataclass
class Warning:
    """
    Structured warning for partial failures and non-critical issues.
    """

    message: str
    severity: ErrorSeverity
    context: ErrorContext
    affected_items: List[str] = field(
        default_factory=list
    )  # IDs or descriptions of affected items
    impact_description: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "message": self.message,
            "severity": self.severity.value,
            "context": self.context.to_dict(),
            "affected_items": self.affected_items,
            "impact_description": self.impact_description,
            "timestamp": self.timestamp,
        }


class ErrorClassifier:
    """
    Utility class for classifying exceptions into structured errors.
    """

    @staticmethod
    def classify_exception(
        exception: Exception, context: ErrorContext, operation_type: str = "unknown"
    ) -> StructuredError:
        """
        Classify an exception into a structured error with appropriate category and severity.

        Args:
            exception: The exception to classify
            context: Context information about when/where the error occurred
            operation_type: Type of operation being performed

        Returns:
            StructuredError with appropriate classification
        """
        error_message = str(exception)
        exception_type = type(exception).__name__

        # Network-related errors
        if any(
            keyword in error_message.lower()
            for keyword in [
                "timeout",
                "connection",
                "network",
                "dns",
                "resolve",
                "unreachable",
            ]
        ):
            return StructuredError(
                message=f"Network error during {operation_type}: {error_message}",
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM,
                context=context,
                original_exception=exception,
                recovery_suggestions=[
                    "Retry the operation after a brief delay",
                    "Check network connectivity",
                    "Verify the target URL is accessible",
                ],
            )

        # Browser-specific errors
        if (
            any(
                keyword in error_message.lower()
                for keyword in ["browser", "context", "page", "playwright", "chromium"]
            )
            or "Target page, context or browser has been closed" in error_message
        ):
            return StructuredError(
                message=f"Browser error during {operation_type}: {error_message}",
                category=ErrorCategory.BROWSER,
                severity=ErrorSeverity.HIGH,
                context=context,
                original_exception=exception,
                recovery_suggestions=[
                    "Recreate browser context",
                    "Retry with a fresh browser instance",
                    "Check browser resource limits",
                ],
            )

        # Resource exhaustion errors
        if any(
            keyword in error_message.lower()
            for keyword in [
                "memory",
                "resource",
                "limit",
                "quota",
                "exhausted",
                "semaphore",
            ]
        ):
            return StructuredError(
                message=f"Resource limitation during {operation_type}: {error_message}",
                category=ErrorCategory.RESOURCE,
                severity=ErrorSeverity.HIGH,
                context=context,
                original_exception=exception,
                recovery_suggestions=[
                    "Reduce concurrent operations",
                    "Wait for resources to become available",
                    "Implement backpressure control",
                ],
            )

        # Parsing/extraction errors
        if any(
            keyword in error_message.lower()
            for keyword in [
                "parse",
                "extract",
                "selector",
                "element not found",
                "query_selector",
            ]
        ):
            return StructuredError(
                message=f"Data extraction error during {operation_type}: {error_message}",
                category=ErrorCategory.PARSING,
                severity=ErrorSeverity.MEDIUM,
                context=context,
                original_exception=exception,
                recovery_suggestions=[
                    "Check if page structure has changed",
                    "Verify CSS selectors are correct",
                    "Retry with updated extraction logic",
                ],
            )

        # Validation errors
        if any(
            keyword in error_message.lower()
            for keyword in ["validation", "invalid", "missing", "required", "format"]
        ):
            return StructuredError(
                message=f"Validation error during {operation_type}: {error_message}",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                context=context,
                original_exception=exception,
                recovery_suggestions=[
                    "Check input parameters",
                    "Validate data format",
                    "Review API documentation",
                ],
            )

        # HTTP errors
        if "HTTPException" in exception_type or any(
            keyword in error_message.lower()
            for keyword in ["http", "404", "500", "403", "forbidden", "not found"]
        ):
            severity = (
                ErrorSeverity.HIGH if "500" in error_message else ErrorSeverity.MEDIUM
            )
            category = (
                ErrorCategory.NON_RECOVERABLE
                if "404" in error_message
                else ErrorCategory.RECOVERABLE
            )

            return StructuredError(
                message=f"HTTP error during {operation_type}: {error_message}",
                category=category,
                severity=severity,
                context=context,
                original_exception=exception,
                recovery_suggestions=[
                    "Check URL validity"
                    if "404" in error_message
                    else "Retry after delay",
                    "Verify server availability",
                    "Check for rate limiting",
                ],
            )

        # Default classification for unknown errors
        return StructuredError(
            message=f"Unknown error during {operation_type}: {error_message}",
            category=ErrorCategory.RECOVERABLE,  # Default to recoverable for safety
            severity=ErrorSeverity.MEDIUM,
            context=context,
            original_exception=exception,
            recovery_suggestions=[
                "Retry the operation",
                "Check system logs for more details",
                "Contact support if issue persists",
            ],
        )


class WarningManager:
    """
    Manager for collecting and organizing warnings during operations.
    """

    def __init__(self):
        self.warnings: List[Warning] = []
        self._warning_counts: Dict[str, int] = {}

    def add_warning(
        self,
        message: str,
        severity: ErrorSeverity,
        context: ErrorContext,
        affected_items: List[str] = None,
        impact_description: str = None,
    ) -> None:
        """Add a warning to the collection."""
        warning = Warning(
            message=message,
            severity=severity,
            context=context,
            affected_items=affected_items or [],
            impact_description=impact_description,
        )

        self.warnings.append(warning)

        # Track warning frequency for analysis
        warning_key = f"{severity.value}:{message[:50]}"
        self._warning_counts[warning_key] = self._warning_counts.get(warning_key, 0) + 1

    def add_error_as_warning(
        self,
        error: StructuredError,
        affected_items: List[str] = None,
        impact_description: str = None,
    ) -> None:
        """Convert a structured error to a warning for partial failure handling."""
        self.add_warning(
            message=f"Partial failure: {error.message}",
            severity=error.severity,
            context=error.context,
            affected_items=affected_items,
            impact_description=impact_description,
        )

    def get_warnings(self) -> List[Warning]:
        """Get all collected warnings."""
        return self.warnings.copy()

    def get_warning_summary(self) -> Dict[str, Any]:
        """Get a summary of warnings by severity and frequency."""
        if not self.warnings:
            return {"total_warnings": 0, "by_severity": {}, "most_frequent": []}

        severity_counts = {}
        for warning in self.warnings:
            severity = warning.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # Get most frequent warning types
        most_frequent = sorted(
            self._warning_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]  # Top 5 most frequent

        return {
            "total_warnings": len(self.warnings),
            "by_severity": severity_counts,
            "most_frequent": [
                {"pattern": pattern, "count": count} for pattern, count in most_frequent
            ],
        }

    def has_critical_warnings(self) -> bool:
        """Check if there are any critical warnings."""
        return any(w.severity == ErrorSeverity.CRITICAL for w in self.warnings)

    def get_user_friendly_messages(self) -> List[str]:
        """Get user-friendly warning messages for API responses."""
        messages = []

        # Group warnings by severity and create concise messages
        high_severity_warnings = [
            w
            for w in self.warnings
            if w.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
        ]
        medium_severity_warnings = [
            w for w in self.warnings if w.severity == ErrorSeverity.MEDIUM
        ]

        if high_severity_warnings:
            affected_count = sum(len(w.affected_items) for w in high_severity_warnings)
            if affected_count > 0:
                messages.append(f"High priority issues affected {affected_count} items")

        if medium_severity_warnings:
            affected_count = sum(
                len(w.affected_items) for w in medium_severity_warnings
            )
            if affected_count > 0:
                messages.append(f"Minor issues affected {affected_count} items")

        # Add specific messages for unique warning types
        unique_messages = set()
        for warning in self.warnings:
            if warning.impact_description:
                unique_messages.add(warning.impact_description)
            elif len(warning.affected_items) == 1:
                unique_messages.add(
                    f"Issue with {warning.affected_items[0]}: {warning.message}"
                )

        messages.extend(list(unique_messages)[:3])  # Limit to 3 specific messages

        return messages

    def clear(self) -> None:
        """Clear all warnings."""
        self.warnings.clear()
        self._warning_counts.clear()


class ErrorLogger:
    """
    Enhanced logging system with structured error information and context.
    """

    def __init__(self, logger_name: str = "kleinanzeigen_api"):
        self.logger = logging.getLogger(logger_name)
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Setup logger with appropriate formatting and handlers."""
        if not self.logger.handlers:
            # Create console handler with structured formatting
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log_error(
        self, error: StructuredError, include_stack_trace: bool = True
    ) -> None:
        """Log a structured error with full context information."""
        log_data = {
            "error": error.to_dict(),
            "operation_context": error.context.to_dict(),
        }

        log_message = (
            f"[{error.category.value.upper()}] {error.message} "
            f"(Severity: {error.severity.value}, Retry: {error.context.retry_attempt})"
        )

        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"{log_message} | Context: {log_data}")
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(f"{log_message} | Context: {log_data}")
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"{log_message} | Context: {log_data}")
        else:
            self.logger.info(f"{log_message} | Context: {log_data}")

        # Log stack trace for debugging if available and requested
        if (
            include_stack_trace
            and error.stack_trace
            and error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
        ):
            self.logger.debug(
                f"Stack trace for {error.message}: {''.join(error.stack_trace)}"
            )

    def log_warning(self, warning: Warning) -> None:
        """Log a warning with context information."""
        log_message = (
            f"[WARNING] {warning.message} "
            f"(Severity: {warning.severity.value}, Affected: {len(warning.affected_items)} items)"
        )

        log_data = {"warning": warning.to_dict()}

        if warning.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.logger.warning(f"{log_message} | Context: {log_data}")
        else:
            self.logger.info(f"{log_message} | Context: {log_data}")

    def log_operation_summary(
        self,
        operation: str,
        total_items: int,
        successful_items: int,
        warnings: List[Warning],
        errors: List[StructuredError],
        duration: float,
    ) -> None:
        """Log a summary of an operation with success/failure statistics."""
        success_rate = (successful_items / total_items * 100) if total_items > 0 else 0
        failed_items = total_items - successful_items

        summary_message = (
            f"[OPERATION_SUMMARY] {operation} completed: "
            f"{successful_items}/{total_items} successful ({success_rate:.1f}%), "
            f"{failed_items} failed, {len(warnings)} warnings, "
            f"{len(errors)} errors in {duration:.2f}s"
        )

        if failed_items == 0 and len(errors) == 0:
            self.logger.info(summary_message)
        elif success_rate >= 80:
            self.logger.warning(summary_message)
        else:
            self.logger.error(summary_message)

        # Log error breakdown if there were significant failures
        if len(errors) > 0:
            error_categories = {}
            for error in errors:
                category = error.category.value
                error_categories[category] = error_categories.get(category, 0) + 1

            self.logger.info(f"Error breakdown for {operation}: {error_categories}")


@contextmanager
def error_handling_context(
    operation: str,
    page_number: int = None,
    url: str = None,
    listing_id: str = None,
    logger: ErrorLogger = None,
):
    """
    Context manager for comprehensive error handling with automatic logging.

    Usage:
        with error_handling_context("fetch_page", page_number=1, url="...") as ctx:
            # Perform operation
            result = await some_operation()
            ctx.add_success_metric(result)
    """

    class ErrorHandlingContext:
        def __init__(self, operation: str, context: ErrorContext, logger: ErrorLogger):
            self.operation = operation
            self.context = context
            self.logger = logger or ErrorLogger()
            self.warnings = WarningManager()
            self.errors: List[StructuredError] = []
            self.start_time = time.time()

        def add_warning(
            self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, **kwargs
        ):
            """Add a warning to the context."""
            self.warnings.add_warning(message, severity, self.context, **kwargs)

        def handle_exception(
            self, exception: Exception, operation_type: str = None
        ) -> StructuredError:
            """Handle an exception and convert it to a structured error."""
            error = ErrorClassifier.classify_exception(
                exception, self.context, operation_type or self.operation
            )
            self.errors.append(error)
            self.logger.log_error(error)
            return error

        def get_duration(self) -> float:
            """Get the duration of the operation."""
            return time.time() - self.start_time

        def has_errors(self) -> bool:
            """Check if any errors were recorded."""
            return len(self.errors) > 0

        def has_warnings(self) -> bool:
            """Check if any warnings were recorded."""
            return len(self.warnings.get_warnings()) > 0

    context = ErrorContext(
        operation=operation, page_number=page_number, url=url, listing_id=listing_id
    )

    error_context = ErrorHandlingContext(operation, context, logger)

    try:
        yield error_context
    except Exception as e:
        error_context.handle_exception(e)
        raise
    finally:
        # Log operation summary
        if logger:
            logger.log_operation_summary(
                operation=operation,
                total_items=1,  # Single operation
                successful_items=0 if error_context.has_errors() else 1,
                warnings=error_context.warnings.get_warnings(),
                errors=error_context.errors,
                duration=error_context.get_duration(),
            )
