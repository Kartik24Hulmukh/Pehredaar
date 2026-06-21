"""
Pehredaar — PII Redaction Module (DPDP Act 2023 Compliant)
============================================================
Redacts Personally Identifiable Information from text and images BEFORE any
model call, per the Digital Personal Data Protection Act 2023.

Redaction is performed entirely through deterministic regex matching — no AI /
model calls are made, ensuring PII never reaches a third-party endpoint.

Supported PII types:
  * Indian names (label-context patterns: "Patient:", "Name:", "Mr./Mrs.")
  * UHID / patient ID numbers
  * Policy numbers (alphanumeric)
  * Phone numbers (Indian format: +91, 0, or bare 10 digits)
  * Aadhaar numbers (12-digit or XXXX-XXXX-XXXX)
  * PAN numbers (5 letters + 4 digits + 1 letter)
  * Email addresses
  * Addresses (partial — street numbers, Indian PIN codes)

Design principles:
  1. NEVER log or store original PII values — only type + length + position.
  2. Replace PII with ``[REDACTED:TYPE]`` markers in text.
  3. Do NOT over-redact — drug names, medical terms, and hospital names are
     preserved.  Only human-identifying data is redacted.
  4. Graceful error handling — if OCR fails on an image, return the original.
"""

from __future__ import annotations

import os
import re
import tempfile
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Regex patterns for Indian PII formats
# ---------------------------------------------------------------------------

# Phone numbers: +91 followed by 10 digits, or 0 + 10-11 digits, or bare 10 digits
# Starts with 6-9 per TRAI numbering plan for mobile; landlines start with 0 + area code
_PHONE_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"\+91[6-9]\d{9}"),
    re.compile(r"\+91\d{10}"),
    re.compile(r"\b0\d{10}\b"),
    re.compile(r"\b[6-9]\d{9}\b"),
]

# Aadhaar: 12 consecutive digits, or XXXX-XXXX-XXXX format
# UIDAI spec says first digit is never 0 or 1, but for redaction robustness
# (OCR may produce any digits) we match any 12-digit number in 4-4-4 groups.
_AADHAAR_PATTERNS: List[re.Pattern[str]] = [
    # XXXX-XXXX-XXXX or XXXX XXXX XXXX format
    re.compile(r"\b\d{4}[\s-]\d{4}[\s-]\d{4}\b"),
    # 12 consecutive digits (must be word-bounded to avoid matching longer numbers)
    re.compile(r"\b\d{12}\b"),
]

# PAN: 5 letters + 4 digits + 1 letter (e.g. ABCDE1234F)
_PAN_PATTERN: re.Pattern[str] = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")

# Email addresses
_EMAIL_PATTERN: re.Pattern[str] = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)

# UHID / patient ID: typically labelled "UHID", "Patient ID", "Reg No", "MRN"
# Matches alphanumeric IDs of 4-20 chars following such labels
_UHID_PATTERN: re.Pattern[str] = re.compile(
    r"(?:UHID|Patient\s*ID|Reg\.?\s*No|MRN|Registration\s*No|Hospital\s*ID)"
    r"[\s.:]*([A-Z0-9]{4,20})",
    re.IGNORECASE,
)

# Policy number: labelled "Policy", "Policy No", "Policy Number"
# Matches alphanumeric IDs of 6-20 chars following such labels
_POLICY_PATTERN: re.Pattern[str] = re.compile(
    r"(?:Policy\s*(?:No\.?|Number)?|Pol\.?\s*No)"
    r"[\s.:]*([A-Z0-9]{6,20})",
    re.IGNORECASE,
)

# Indian PIN codes: 6 digits, first digit 1-8
_PINCODE_PATTERN: re.Pattern[str] = re.compile(r"\b[1-8]\d{5}\b")

