import requests

BASE_URL = "http://127.0.0.1:8001"


def upload_resume(file):
    files = {"file": (file.name, file.getvalue())}
    res = requests.post(f"{BASE_URL}/api/rag/upload", files=files)
    return res.json()


def rag_query(question: str):
    res = requests.post(
        f"{BASE_URL}/api/rag/query",
        json={"question": question}
    )
    return res.json()


def search_jobs(keyword, location="Malaysia", per_page=5, page=1):
    payload = {
        "keyword": keyword,
        "location": location,
        "per_page": per_page,
        "page": page
    }
    res = requests.post(f"{BASE_URL}/api/jobs/search", json=payload)
    return res.json()