from email.mime.text import MIMEText
import logging
import smtplib
from typing import Any, Dict
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email import encoders

from dna_core.engine.graph.graph_event import EventType, GraphEvent
from dna_core.engine.interfaces.i_processor import IProcessor

logger = logging.getLogger(__name__)

class MailSenderProcessor(IProcessor):
    def __init__(self, config: Dict[str, Any]):
        self.username = config["credential"]["username"]
        self.password = config["credential"]["password"]
        self.server_name = config["credential"]["server_name"]
        self.server_port = config["credential"]["server_port"] or 25
        self.use_ssl = config["credential"]["use_ssl"] or False
        self.use_tls = config["credential"]["use_tls"] or False
        
        self.default_from = config.get("default_from", self.username or "noreply@localhost")
        
        self.config_email_settings = config.get("email_settings", {})

        self.connected = False
        
    def create_error_event(self, error_message: str, original_event: GraphEvent, node_id: str) -> GraphEvent:
        return GraphEvent(
            type=EventType.ERROR,
            data={
                "error": error_message,
                "original_request": original_event.data
            },
            source_id=node_id,
            metadata={
                "status": "error",
                **original_event.metadata
            }
        )
        
    async def process(self, event: GraphEvent, context: Dict[str, Any]):
        merged_data = self._merge_email_data(event.data)
        print(merged_data)
        if not self._validate_request_data(merged_data):
            error_event = self.create_error_event("Invalid request data", event, context["node_id"])
            return error_event
        
        try:
            if not self.connected:
                await self._connect()
            
            msg = self._build_email_message(merged_data)
            
            await self._send_email(msg, merged_data)
            
            return self._create_success_event(event, context["node_id"])
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return self.create_error_event(f"Email sending failed: {str(e)}", event, context["node_id"])
        
    def can_handle(self, event: GraphEvent):
        return True
        
    def _generate_message_id(self) -> str:
        """Generate a unique Message-ID header"""
        import time
        import random
        import socket
        
        timestamp = str(int(time.time()))
        random_part = str(random.randint(100000, 999999))
        hostname = socket.getfqdn() or "localhost"
        
        return f"<{timestamp}.{random_part}@{hostname}>"
    
    def _merge_email_data(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge config email settings with event data.
        Event data takes priority over config settings.
        """
        merged_data = {}
        
        merged_data.update(self.config_email_settings)
        merged_data.update(event_data)
        
        if 'from' not in merged_data:
            merged_data['from'] = self.username or "noreply@localhost"
            
        # Handle content -> body mapping if needed
        if 'content' in merged_data and 'body' not in merged_data:
            if isinstance(merged_data['content'], dict):
                # Convert dict content to formatted string
                merged_data['body'] = self._format_dict_content(merged_data['content'])
            else:
                merged_data['body'] = str(merged_data['content'])
        
        logger.debug(f"Merged email data: {merged_data}")
        return merged_data
        
    def _format_dict_content(self, content: Dict[str, Any]) -> str:
        """Format dictionary content into readable text"""
        lines = []
        for key, value in content.items():
            if isinstance(value, dict):
                lines.append(f"{key.title()}:")
                for sub_key, sub_value in value.items():
                    lines.append(f"  {sub_key.title()}: {sub_value}")
            else:
                lines.append(f"{key.title()}: {value}")
        return "\n".join(lines)
    
    def _build_email_message(self, data: Dict[str, Any]) -> MIMEMultipart:
        """Build email message from event data"""
        from email.utils import formatdate
        
        msg = MIMEMultipart('alternative')
        
        msg['From'] = data.get('from', self.default_from)
        msg['To'] = self._format_recipients(data['to'])
        msg['Subject'] = data['subject']
        msg['Date'] = formatdate(localtime=True)  
        msg['Message-ID'] = self._generate_message_id()  
        
        if 'cc' in data:
            msg['Cc'] = self._format_recipients(data['cc'])
        if 'bcc' in data:
            msg['Bcc'] = self._format_recipients(data['bcc'])
            
        # Fixed: Use proper logging method
        logger.debug(f"Building email message: {data}")
        
        # Ensure we have a body
        body = data.get('body', '')
        if not body:
            body = "No content provided"
            
        if data.get('html'):
            msg.attach(MIMEText(body, 'plain'))
            if 'html_body' in data:
                msg.attach(MIMEText(data['html_body'], 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))
        
        if 'attachments' in data:
            self._add_attachments(msg, data['attachments'])
        
        return msg
    
    def _format_recipients(self, recipients) -> str:
        """Format recipients for email headers"""
        if isinstance(recipients, str):
            return recipients
        elif isinstance(recipients, list):
            return ', '.join(recipients)
        return str(recipients)
    
    def _add_attachments(self, msg: MIMEMultipart, attachments: list):
        """Add attachments to email message"""
        for attachment in attachments:
            if isinstance(attachment, dict) and 'filename' in attachment and 'content' in attachment:
                part = MIMEBase('application', "octet-stream")
                part.set_payload(attachment['content'])
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f"attachment; filename={attachment['filename']}")
                msg.attach(part)
    
    async def _connect(self):
        """Connect to SMTP server with improved authentication handling"""
        try:
            if self.use_ssl:
                self.smtp_server = smtplib.SMTP_SSL(self.server_name, self.server_port)
                logger.info(f"Connected via SSL to {self.server_name}:{self.server_port}")
            else:
                self.smtp_server = smtplib.SMTP(self.server_name, self.server_port)
                logger.info(f"Connected to {self.server_name}:{self.server_port}")
                
                if self.use_tls:
                    try:
                        self.smtp_server.starttls()
                        logger.info("TLS enabled successfully")
                    except smtplib.SMTPNotSupportedError:
                        logger.warning("STARTTLS not supported by server, continuing without TLS")
                    except Exception as e:
                        logger.warning(f"TLS failed: {str(e)}, continuing without TLS")
            
            # EHLO
            self.smtp_server.ehlo()
            
            # Only attempt login if we have credentials AND the server supports AUTH
            if self.username and self.password:
                try:
                    self.smtp_server.login(self.username, self.password)
                    logger.info("Authentication successful")
                except smtplib.SMTPNotSupportedError:
                    logger.warning("SMTP AUTH not supported by server, continuing without authentication")
                except smtplib.SMTPAuthenticationError as e:
                    logger.warning(f"Authentication failed: {str(e)}, continuing without authentication")
            else:
                logger.info("No credentials provided, skipping authentication")
            
            self.connected = True
            
        except Exception as e:
            logger.error(f"Failed to connect to SMTP server: {str(e)}")
            if hasattr(self, 'smtp_server') and self.smtp_server:
                try:
                    self.smtp_server.quit()
                except:
                    pass
            self.smtp_server = None
            self.connected = False
            raise

    async def _send_email(self, msg: MIMEMultipart, data: Dict[str, Any]):
        """Send the email message"""
        try:
            # Get all recipients
            recipients = []
            
            # Add 'to' recipients
            to_recipients = data['to']
            if isinstance(to_recipients, str):
                recipients.append(to_recipients)
            elif isinstance(to_recipients, list):
                recipients.extend(to_recipients)
            
            # Add 'cc' recipients
            if 'cc' in data:
                cc_recipients = data['cc']
                if isinstance(cc_recipients, str):
                    recipients.append(cc_recipients)
                elif isinstance(cc_recipients, list):
                    recipients.extend(cc_recipients)
            
            # Add 'bcc' recipients
            if 'bcc' in data:
                bcc_recipients = data['bcc']
                if isinstance(bcc_recipients, str):
                    recipients.append(bcc_recipients)
                elif isinstance(bcc_recipients, list):
                    recipients.extend(bcc_recipients)
            
            # Send the email
            self.smtp_server.send_message(msg, to_addrs=recipients)
            logger.info(f"Email sent successfully to {recipients}")
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            raise

    def _validate_request_data(self, data: Any) -> bool:
        if not isinstance(data, dict):
            logger.error("Request data must be a dictionary")
            return False
        
        required_fields = ["to", "subject"]
        
        for field in required_fields:
            if field not in data:
                logger.error(f"Missing required field: {field}")
                return False
            
            if not data[field] or (isinstance(data[field], str) and not data[field].strip()):
                logger.error(f"Field '{field}' cannot be empty")
                return False

        return True
        
    def _create_success_event(self, original_event: GraphEvent, node_id: str) -> GraphEvent:
        """Create success event"""
        return GraphEvent(
            type=EventType.COMPUTATION_RESULT,
            data={
                "status": "sent",
                "message": "Email sent successfully"
            },
            source_id=node_id,
            metadata={
                "status": "success",
                **original_event.metadata
            }
        )