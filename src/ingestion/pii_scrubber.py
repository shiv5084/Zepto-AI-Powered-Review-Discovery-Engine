import re
import logging

# Configure logger
logger = logging.getLogger(__name__)


class PIIScrubber:
    """Handles local scrubbing of PII using deterministic regex patterns.

    Detects and redacts:
    - Email addresses
    - IP addresses
    - Phone numbers
    - Reddit user handles  (u/username)
    - Social media handles (@username)
    """

    def __init__(self):
        self.presidio_available = False
        # Email addresses
        self.email_regex = re.compile(
            r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b"
        )
        # IPv4 addresses
        self.ip_regex = re.compile(
            r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
        )
        # Phone numbers (various formats)
        self.phone_regex = re.compile(
            r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        )
        # Reddit handles: u/username or /u/username
        self.reddit_handle_regex = re.compile(
            r"/?\bu/[A-Za-z0-9_-]+\b"
        )
        # Social media @handles — evaluated after email masking so
        # the @ in already-masked [EMAIL] tokens is never re-matched.
        self.social_handle_regex = re.compile(
            r"(?<!\w)@[A-Za-z0-9_]+\b"
        )

        logger.info("PIIScrubber initialised (regex-only mode).")

    def scrub_regex(self, text: str) -> str:
        """Apply deterministic regex filters to redact common PII identifiers."""
        if not text:
            return ""

        # 1. Mask emails first (prevents @ in email from being caught by handle regex)
        text = self.email_regex.sub("[EMAIL]", text)
        # 2. Mask IP addresses
        text = self.ip_regex.sub("[IP_ADDRESS]", text)
        # 3. Mask phone numbers
        text = self.phone_regex.sub("[PHONE_NUMBER]", text)
        # 4. Mask Reddit handles
        text = self.reddit_handle_regex.sub("[USER_HANDLE]", text)
        # 5. Mask Twitter/social @handles
        text = self.social_handle_regex.sub("[USER_HANDLE]", text)

        return text

    def scrub(self, text: str) -> str:
        """Fully scrub a text block. Public entry point for all callers."""
        if not text:
            return ""
        return self.scrub_regex(text)
