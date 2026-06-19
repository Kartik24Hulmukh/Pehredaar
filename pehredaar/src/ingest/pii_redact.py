import re

def redact_pii(text: str) -> str:
    """Scrub Aadhaar, PAN, and Phone numbers from text."""
    if not text:
        return text

    # Redact Aadhaar (12 digits, optional spaces)
    aadhaar_pattern = r'\b\d{4}\s?\d{4}\s?\d{4}\b'
    text = re.sub(aadhaar_pattern, '[REDACTED_AADHAAR]', text)

    # Redact PAN (5 letters, 4 digits, 1 letter)
    pan_pattern = r'\b[A-Z]{5}\d{4}[A-Z]{1}\b'
    text = re.sub(pan_pattern, '[REDACTED_PAN]', text)

    # Redact Phone numbers (10 digits)
    phone_pattern = r'\b[6-9]\d{9}\b'
    text = re.sub(phone_pattern, '[REDACTED_PHONE]', text)

    return text
