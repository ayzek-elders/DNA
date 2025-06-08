import threading
import secrets
import time
from typing import Dict, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CredentialType(Enum):
    """Enum for supported credential types"""
    PASSWORD = "password"
    API_KEY = "api_key"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    SSH_KEY = "ssh_key"

@dataclass
class CredentialEntry:
    """Data class for credential entries"""
    credential_data: bytes
    salt: bytes
    created_at: float
    last_accessed: float
    access_count: int = 0
    metadata: Optional[Dict] = None

class InMemoryDatabase:
    """
    Secure in-memory database for storing encrypted credentials.
    Thread-safe with automatic cleanup and access tracking.
    """
    
    def __init__(self, max_credentials: int = 1000, cleanup_interval: int = 3600):
        """
        Initialize the database.
        
        Args:
            max_credentials: Maximum number of credentials to store
            cleanup_interval: Interval in seconds for cleanup operations
        """
        self._credentials: Dict[str, CredentialEntry] = {}
        self._lock = threading.RLock()
        self._max_credentials = max_credentials
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()
        
        # Track active credential types
        self._active_types: Set[CredentialType] = set()
        
        logger.info(f"InMemoryDatabase initialized with max_credentials={max_credentials}")

    def add_credential(self, 
                      credential_type: CredentialType, 
                      credential_to_store: bytes, 
                      salt: bytes,
                      metadata: Optional[Dict] = None) -> bool:
        """
        Add a new credential to the database.
        
        Args:
            credential_type: Type of credential (enum)
            credential_to_store: Encrypted credential data
            salt: Salt used for encryption
            metadata: Optional metadata dictionary
            
        Returns:
            bool: True if credential was added successfully
            
        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If database is full
        """
        self._validate_inputs(credential_type, credential_to_store, salt)
        
        with self._lock:
            # Check capacity
            if len(self._credentials) >= self._max_credentials:
                if len(self._credentials) >= self._max_credentials:
                    raise RuntimeError(f"Database at capacity ({self._max_credentials})")
            
            credential_key = credential_type.value
            current_time = time.time()
            
            # Create credential entry
            entry = CredentialEntry(
                credential_data=credential_to_store,
                salt=salt,
                created_at=current_time,
                last_accessed=current_time,
                metadata=metadata or {}
            )
            
            # Store credential
            self._credentials[credential_key] = entry
            self._active_types.add(credential_type)
            
            logger.info(f"Credential added: type={credential_type.value}")
            return True

    def get_credential(self, credential_type: CredentialType) -> Optional[Tuple[bytes, bytes]]:
        """
        Retrieve a credential from the database.
        
        Args:
            credential_type: Type of credential to retrieve
            
        Returns:
            Tuple of (credential_data, salt) or None if not found
        """
        if not isinstance(credential_type, CredentialType):
            raise ValueError("credential_type must be a CredentialType enum")
            
        with self._lock:
            entry = self._credentials.get(credential_type.value)
            if entry:
                entry.last_accessed = time.time()
                entry.access_count += 1
                
                logger.debug(f"Credential accessed: type={credential_type.value}")
                return (entry.credential_data, entry.salt)
            
            logger.warning(f"Credential not found: type={credential_type.value}")
            return None

    def exists(self, credential_type: CredentialType) -> bool:
        """Check if a credential exists in the database."""
        if not isinstance(credential_type, CredentialType):
            raise ValueError("credential_type must be a CredentialType enum")
            
        with self._lock:
            return credential_type.value in self._credentials

    def clear_all(self) -> None:
        """Securely clear all credentials from the database."""
        with self._lock:
            for entry in self._credentials.values():
                self._secure_clear(entry.credential_data)
                self._secure_clear(entry.salt)
            
            self._credentials.clear()
            self._active_types.clear()
            
            logger.info("All credentials cleared from database")

    def _validate_inputs(self, credential_type: CredentialType, 
                        credential_data: bytes, salt: bytes) -> None:
        """Validate input parameters."""
        if not isinstance(credential_type, CredentialType):
            raise ValueError("credential_type must be a CredentialType enum")
        
        if not isinstance(credential_data, bytes):
            raise ValueError("credential_data must be bytes")
        
        if not isinstance(salt, bytes):
            raise ValueError("salt must be bytes")
        
        if len(credential_data) == 0:
            raise ValueError("credential_data cannot be empty")
        
        if len(salt) < 32:  # Minimum salt length
            raise ValueError("salt must be at least 16 bytes")

    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            self.clear_all()
        except Exception:
            pass  