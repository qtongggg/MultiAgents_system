def filter_jobs_by_company(payloads: list[dict], company_name: str) -> list[dict]:
    target = company_name.lower().strip()
    return [
        p for p in payloads
        if target in (p.get("company", "") or "").lower()
    ]