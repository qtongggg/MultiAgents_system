from import BaseModel
from typing import List

# class RAGChunkAndSrc(BaseModel):
#     chunk: list[str]
#     source_id: str = None


# class RAGUpsertResult(BaseModel):
#     ingested: int


# class RAGSearchResult(BaseModel):
#     contexts: list[str]
#     sources: list[str]

# class RAGQueryRequest(BaseModel):
#     answer: str
#     sources: list[str]
#     num_contexts: int



class MatchResult(BaseModel):
    fit_score: float
    matching_skills: List[str]
    missing_skills: List[str]
    reason: str

class JobSearchInfo(BaseModel):
    job_id: str
    title: str
    company: str
    job_description: str
    location: str
    employment_type: str
    link: str

class SummaryJobInfo(BaseModel):
    brief_summary: str
    hr_insight: str


