"""Search endpoint: runs the full lead-generation pipeline (Maps
discovery -> website enrichment -> social discovery -> URL selection)
for one keyword/location and returns the resulting leads."""

from dataclasses import asdict

from fastapi import APIRouter

from app.core.playwright_loop import run_playwright
from app.pipeline.orchestrator import PipelineOrchestrator
from app.schemas.response import APIResponse
from app.schemas.search import LeadOut, MetricsOut, ProgressOut, SearchRequest, SearchResult

router = APIRouter()


@router.post("/search", response_model=APIResponse[SearchResult], tags=["search"])
async def search(request: SearchRequest) -> APIResponse[SearchResult]:
    orchestrator = PipelineOrchestrator()
    result = await run_playwright(orchestrator.run(request))

    data = SearchResult(
        leads=[LeadOut.from_domain(lead) for lead in result.leads],
        total=len(result.leads),
        metrics=MetricsOut(**asdict(result.metrics)),
        progress=ProgressOut(**asdict(result.progress)),
    )
    return APIResponse.ok(data=data, message=f"Found {len(data.leads)} leads")