# Street numbers: "H.No. 123", "House No 45", "No. 78", "Plot 12"
_STREET_NUMBER_PATTERN: re.Pattern[str] = re.compile(
    r"(?:H\.?\s*No\.?|House\s*No\.?|Plot\s*No\.?|Flat\s*No\.?|Door\s*No\.?)"
    r"[\s.:]*\d+[A-Z]?",
    re.IGNORECASE,
)

# Indian names: appear after labels like "Patient:", "Name:", "Mr.", "Mrs.", "S/o", "D/o"
# Matches 1-4 capitalized words following the label
_NAME_LABELS: str = (
    r"(?:Patient\s*Name|Patient|Name|Mr\.|Mrs\.|Ms\.|Smt\.|Shri|S/o|D/o|W/o|C/o)"
)
_NAME_PATTERN: re.Pattern[str] = re.compile(
    rf"{_NAME_LABELS}[\s.:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){{0,3}})"
)

# Common Indian name components for standalone detection (conservative)
# Only used when a name label is present to avoid over-redaction
_INDIAN_NAME_PREFIXES: Tuple[str, ...] = (
    "Mr", "Mrs", "Ms", "Smt", "Shri",
)

# Fields in bill JSON that contain PII and must be redacted
_PII_JSON_FIELDS: Tuple[str, ...] = (
    "patient_name", "uhid", "policy_no", "phone", "address",
    "patient_phone", "patient_address", "email", "patient_email",
    "name", "contact", "patient_id", "registration_no",
)


# ---------------------------------------------------------------------------
# PII Redactor
# ---------------------------------------------------------------------------

