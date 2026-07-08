from career_ops.ingestion.job_ingestion import JobIngestionPipeline
from career_ops.models import JobIngestionResult


class OpportunityAgent:
    name = "Opportunity Agent"

    def __init__(self, pipeline: JobIngestionPipeline | None = None) -> None:
        self.pipeline = pipeline or JobIngestionPipeline()

    def ingest_url(self, url: str) -> JobIngestionResult:
        return self.pipeline.ingest_url(url)
