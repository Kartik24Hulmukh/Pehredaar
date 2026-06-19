from typing import Dict, Any, List

def generate_sheet(exposure: int, flags: List[str]) -> Dict[str, Any]:
    """Generates a Before You Sign sheet output."""
    script = "Hi, I noticed the proportionate deduction is very high. Can you please check if it's correctly calculated?"

    # Enhancing the script based on P4 requirements
    sheet_content = f"### Before You Sign\n\n**Total Exposure:** ₹{exposure}\n\n**Top Flags:**\n"
    for idx, flag in enumerate(flags[:5]):
        sheet_content += f"{idx + 1}. {flag}\n"

    if exposure > 10000:
        script = f"Hi, I noticed my exposure is ₹{exposure}. Could you confirm that items like medicines and consumables were NOT subjected to proportionate deduction as per IRDAI rules?"

    return {
        "exposure": exposure,
        "flags": flags,
        "sheet_content": sheet_content,
        "script": script,
        "written_confirmation_instructions": "Ask the hospital desk to provide in writing that proportionate deduction was not applied to fixed items (medicines, implants).",
        "disclaimer": "Informational only, not legal or insurance advice."
    }