class PIIRedactor:
    """
    Deterministic PII redaction engine.

    All methods are static and perform pure regex-based redaction — no model
    calls, no network, no logging of original values.

    Usage::

        result = PIIRedactor.redact_text("Patient: Ramesh Kumar, Phone: +919876543210")
        # result = {
        #     "redacted_text": "Patient: [REDACTED:NAME], Phone: [REDACTED:PHONE]",
        #     "redactions": [
        #         {"type": "NAME", "original_length": 11, "position": 9},
        #         {"type": "PHONE", "original_length": 13, "position": 23},
        #     ],
        # }
    """

    # ------------------------------------------------------------------ #
    #  Text redaction                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def redact_text(text: str) -> Dict[str, Any]:
        """
        Redact PII from a text string.

        Replaces all detected PII with ``[REDACTED:TYPE]`` markers and returns
        a metadata dict listing each redaction's type, original character
        length, and start position in the original text.

        .. note::
            Original PII values are NEVER stored or returned — only their
            type, length, and position.

        Parameters
        ----------
        text
            Raw input text that may contain PII.

        Returns
        -------
        dict
            Keys:
                * ``redacted_text`` — the text with PII replaced by markers.
                * ``redactions`` — list of ``{type, original_length, position}``.
        """
        if not text or not text.strip():
            return {"redacted_text": text or "", "redactions": []}

        redactions: List[Dict[str, Any]] = []

        # Collect all matches with their positions, then apply from end to
        # start so earlier offsets remain valid.
        # Each entry: (start, end, pii_type, original_text)

        matches: List[Tuple[int, int, str, str]] = []

        # --- Phone numbers ---
        for pat in _PHONE_PATTERNS:
            for m in pat.finditer(text):
                matches.append((m.start(), m.end(), "PHONE", m.group()))

        # --- Aadhaar numbers ---
        for pat in _AADHAAR_PATTERNS:
            for m in pat.finditer(text):
                # Avoid matching bare 12-digit sequences that are part of
                # longer numbers (e.g. account numbers) — require word boundary
                val = m.group()
                digits_only = re.sub(r"\D", "", val)
                if len(digits_only) == 12:
                    matches.append((m.start(), m.end(), "AADHAAR", val))

        # --- PAN numbers ---
        for m in _PAN_PATTERN.finditer(text):
            matches.append((m.start(), m.end(), "PAN", m.group()))

        # --- Email addresses ---
        for m in _EMAIL_PATTERN.finditer(text):
            matches.append((m.start(), m.end(), "EMAIL", m.group()))

        # --- UHID / patient ID ---
        for m in _UHID_PATTERN.finditer(text):
            # Group 1 is the actual ID; redact only that portion
            id_start = m.start(1)
            id_end = m.end(1)
            matches.append((id_start, id_end, "UHID", m.group(1)))

        # --- Policy numbers ---
        for m in _POLICY_PATTERN.finditer(text):
            id_start = m.start(1)
            id_end = m.end(1)
            matches.append((id_start, id_end, "POLICY", m.group(1)))

        # --- PIN codes ---
        for m in _PINCODE_PATTERN.finditer(text):
            matches.append((m.start(), m.end(), "PINCODE", m.group()))

        # --- Street numbers ---
        for m in _STREET_NUMBER_PATTERN.finditer(text):
            matches.append((m.start(), m.end(), "ADDRESS", m.group()))

        # --- Names (label-context) ---
        for m in _NAME_PATTERN.finditer(text):
            name_start = m.start(1)
            name_end = m.end(1)
            name_val = m.group(1)
            # Guard: don't redact if the "name" is actually a common word
            # that happens to be capitalized (e.g. "Cash", "Total")
            _lower = name_val.lower()
            if _lower not in _NON_NAME_WORDS:
                matches.append((name_start, name_end, "NAME", name_val))

        # --- De-duplicate overlapping matches (keep longest at each position) ---
        matches = PIIRedactor._deduplicate_matches(matches)

        # --- Sort by start position descending (apply from end) ---
        matches.sort(key=lambda t: t[0], reverse=True)

        # --- Apply redactions ---
        redacted = text
        for start, end, pii_type, original in matches:
            marker = f"[REDACTED:{pii_type}]"
            redacted = redacted[:start] + marker + redacted[end:]
            redactions.append({
                "type": pii_type,
                "original_length": len(original),
                "position": start,
            })

        # Reverse redactions list to be in position order (ascending)
        redactions.reverse()

        return {
            "redacted_text": redacted,
            "redactions": redactions,
        }

    # ------------------------------------------------------------------ #
    #  Image redaction                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def redact_image(image_path: str) -> str:
        """
        Redact PII from an image by OCR-ing it, locating PII regions, and
        blacking them out with PIL/Pillow.

        The redacted image is saved to a temporary file and the path is
        returned.  If OCR fails or no PII is found, the original image is
        copied to a temp path and returned unchanged.

        Parameters
        ----------
        image_path
            Path to the input image file (PNG, JPEG, etc.).

        Returns
        -------
        str
            Path to the redacted (or original-copy) image in a temp directory.
        """
        try:
            from PIL import Image, ImageDraw
            import pytesseract
        except ImportError:
            # If dependencies are missing, return a copy of the original
            return PIIRedactor._copy_original(image_path)

        try:
            img = Image.open(image_path)
        except Exception:
            return PIIRedactor._copy_original(image_path)

        try:
            # OCR with bounding box data
            ocr_data = pytesseract.image_to_data(
                img, output_type=pytesseract.Output.DICT
            )
        except Exception:
            # OCR failed — return original copy
            return PIIRedactor._copy_original(image_path)

        # Reconstruct text lines and find PII regions
        # pytesseract returns word-level data; we need to group words into
        # lines and check each line for PII
        n_words = len(ocr_data["text"])
        if n_words == 0:
            return PIIRedactor._copy_original(image_path)

        # Group words by line number and block
        lines: Dict[int, List[Dict[str, Any]]] = {}
        for i in range(n_words):
            text_val = ocr_data["text"][i].strip()
            if not text_val:
                continue
            conf = int(ocr_data["conf"][i]) if str(ocr_data["conf"][i]).lstrip("-").isdigit() else -1
            if conf < 0:
                continue
            line_key = (
                ocr_data["block_num"][i],
                ocr_data["par_num"][i],
                ocr_data["line_num"][i],
            )
            if line_key not in lines:
                lines[line_key] = []
            lines[line_key].append({
                "text": text_val,
                "left": ocr_data["left"][i],
                "top": ocr_data["top"][i],
                "width": ocr_data["width"][i],
                "height": ocr_data["height"][i],
                "conf": conf,
            })

        # Check each line for PII and collect regions to black out
        regions_to_redact: List[Tuple[int, int, int, int]] = []  # (left, top, right, bottom)

        for line_key, words in lines.items():
            line_text = " ".join(w["text"] for w in words)
            if not line_text.strip():
                continue

            # Check if this line contains PII
            pii_found = PIIRedactor._detect_pii_in_line(line_text)

            if pii_found:
                # Compute bounding box for the entire line
                min_left = min(w["left"] for w in words)
                min_top = min(w["top"] for w in words)
                max_right = max(w["left"] + w["width"] for w in words)
                max_bottom = max(w["top"] + w["height"] for w in words)
                # Add small padding
                padding = 2
                regions_to_redact.append((
                    max(0, min_left - padding),
                    max(0, min_top - padding),
                    max_right + padding,
                    max_bottom + padding,
                ))

        if not regions_to_redact:
            # No PII found — return copy of original
            return PIIRedactor._copy_original(image_path)

        # Black out PII regions
        draw = ImageDraw.Draw(img)
        for left, top, right, bottom in regions_to_redact:
            draw.rectangle([left, top, right, bottom], fill="black")

        # Save to temp file
        fd, temp_path = tempfile.mkstemp(
            suffix="_redacted.png", prefix="pehredaar_"
        )
        os.close(fd)
        img.save(temp_path)

        return temp_path

    # ------------------------------------------------------------------ #
    #  Bill JSON redaction                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def redact_bill_json(bill_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact PII fields from a structured bill JSON dict.

        Removes or redacts patient-identifying fields (patient_name, uhid,
        policy_no, phone, address, email) while preserving all medical and
        financial data (line items, amounts, dates, hospital name).

        Parameters
        ----------
        bill_json
            Parsed bill JSON dict following the canonical schema.

        Returns
        -------
        dict
            A new dict with PII fields redacted.  The original dict is not
            modified.
        """
        if not bill_json:
            return {}

        # Deep copy to avoid mutating the original
        import copy
        redacted = copy.deepcopy(bill_json)

        # --- Redact top-level PII fields ---
        patient_info = redacted.get("patient_info", {})
        if isinstance(patient_info, dict):
            for field in list(patient_info.keys()):
                if PIIRedactor._is_pii_field(field):
                    patient_info[field] = "[REDACTED]"

        # Also check top-level fields that might contain PII directly
        for field in list(redacted.keys()):
            if PIIRedactor._is_pii_field(field) and field not in ("patient_info",):
                if isinstance(redacted[field], str):
                    redacted[field] = "[REDACTED]"
                elif isinstance(redacted[field], dict):
                    for sub_field in list(redacted[field].keys()):
                        if PIIRedactor._is_pii_field(sub_field):
                            redacted[field][sub_field] = "[REDACTED]"

        # --- Redact PII within line item raw_text ---
        for item in redacted.get("line_items", []):
            if isinstance(item, dict) and "raw_text" in item:
                raw = item.get("raw_text", "")
                if isinstance(raw, str) and raw:
                    result = PIIRedactor.redact_text(raw)
                    item["raw_text"] = result["redacted_text"]

        return redacted

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _deduplicate_matches(
        matches: List[Tuple[int, int, str, str]]
    ) -> List[Tuple[int, int, str, str]]:
        """
        Remove overlapping matches, keeping the longest span at each position.
        """
        if not matches:
            return []

        # Sort by start position, then by length descending
        sorted_matches = sorted(matches, key=lambda t: (t[0], -(t[1] - t[0])))

        result: List[Tuple[int, int, str, str]] = []
        last_end = -1

        for start, end, pii_type, original in sorted_matches:
            if start >= last_end:
                result.append((start, end, pii_type, original))
                last_end = end
            # If overlapping, the earlier (longer) match wins

        return result

    @staticmethod
    def _detect_pii_in_line(line_text: str) -> bool:
        """
        Check if a line of OCR text contains any PII patterns.
        Returns True if PII is detected, False otherwise.
        """
        # Phone
        for pat in _PHONE_PATTERNS:
            if pat.search(line_text):
                return True

        # Aadhaar
        for pat in _AADHAAR_PATTERNS:
            m = pat.search(line_text)
            if m:
                digits = re.sub(r"\D", "", m.group())
                if len(digits) == 12:
                    return True

        # PAN
        if _PAN_PATTERN.search(line_text):
            return True

        # Email
        if _EMAIL_PATTERN.search(line_text):
            return True

        # UHID / patient ID labels
        if _UHID_PATTERN.search(line_text):
            return True

        # Policy number labels
        if _POLICY_PATTERN.search(line_text):
            return True

        # Name labels (conservative — only with explicit labels)
        if _NAME_PATTERN.search(line_text):
            return True

        # PIN code
        if _PINCODE_PATTERN.search(line_text):
            return True

        return False

    @staticmethod
    def _is_pii_field(field_name: str) -> bool:
        """Check if a JSON field name corresponds to PII."""
        lower = field_name.lower().strip()
        return lower in {f.lower() for f in _PII_JSON_FIELDS}

    @staticmethod
    def _copy_original(image_path: str) -> str:
        """Copy the original image to a temp path and return it."""
        try:
            from PIL import Image
            img = Image.open(image_path)
            fd, temp_path = tempfile.mkstemp(
                suffix="_original_copy.png", prefix="pehredaar_"
            )
            os.close(fd)
            img.save(temp_path)
            return temp_path
        except Exception:
            # Last resort: return the original path itself
            return image_path


# Words that are capitalized but should NOT be treated as names
_NON_NAME_WORDS: frozenset[str] = frozenset({
    "cash", "total", "subtotal", "grand", "bill", "invoice", "receipt",
    "date", "amount", "rupees", "rs", "dr", "cr", "debit", "credit",
    "hospital", "clinic", "nursing", "home", "centre", "center",
    "pharmacy", "laboratory", "lab", "diagnostics", "ward", "room",
    "surgery", "consultation", "medicine", "implant", "blood",
    "discharge", "admission", "patient", "details", "summary",
    "department", "emergency", "icu", "ot", "operation",
})


# ---------------------------------------------------------------------------
# Module-level convenience functions (match the spec's function signatures)
# ---------------------------------------------------------------------------

def redact_text(text: str) -> Dict[str, Any]:
    """
    Redact PII from a text string.

    Convenience wrapper around ``PIIRedactor.redact_text``.

    Parameters
    ----------
    text
        Raw input text that may contain PII.

    Returns
    -------
    dict
        ``{redacted_text, redactions: [{type, original_length, position}]}``
    """
    return PIIRedactor.redact_text(text)


def redact_image(image_path: str) -> str:
    """
    Redact PII from an image.

    Convenience wrapper around ``PIIRedactor.redact_image``.

    Parameters
    ----------
    image_path
        Path to the input image file.

    Returns
    -------
    str
        Path to the redacted image in a temp directory.
    """
    return PIIRedactor.redact_image(image_path)


def redact_bill_json(bill_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Redact PII fields from a structured bill JSON dict.

    Convenience wrapper around ``PIIRedactor.redact_bill_json``.

    Parameters
    ----------
    bill_json
        Parsed bill JSON dict.

    Returns
    -------
    dict
        Bill JSON with PII fields redacted.
    """
    return PIIRedactor.redact_bill_json(bill_json)