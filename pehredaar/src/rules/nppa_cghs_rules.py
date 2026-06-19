from typing import List, Dict, Any

def check_cghs_benchmarks(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flag medicine ceiling breaches and CGHS reference benchmarks."""
    flags = []

    # Mocking a benchmark database
    cghs_benchmarks = {
        "consultation": 300,
        "paracetamol 500mg": 1.5
    }

    for item in items:
        name = item.get("canonical_name", "").lower()
        price = item.get("unit_price", 0)

        if name in cghs_benchmarks and price > cghs_benchmarks[name]:
            flags.append({
                "item": item["canonical_name"],
                "reason": f"Exceeds CGHS benchmark of {cghs_benchmarks[name]}.",
                "clause": "CGHS Benchmark (Reference Only)"
            })

    return flags
