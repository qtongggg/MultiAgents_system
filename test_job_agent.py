from tools.job_searcher import search_jobs

jobs = search_jobs(
            "ai engineer",
            "malaysia",
            page=1,
            per_page= 3
        )

print(jobs)