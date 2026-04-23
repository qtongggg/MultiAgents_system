import sys
import uuid
import requests 
import os 
import inngest
from dotenv import load_dotenv
import http.client
import urllib.parse
import json
import uuid
from pprint import pprint

load_dotenv()


def search_jobs(keyword: str, location: str = "Malaysia", page: int = 1, per_page: int = 5):
    API_KEY = os.getenv("JOB_SEARCH_API_KEY").strip()
    conn = http.client.HTTPSConnection("api.openwebninja.com")
    
    query_params = urllib.parse.urlencode({
    "query": keyword,
    "location": location,
    "country": "MY",
    "page": str(page),
    "job_publishers": "linkedin",
    "per_page": str(per_page),
    "date_posted": "month",   # only jobs posted in the last month
})

    headers = {
    'x-api-key': API_KEY
    
    }
    conn.request("GET", f"/jsearch/search?{query_params}", headers=headers)
    res = conn.getresponse()
    data = res.read()
    jobs_json = json.loads(data.decode("utf-8"))

    # return only the first `per_page` jobs
    
    jobs = jobs_json.get("data", [])[:per_page]
    
    
    return jobs


def clean_job_results(jobs):
    cleaned = [
        {
            "job_id": job.get("job_id") or str(uuid.uuid4()),
            "title": job.get("job_title") or "",
            "company": job.get("employer_name") or "",
            "job_description": job.get("job_description") or "",
            "location": job.get("job_location") or "",
            "employment_type": job.get("job_employment_type") or "",
            "link": job.get("job_apply_link") or "",
        }
        for job in jobs
    ]
    return cleaned

