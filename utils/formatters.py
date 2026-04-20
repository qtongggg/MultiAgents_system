def format_jobs_list(payloads: list[dict]) -> str:
    if not payloads:
        return "No jobs found."

    lines = ["Here are the jobs:\n"]

    for job in payloads:
        title = job.get("title", "Unknown")
        company = job.get("company", "Unknown")
        location = job.get("location", "Unknown")
        link = job.get("link", "")

        lines.append(f"- {title} @ {company} ({location})")
        if link:
            lines.append(f"  Apply: {link}")

    return "\n".join(lines)


def format_jobs_context(payloads: list[dict]) -> str:
    blocks = []

    for job in payloads:
        blocks.append(f"""
                    Title: {job.get("title")}
                    Company: {job.get("company")}
                    Location: {job.get("location")}
                    Description: {job.get("job_description")}
                    """)

    return "\n\n".join(blocks)