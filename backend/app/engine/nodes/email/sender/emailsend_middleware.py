import datetime
import logging
from typing import Any, Dict, Optional
from app.engine.graph.graph_event import EventType, GraphEvent
from app.engine.interfaces.i_middleware import IMiddleware

logger = logging.getLogger(__name__)

class EmailLoggingMiddleware(IMiddleware):
    """
    Middleware for logging email sending operations.
    
    Provides detailed logging of email operations including recipient information,
    subject lines, and sending status while being careful not to log sensitive content.
    """
    
    async def before_process(self, event: GraphEvent, node_id: str) -> GraphEvent:
        """Log email sending attempt with sanitized information"""
        if event.data and isinstance(event.data, dict):
            log_data = self._create_safe_log_data(event.data)
            
            recipients_info = self._format_recipients_info(log_data)
            subject_info = f" - Subject: '{log_data.get('subject', 'No subject')}'"
            
            logger.info(f"Email sending started - Node {node_id}: {recipients_info}{subject_info}")
            
            # Log additional details at debug level
            if logger.isEnabledFor(logging.DEBUG):
                debug_info = {
                    "from": log_data.get("from", "Not specified"),
                    "cc_count": len(log_data.get("cc", [])) if isinstance(log_data.get("cc"), list) else (1 if log_data.get("cc") else 0),
                    "bcc_count": len(log_data.get("bcc", [])) if isinstance(log_data.get("bcc"), list) else (1 if log_data.get("bcc") else 0),
                    "has_attachments": "attachments" in log_data and bool(log_data["attachments"]),
                    "attachment_count": len(log_data.get("attachments", [])) if log_data.get("attachments") else 0,
                    "html_enabled": log_data.get("html", False),
                    "priority": log_data.get("priority", "normal")
                }
                logger.debug(f"Email details - Node {node_id}: {debug_info}")
        
        return event
    
    async def after_process(self, event: GraphEvent, result: Optional[GraphEvent], node_id: str) -> Optional[GraphEvent]:
        """Log email sending result"""
        if result:
            if result.type.name == "ERROR":
                error_msg = result.data.get("error", "Unknown error")
                logger.error(f"Email sending failed - Node {node_id}: {error_msg}")
            else:
                status = result.metadata.get("status", "unknown")
                message = result.data.get("message", "Email processed")
                logger.info(f"Email sending completed - Node {node_id}: {status} - {message}")
                
                # Log success details at debug level
                if logger.isEnabledFor(logging.DEBUG) and result.data:
                    logger.debug(f"Email result details - Node {node_id}: {result.data}")
        else:
            logger.warning(f"Email processing returned no result - Node {node_id}")
        
        return result
    
    def _create_safe_log_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a sanitized version of email data for logging.
        Removes or truncates sensitive/large content.
        """
        safe_data = {}
        
        # Safe fields to log as-is
        safe_fields = ["to", "from", "cc", "bcc", "subject", "html", "priority"]
        for field in safe_fields:
            if field in data:
                safe_data[field] = data[field]
        
        # Truncate body for logging
        if "body" in data:
            body = str(data["body"])
            if len(body) > 100:
                safe_data["body"] = body[:100] + "... (truncated)"
            else:
                safe_data["body"] = body
        
        # Summarize attachments without content
        if "attachments" in data and data["attachments"]:
            attachments = data["attachments"]
            if isinstance(attachments, list):
                safe_data["attachments"] = [
                    {
                        "filename": att.get("filename", "unknown") if isinstance(att, dict) else "unknown",
                        "size": len(str(att.get("content", ""))) if isinstance(att, dict) and "content" in att else 0
                    }
                    for att in attachments
                ]
            else:
                safe_data["attachments"] = "Invalid attachment format"
        
        return safe_data
    
    def _format_recipients_info(self, data: Dict[str, Any]) -> str:
        """Format recipient information for logging"""
        recipients = []
        
        # Count TO recipients
        to_recipients = data.get("to", [])
        if isinstance(to_recipients, str):
            to_count = 1
        elif isinstance(to_recipients, list):
            to_count = len(to_recipients)
        else:
            to_count = 0
        
        if to_count > 0:
            recipients.append(f"{to_count} recipient{'s' if to_count > 1 else ''}")
        
        # Count CC recipients
        cc_recipients = data.get("cc", [])
        if isinstance(cc_recipients, str):
            cc_count = 1
        elif isinstance(cc_recipients, list):
            cc_count = len(cc_recipients)
        else:
            cc_count = 0
        
        if cc_count > 0:
            recipients.append(f"{cc_count} CC")
        
        # Count BCC recipients
        bcc_recipients = data.get("bcc", [])
        if isinstance(bcc_recipients, str):
            bcc_count = 1
        elif isinstance(bcc_recipients, list):
            bcc_count = len(bcc_recipients)
        else:
            bcc_count = 0
        
        if bcc_count > 0:
            recipients.append(f"{bcc_count} BCC")
        
        total_count = to_count + cc_count + bcc_count
        
        if recipients:
            return f"To {total_count} total ({', '.join(recipients)})"
        else:
            return "No recipients specified"
        
class EmailValidationMiddleware(IMiddleware):
    """
    Optional middleware for additional email validation and preprocessing.
    
    Can be used to enforce organizational email policies, domain restrictions,
    or content filtering before sending emails.
    """
    
    def __init__(self, 
                 allowed_domains: Optional[list] = None,
                 blocked_domains: Optional[list] = None,
                 max_recipients: Optional[int] = None,
                 require_subject: bool = True):
        """
        Initialize email validation middleware.
        
        Args:
            allowed_domains: List of allowed email domains (whitelist)
            blocked_domains: List of blocked email domains (blacklist) 
            max_recipients: Maximum total number of recipients allowed
            require_subject: Whether subject line is required
        """
        self.allowed_domains = allowed_domains or []
        self.blocked_domains = blocked_domains or []
        self.max_recipients = max_recipients
        self.require_subject = require_subject
    
    async def before_process(self, event: GraphEvent, node_id: str) -> GraphEvent:
        """Validate email data before processing"""
        if event.data and isinstance(event.data, dict):
            validation_errors = []
            
            # Validate domains
            domain_errors = self._validate_email_domains(event.data)
            validation_errors.extend(domain_errors)
            
            # Validate recipient count
            if self.max_recipients:
                count_error = self._validate_recipient_count(event.data)
                if count_error:
                    validation_errors.append(count_error)
            
            # Validate required fields
            if self.require_subject and not event.data.get("subject", "").strip():
                validation_errors.append("Subject line is required")
            
            # If validation fails, modify event to indicate error
            if validation_errors:
                logger.error(f"Email validation failed - Node {node_id}: {'; '.join(validation_errors)}")
                # You could modify the event here or raise an exception
                # depending on your error handling strategy
                return GraphEvent(
                    type= EventType.ERROR,
                    source_id=event.source_id,
                    timestamp=datetime.datetime.now(),
                    data=validation_errors
                )
        
        return event
    
    async def after_process(self, event: GraphEvent, result: Optional[GraphEvent], node_id: str) -> Optional[GraphEvent]:
        """No post-processing needed for validation middleware"""
        return result
    
    def _validate_email_domains(self, data: Dict[str, Any]) -> list:
        """Validate email domains against allowed/blocked lists"""
        errors = []
        
        all_emails = []
        
        # Collect all email addresses
        for field in ["to", "from", "cc", "bcc"]:
            if field in data:
                field_emails = data[field]
                if isinstance(field_emails, str):
                    all_emails.append((field, field_emails))
                elif isinstance(field_emails, list):
                    for email in field_emails:
                        all_emails.append((field, email))
        
        # Check each email
        for field, email in all_emails:
            if isinstance(email, str) and "@" in email:
                domain = email.split("@")[1].lower()
                
                # Check against allowed domains (whitelist)
                if self.allowed_domains and domain not in self.allowed_domains:
                    errors.append(f"Domain '{domain}' not in allowed domains list ({field}: {email})")
                
                # Check against blocked domains (blacklist)
                if domain in self.blocked_domains:
                    errors.append(f"Domain '{domain}' is blocked ({field}: {email})")
        
        return errors
    
    def _validate_recipient_count(self, data: Dict[str, Any]) -> Optional[str]:
        """Validate total recipient count"""
        total_count = 0
        
        for field in ["to", "cc", "bcc"]:
            if field in data:
                field_data = data[field]
                if isinstance(field_data, str):
                    total_count += 1
                elif isinstance(field_data, list):
                    total_count += len(field_data)
        
        if total_count > self.max_recipients:
            return f"Too many recipients ({total_count}). Maximum allowed: {self.max_recipients}"
        
        return None