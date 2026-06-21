"""
Pehredaar — Bill Ingestion Module
==================================
Converts hospital bill images/PDFs to structured JSON following the canonical
bill schema.  Uses deterministic text extraction (pdfplumber for PDFs,
pytesseract for images) and regex-based parsing — no model calls for the
extraction itself.

Canonical bill JSON schema::

    {
      "hospital_name": str,
      "bill_number": str,
      "bill_date": str,
      "patient_info": {redacted},
      "room_rent_total": float,
      "room_rent_per_day": float,
      "days": int,
      "line_items": [
        {"name": str, "qty": int, "unit_price": float, "amount": float,
         "category": str, "raw_text": str, "confidence": float}
      ],
      "total_amount": float,
      "extraction_confidence": float
    }

Categorization follows IRDAI proportionate-deduction rules:
  * ``variable`` — surgery, surgeon, nursing, OT, consultation, doctor visit,
    anaesthesia, ICU care (subject to proportionate deduction; ICU is exempt
    per IRDAI/HLT/REG/CIR/151/06/2020 but still categorised as variable)
  * ``fixed`` — medicines, pharmacy, implants, medical devices, diagnostics,
    laboratory, pathology, consumables, blood (NOT subject to deduction)
  * ``room`` — room rent, ward charges, ICU room, deluxe room
  * ``other`` — anything that doesn't match the above

PII is redacted from patient_info before the JSON is returned.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Import PII redaction — with exec()-harness fallback
# ---------------------------------------------------------------------------
try:
    from src.core.pii_redaction import redact_text, redact_bill_json
except ImportError:  # pragma: no cover — exercised by exec-based test harness
    # When loaded via exec() the names may already be in the global scope
    # because pii_redaction.py was exec'd immediately before this file.
    if "redact_text" not in globals() or "redact_bill_json" not in globals():
        # Define minimal no-op fallbacks so the module doesn't crash
        # if PII redaction is unavailable — patient_info will be marked
        # [REDACTED] generically.
        def redact_text(text: str) -> Dict[str, Any]:  # type: ignore[no-redef]
            return {"redacted_text": text, "redactions": []}

        def redact_bill_json(bill_json: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[no-redef]
            return bill_json


# ---------------------------------------------------------------------------
# Categorization keyword sets
# ---------------------------------------------------------------------------

# VARIABLE charges — subject to proportionate deduction
_VARIABLE_KEYWORDS: Tuple[str, ...] = (
    "surgery", "surgeon", "surgical",
    "nursing", "nurse",
    "ot ", "o.t.", "operation theatre", "operation theater", "operation-theatre",
    "operation room", "operating",
    "consultation", "consult", "consultant",
    "doctor visit", "doctor's visit", "doctor fee", "doctor's fee",
    "doctors visit", "doctors fee", "visiting",
    "anaesthesia", "anesthesia", "anesthetic", "anaesthetic",
    "icu care", "icu charges", "icu monitoring", "intensive care",
    "procedure", "catheterization", "cath lab",
    "physiotherapy", "physio",
    "medical officer", "attending",
)

# FIXED charges — NOT subject to proportionate deduction
_FIXED_KEYWORDS: Tuple[str, ...] = (
    "medicine", "medicines", "pharmacy", "pharmacist", "drug", "drugs",
    "tablet", "tablets", "capsule", "capsules", "injection", "injections",
    "syrup", "iv fluid", "ivf",
    "implant", "implants",
    "medical device", "medical devices", "device",
    "diagnostic", "diagnostics", "investigation", "investigations",
    "laboratory", "lab ", "lab.", "pathology", "path lab",
    "blood", "blood bank",
    "consumable", "consumables", "disposable", "disposables",
    "x-ray", "xray", "x ray", "ct scan", "mri", "ultrasound", "sonography",
    "ecg", "eeg", "emg", "echo", "endoscopy", "colonoscopy",
    "biopsy", "culture", "urine test", "blood test",
)

# ROOM charges
_ROOM_KEYWORDS: Tuple[str, ...] = (
    "room rent", "room charge", "room charges",
    "ward charges", "ward charge",
    "icu room", "icu rent",
    "deluxe room", "deluxe",
    "private room", "single room", "twin sharing",
    "general ward", "semi private", "semi-private",
    "room", "ward",
)

# Hospital name labels
_HOSPITAL_LABELS: Tuple[str, ...] = (
    "hospital", "clinic", "medical centre", "medical center",
    "nursing home", "healthcare", "care hospital",
)

# Bill number labels
_BILL_NO_LABELS: Tuple[str, ...] = (
    "bill no", "bill number", "invoice no", "invoice number",
    "bill #", "invoice #", "receipt no", "receipt number",
    "billno", "invoiceno",
)

# Date patterns (Indian format: DD/MM/YYYY or DD-MM-YYYY)
_DATE_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b"),
    re.compile(r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{2,4})\b", re.IGNORECASE),
]

# Patient info labels
_PATIENT_LABELS: Tuple[str, ...] = (
    "patient name", "patient", "name", "mr.", "mrs.", "ms.",
    "smt.", "shri", "s/o", "d/o", "w/o",
)

# UHID / patient ID labels
_UHID_LABELS: Tuple[str, ...] = (
    "uhid", "patient id", "reg no", "registration no", "mrn", "hospital id",
)

# Policy number labels
_POLICY_LABELS: Tuple[str, ...] = (
    "policy no", "policy number", "policy", "pol no",
)

# Phone patterns (Indian format)
_PHONE_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"\+91[6-9]\d{9}"),
    re.compile(r"\+91\d{10}"),
    re.compile(r"\b0\d{10}\b"),
    re.compile(r"\b[6-9]\d{9}\b"),
]

# Room rent extraction patterns
_ROOM_RENT_PATTERNS: List[re.Pattern[str]] = [
    re.compile(
        r"room\s*rent.*?(\d+(?:[.,]\d+)*)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:ward|room)\s*charges.*?(\d+(?:[.,]\d+)*)",
        re.IGNORECASE,
    ),
]

# Per-day room rent pattern: "Room Rent @ 5000/day" or "5000 per day"
_ROOM_PER_DAY_PATTERN: re.Pattern[str] = re.compile(
    r"(?:room|ward).*?(\d+(?:[.,]\d+)*)\s*(?:/|per)\s*day",
    re.IGNORECASE,
)

# Days pattern: "3 days", "No. of days: 3", "Days: 4"
_DAYS_PATTERN: re.Pattern[str] = re.compile(
    r"(?:no\.?\s*of\s*days|days|no\.?\s*of\s*days\s*admitted)\s*[:\-]?\s*(\d+)",
    re.IGNORECASE,
)

# Total amount patterns
_TOTAL_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"grand\s*total.*?(\d+(?:[.,]\d+)*)", re.IGNORECASE),
    re.compile(r"total\s*amount.*?(\d+(?:[.,]\d+)*)", re.IGNORECASE),
    re.compile(r"total.*?(\d+(?:[.,]\d+)*)", re.IGNORECASE),
    re.compile(r"net\s*amount.*?(\d+(?:[.,]\d+)*)", re.IGNORECASE),
    re.compile(r"amount\s*payable.*?(\d+(?:[.,]\d+)*)", re.IGNORECASE),
]

# Line item pattern: name followed by optional qty, unit price, and amount
# Indian bills often format as: "Item Name      2    500    1000"
# or "Item Name              1000"
# or "Item Name    Qty: 2    500    1000"
_LINE_ITEM_PATTERN: re.Pattern[str] = re.compile(
    r"^(.+?)\s{2,}(\d+)\s+([\d,.]+)\s+([\d,.]+)\s*$"
)
_LINE_ITEM_PATTERN_3COL: re.Pattern[str] = re.compile(
    r"^(.+?)\s{2,}(\d+)\s+([\d,.]+)\s*$"
)
_LINE_ITEM_PATTERN_2COL: re.Pattern[str] = re.compile(
    r"^(.+?)\s{2,}([\d,.]+)\s*$"
)

# Numeric value extraction
_AMOUNT_PATTERN: re.Pattern[str] = re.compile(r"(\d+(?:[.,]\d+)*)")


# ---------------------------------------------------------------------------
# Bill Ingestion
# ---------------------------------------------------------------------------

class BillIngestion:
    """
    Hospital bill ingestion engine.

    Converts bill images/PDFs to structured JSON using deterministic text
    extraction and regex parsing.  No model calls are made for extraction.

    Usage::

        bill = BillIngestion.ingest_bill("/path/to/bill.pdf")
        # bill = {hospital_name, bill_number, ..., line_items: [...], ...}
    """

    # ------------------------------------------------------------------ #
    #  Main entry point                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def ingest_bill(file_path: str, file_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Main entry point: convert a bill image/PDF to structured JSON.

        Detects file type automatically if ``file_type`` is not provided,
        extracts text (pdfplumber for PDFs, pytesseract for images), parses
        it into the canonical bill schema, and redacts PII from patient_info.

        Parameters
        ----------
        file_path
            Path to the bill file (PDF, PNG, JPEG, etc.).
        file_type
            Optional file type hint: ``"pdf"``, ``"image"``, or ``None``
            for auto-detection.

        Returns
        -------
        dict
            Canonical bill JSON with PII redacted.
        """
        if not file_path or not os.path.exists(file_path):
            return BillIngestion._empty_bill(
                f"File not found: {file_path}"
            )

        # --- Detect file type ---
        if file_type is None:
            file_type = BillIngestion._detect_file_type(file_path)

        # --- Extract text ---
        try:
            if file_type == "pdf":
                text = BillIngestion._extract_pdf_text(file_path)
            else:
                text = BillIngestion._extract_image_text(file_path)
        except Exception as e:
            return BillIngestion._empty_bill(
                f"Text extraction failed: {e}"
            )

        if not text or not text.strip():
            return BillIngestion._empty_bill(
                "No text could be extracted from the file."
            )

        # --- Parse text into structured JSON ---
        bill = BillIngestion.parse_bill_text(text)

        # --- Redact PII ---
        bill = redact_bill_json(bill)

        return bill

    # ------------------------------------------------------------------ #
    #  Text parsing                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def parse_bill_text(text: str) -> Dict[str, Any]:
        """
        Parse raw bill text into structured JSON following the canonical schema.

        Extracts hospital name, bill number, date, patient info (redacted),
        line items with categorization, room rent details, and totals.

        Parameters
        ----------
        text
            Raw text extracted from the bill (via OCR or pdfplumber).

        Returns
        -------
        dict
            Canonical bill JSON dict.
        """
        if not text or not text.strip():
            return BillIngestion._empty_bill("Empty text input.")

        lines = text.split("\n")
        lines = [l.rstrip() for l in lines if l.strip()]

        # --- Extract metadata ---
        hospital_name = BillIngestion._extract_hospital_name(lines)
        bill_number = BillIngestion._extract_bill_number(lines)
        bill_date = BillIngestion._extract_date(text)

        # --- Extract patient info (redacted) ---
        patient_info = BillIngestion._extract_patient_info(lines, text)
        # Redact PII from patient_info before returning
        patient_info = BillIngestion._redact_patient_info(patient_info)

        # --- Extract room rent ---
        room_rent_total, room_rent_per_day, days = BillIngestion._extract_room_rent(lines, text)

        # --- Extract line items ---
        line_items = BillIngestion._extract_line_items(lines)

        # --- Extract total amount ---
        total_amount = BillIngestion._extract_total(lines, text)

        # If total not found, sum line items
        if total_amount == 0.0 and line_items:
            total_amount = sum(item.get("amount", 0.0) for item in line_items)

        # --- Compute extraction confidence ---
        confidence = BillIngestion._compute_confidence(
            hospital_name, bill_number, bill_date, line_items, total_amount
        )

        return {
            "hospital_name": hospital_name,
            "bill_number": bill_number,
            "bill_date": bill_date,
            "patient_info": patient_info,
            "room_rent_total": room_rent_total,
            "room_rent_per_day": room_rent_per_day,
            "days": days,
            "line_items": line_items,
            "total_amount": total_amount,
            "extraction_confidence": confidence,
        }

    # ------------------------------------------------------------------ #
    #  Item categorization                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def categorize_item(item_name: str) -> str:
        """
        Categorize a bill line item as 'variable', 'fixed', 'room', or 'other'.

        Categorization follows IRDAI proportionate-deduction rules:

        * **variable** — surgery, surgeon, nursing, OT, operation theatre,
          consultation, doctor visit, anaesthesia, ICU care.  These are
          subject to proportionate deduction (ICU is exempt per IRDAI but
          still categorised as variable).
        * **fixed** — medicines, pharmacy, implants, medical devices,
          diagnostics, laboratory, pathology, consumables, blood.  These
          are NOT subject to proportionate deduction.
        * **room** — room rent, ward charges, ICU room, deluxe room.
        * **other** — anything that doesn't match the above.

        Parameters
        ----------
        item_name
            The name/description of the bill line item.

        Returns
        -------
        str
            One of ``'variable'``, ``'fixed'``, ``'room'``, ``'other'``.
        """
        if not item_name or not item_name.strip():
            return "other"

        name_lower = item_name.lower().strip()

        # --- Check ROOM first (most specific) ---
        for kw in _ROOM_KEYWORDS:
            if kw in name_lower:
                return "room"

        # --- Check FIXED ---
        for kw in _FIXED_KEYWORDS:
            if kw in name_lower:
                return "fixed"

        # --- Check VARIABLE ---
        for kw in _VARIABLE_KEYWORDS:
            if kw in name_lower:
                return "variable"

        return "other"

    # ------------------------------------------------------------------ #
    #  File type detection & text extraction                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _detect_file_type(file_path: str) -> str:
        """Detect file type from extension."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return "pdf"
        # Images
        if ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp"):
            return "image"
        # Default to image for unknown extensions
        return "image"

    @staticmethod
    def _extract_pdf_text(file_path: str) -> str:
        """Extract text from a PDF using pdfplumber."""
        import pdfplumber

        text_parts: List[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        return "\n".join(text_parts)

    @staticmethod
    def _extract_image_text(file_path: str) -> str:
        """Extract text from an image using pytesseract."""
        import pytesseract
        from PIL import Image

        img = Image.open(file_path)
        return pytesseract.image_to_string(img)

    # ------------------------------------------------------------------ #
    #  Metadata extraction helpers                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract_hospital_name(lines: List[str]) -> str:
        """Extract hospital name from the first few lines of the bill."""
        # Hospital name is usually in the first 5 lines and contains a
        # hospital-related keyword
        for i, line in enumerate(lines[:10]):
            line_lower = line.lower()
            for label in _HOSPITAL_LABELS:
                if label in line_lower:
                    # Clean up the line — remove excessive whitespace
                    name = re.sub(r"\s+", " ", line).strip()
                    # Remove common prefixes/suffixes
                    name = re.sub(r"^(?:tax\s*invoice|invoice|bill|receipt)\s*[:\-]?\s*", "", name, flags=re.IGNORECASE)
                    return name.strip()

        # Fallback: first non-empty line that looks like a name (all caps or title case)
        for line in lines[:5]:
            stripped = line.strip()
            if stripped and len(stripped) > 3:
                # Check if it looks like a hospital name (not a number or date)
                if not re.match(r"^[\d\s/\-.,]+$", stripped):
                    return stripped

        return ""

    @staticmethod
    def _extract_bill_number(lines: List[str]) -> str:
        """Extract bill/invoice number from the bill text."""
        for line in lines:
            line_lower = line.lower()
            for label in _BILL_NO_LABELS:
                if label in line_lower:
                    # Extract the number after the label
                    # Look for alphanumeric sequence
                    pattern = re.compile(
                        rf"{re.escape(label)}\s*[:.#]?\s*([A-Z0-9/\-]+)",
                        re.IGNORECASE,
                    )
                    m = pattern.search(line)
                    if m:
                        return m.group(1).strip()
                    # Try extracting any alphanumeric after the label position
                    idx = line_lower.find(label) + len(label)
                    remainder = line[idx:]
                    m2 = re.match(r"\s*[:.#]?\s*([A-Z0-9/\-]+)", remainder, re.IGNORECASE)
                    if m2:
                        return m2.group(1).strip()

        return ""

    @staticmethod
    def _extract_date(text: str) -> str:
        """Extract a date from the bill text (Indian format DD/MM/YYYY)."""
        for pat in _DATE_PATTERNS:
            m = pat.search(text)
            if m:
                # Normalize the date to DD/MM/YYYY format
                groups = m.groups()
                if len(groups) == 3:
                    day, month, year = groups
                    # Handle month name
                    if not month.isdigit():
                        month_map = {
                            "jan": "01", "feb": "02", "mar": "03", "apr": "04",
                            "may": "05", "jun": "06", "jul": "07", "aug": "08",
                            "sep": "09", "oct": "10", "nov": "11", "dec": "12",
                        }
                        month = month_map.get(month[:3].lower(), "01")
                    # Normalize year to 4 digits
                    if len(year) == 2:
                        year = "20" + year if int(year) < 50 else "19" + year
                    return f"{int(day):02d}/{int(month):02d}/{year}"

        return ""

    @staticmethod
    def _extract_patient_info(lines: List[str], full_text: str) -> Dict[str, Any]:
        """
        Extract patient info from the bill.  This will be redacted by
        redact_bill_json before the final JSON is returned.
        """
        info: Dict[str, Any] = {}

        # Patient name
        for line in lines[:20]:
            line_lower = line.lower()
            for label in _PATIENT_LABELS:
                if label in line_lower:
                    # Extract name after the label
                    pattern = re.compile(
                        rf"{re.escape(label)}\s*[:.]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){{0,3}})",
                        re.IGNORECASE,
                    )
                    m = pattern.search(line)
                    if m:
                        info["patient_name"] = m.group(1).strip()
                        break
            if "patient_name" in info:
                break

        # UHID / patient ID
        for line in lines[:20]:
            line_lower = line.lower()
            for label in _UHID_LABELS:
                if label in line_lower:
                    pattern = re.compile(
                        rf"{re.escape(label)}\s*[:.]?\s*([A-Z0-9]{{4,20}})",
                        re.IGNORECASE,
                    )
                    m = pattern.search(line)
                    if m:
                        info["uhid"] = m.group(1).strip()
                        break
            if "uhid" in info:
                break

        # Policy number
        for line in lines[:20]:
            line_lower = line.lower()
            for label in _POLICY_LABELS:
                if label in line_lower:
                    pattern = re.compile(
                        rf"{re.escape(label)}\s*[:.]?\s*([A-Z0-9]{{6,20}})",
                        re.IGNORECASE,
                    )
                    m = pattern.search(line)
                    if m:
                        info["policy_no"] = m.group(1).strip()
                        break
            if "policy_no" in info:
                break

        # Phone number
        for pat in _PHONE_PATTERNS:
            m = pat.search(full_text)
            if m:
                info["phone"] = m.group()
                break

        return info

    @staticmethod
    def _redact_patient_info(patient_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact PII from the patient_info dict.

        Replaces all PII values with ``[REDACTED]`` markers while keeping
        the field keys intact so the structure is visible.
        """
        if not patient_info:
            return {}

        redacted: Dict[str, Any] = {}
        for key, value in patient_info.items():
            if isinstance(value, str) and value:
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = "[REDACTED]"
        return redacted

    @staticmethod
    def _extract_room_rent(
        lines: List[str], full_text: str
    ) -> Tuple[float, float, int]:
        """
        Extract room rent total, per-day rate, and number of days.

        Returns (room_rent_total, room_rent_per_day, days).
        """
        room_rent_total = 0.0
        room_rent_per_day = 0.0
        days = 0

        # --- Extract room rent total ---
        for line in lines:
            line_lower = line.lower()
            if "room" in line_lower or "ward" in line_lower:
                # Try to find an amount on this line
                amounts = _AMOUNT_PATTERN.findall(line)
                if amounts:
                    # Take the last amount on the line (usually the total)
                    val = BillIngestion._parse_amount(amounts[-1])
                    if val > 0:
                        # Check if this is a room rent line (not just mentioning room)
                        if any(kw in line_lower for kw in ("room rent", "room charge", "ward charge", "room ")):
                            room_rent_total = val
                            break

        # --- Extract per-day rate ---
        m = _ROOM_PER_DAY_PATTERN.search(full_text)
        if m:
            room_rent_per_day = BillIngestion._parse_amount(m.group(1))

        # --- Extract number of days ---
        m = _DAYS_PATTERN.search(full_text)
        if m:
            days = int(m.group(1))

        # --- Derive missing values ---
        if room_rent_per_day > 0 and days > 0 and room_rent_total == 0:
            room_rent_total = room_rent_per_day * days
        elif room_rent_total > 0 and days > 0 and room_rent_per_day == 0:
            room_rent_per_day = room_rent_total / days
        elif room_rent_total > 0 and room_rent_per_day > 0 and days == 0:
            days = int(round(room_rent_total / room_rent_per_day))

        return room_rent_total, room_rent_per_day, days

    @staticmethod
    def _extract_line_items(lines: List[str]) -> List[Dict[str, Any]]:
        """
        Extract line items from the bill text.

        Looks for lines that have a description followed by numeric values
        (qty, unit_price, amount) separated by whitespace.
        """
        items: List[Dict[str, Any]] = []
        in_items_section = False

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            line_lower = line_stripped.lower()

            # Skip header lines
            if any(h in line_lower for h in (
                "description", "particulars", "item name", "qty", "quantity",
                "unit price", "rate", "amount", "sr.", "s.no", "sl no",
                "serial",
            )):
                in_items_section = True
                continue

            # Skip total/summary lines
            if any(kw in line_lower for kw in (
                "total", "subtotal", "sub total", "grand total",
                "net amount", "amount payable", "discount",
                "tax", "gst", "round off", "round-off",
            )):
                continue

            # Skip metadata lines (hospital name, dates, patient info)
            if any(kw in line_lower for kw in (
                "hospital", "clinic", "patient", "bill no", "invoice no",
                "date", "uhid", "policy", "doctor", "consultant",
            )):
                # But don't skip if it also has amounts (could be a charge line)
                if not _AMOUNT_PATTERN.search(line_stripped):
                    continue

            # Try to parse as a line item
            item = BillIngestion._parse_line_item(line_stripped)
            if item:
                items.append(item)

        return items

    @staticmethod
    def _parse_line_item(line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single line as a bill line item.

        Tries multiple column patterns:
          1. name + qty + unit_price + amount (4 columns)
          2. name + qty + amount (3 columns)
          3. name + amount (2 columns)
        """
        # Pattern 1: name + qty + unit_price + amount
        m = _LINE_ITEM_PATTERN.match(line)
        if m:
            name = m.group(1).strip()
            qty = int(m.group(2))
            unit_price = BillIngestion._parse_amount(m.group(3))
            amount = BillIngestion._parse_amount(m.group(4))
            category = BillIngestion.categorize_item(name)
            confidence = BillIngestion._item_confidence(name, qty, unit_price, amount)
            return {
                "name": name,
                "qty": qty,
                "unit_price": unit_price,
                "amount": amount,
                "category": category,
                "raw_text": line,
                "confidence": confidence,
            }

        # Pattern 2: name + qty + amount
        m = _LINE_ITEM_PATTERN_3COL.match(line)
        if m:
            name = m.group(1).strip()
            qty = int(m.group(2))
            amount = BillIngestion._parse_amount(m.group(3))
            unit_price = amount / qty if qty > 0 else 0.0
            category = BillIngestion.categorize_item(name)
            confidence = BillIngestion._item_confidence(name, qty, unit_price, amount)
            return {
                "name": name,
                "qty": qty,
                "unit_price": round(unit_price, 2),
                "amount": amount,
                "category": category,
                "raw_text": line,
                "confidence": confidence,
            }

        # Pattern 3: name + amount
        m = _LINE_ITEM_PATTERN_2COL.match(line)
        if m:
            name = m.group(1).strip()
            amount = BillIngestion._parse_amount(m.group(2))
            # Skip if the "name" is just a number or too short
            if len(name) < 3 or re.match(r"^[\d\s.,\-/]+$", name):
                return None
            category = BillIngestion.categorize_item(name)
            confidence = BillIngestion._item_confidence(name, 1, amount, amount)
            return {
                "name": name,
                "qty": 1,
                "unit_price": amount,
                "amount": amount,
                "category": category,
                "raw_text": line,
                "confidence": confidence,
            }

        return None

    @staticmethod
    def _extract_total(lines: List[str], full_text: str) -> float:
        """Extract the total bill amount."""
        # Try grand total first, then total amount, then total
        for pat in _TOTAL_PATTERNS:
            m = pat.search(full_text)
            if m:
                val = BillIngestion._parse_amount(m.group(1))
                if val > 0:
                    return val

        # Fallback: look for "Grand Total" line and take the last number
        for line in lines:
            line_lower = line.lower()
            if "grand total" in line_lower or "total amount" in line_lower:
                amounts = _AMOUNT_PATTERN.findall(line)
                if amounts:
                    return BillIngestion._parse_amount(amounts[-1])

        return 0.0

    # ------------------------------------------------------------------ #
    #  Utility helpers                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_amount(value: str) -> float:
        """
        Parse an amount string that may use Indian or international formatting.

        Handles:
          * "1,23,456" (Indian lakh format)
          * "123,456.78" (international format)
          * "123456.78" (plain)
          * "12,345.00"
        """
        if not value:
            return 0.0

        cleaned = value.strip().replace(",", "").replace(" ", "")
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _item_confidence(
        name: str, qty: int, unit_price: float, amount: float
    ) -> float:
        """
        Compute a confidence score (0.0–1.0) for a parsed line item.

        Higher confidence when:
          * Name is descriptive (longer than a few chars)
          * Qty and unit_price are present and consistent with amount
          * Amount is a positive number
        """
        score = 0.5  # base

        if len(name) >= 5:
            score += 0.1
        if len(name) >= 10:
            score += 0.05

        if qty > 0:
            score += 0.1

        if unit_price > 0:
            score += 0.1

        if amount > 0:
            score += 0.1

        # Check consistency: qty * unit_price ≈ amount
        if qty > 0 and unit_price > 0 and amount > 0:
            expected = qty * unit_price
            if abs(expected - amount) / max(amount, 1) < 0.05:
                score += 0.1
            elif abs(expected - amount) / max(amount, 1) < 0.15:
                score += 0.05

        return min(score, 1.0)

    @staticmethod
    def _compute_confidence(
        hospital_name: str,
        bill_number: str,
        bill_date: str,
        line_items: List[Dict[str, Any]],
        total_amount: float,
    ) -> float:
        """
        Compute overall extraction confidence for the bill.

        Based on how many key fields were successfully extracted and the
        average confidence of line items.
        """
        score = 0.0
        fields_found = 0
        total_fields = 5

        if hospital_name:
            fields_found += 1
        if bill_number:
            fields_found += 1
        if bill_date:
            fields_found += 1
        if line_items:
            fields_found += 1
        if total_amount > 0:
            fields_found += 1

        score = fields_found / total_fields  # 0.0 to 1.0

        # Blend with average line item confidence
        if line_items:
            avg_item_conf = sum(
                item.get("confidence", 0.5) for item in line_items
            ) / len(line_items)
            score = (score * 0.6) + (avg_item_conf * 0.4)

        return round(score, 2)

    @staticmethod
    def _empty_bill(reason: str = "") -> Dict[str, Any]:
        """Return an empty bill JSON with an error note."""
        return {
            "hospital_name": "",
            "bill_number": "",
            "bill_date": "",
            "patient_info": {},
            "room_rent_total": 0.0,
            "room_rent_per_day": 0.0,
            "days": 0,
            "line_items": [],
            "total_amount": 0.0,
            "extraction_confidence": 0.0,
            "error": reason,
        }


# ---------------------------------------------------------------------------
# Module-level convenience functions (match the spec's function signatures)
# ---------------------------------------------------------------------------

def ingest_bill(file_path: str, file_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Main entry point: convert a bill image/PDF to structured JSON.

    Convenience wrapper around ``BillIngestion.ingest_bill``.

    Parameters
    ----------
    file_path
        Path to the bill file (PDF, PNG, JPEG, etc.).
    file_type
        Optional file type hint: ``"pdf"``, ``"image"``, or ``None``.

    Returns
    -------
    dict
        Canonical bill JSON with PII redacted.
    """
    return BillIngestion.ingest_bill(file_path, file_type)


def parse_bill_text(text: str) -> Dict[str, Any]:
    """
    Parse raw bill text into structured JSON.

    Convenience wrapper around ``BillIngestion.parse_bill_text``.

    Parameters
    ----------
    text
        Raw text extracted from the bill.

    Returns
    -------
    dict
        Canonical bill JSON dict.
    """
    return BillIngestion.parse_bill_text(text)


def categorize_item(item_name: str) -> str:
    """
    Categorize a bill line item.

    Convenience wrapper around ``BillIngestion.categorize_item``.

    Parameters
    ----------
    item_name
        The name/description of the bill line item.

    Returns
    -------
    str
        One of ``'variable'``, ``'fixed'``, ``'room'``, ``'other'``.
    """
    return BillIngestion.categorize_item(item_name)