import asyncio
from app.pipeline.orchestrator import PipelineOrchestrator
from app.schemas.search import SearchRequest


async def main():
    orchestrator = PipelineOrchestrator()
    request = SearchRequest(keyword="coffee shops", location="Seattle, WA", limit=10)
    result = await orchestrator.run(request)

    for lead in result.leads:
        print(lead.business_name, "|", lead.website, "|", lead.social.instagram_url)

    print("\nTotal leads:", len(result.leads))
    print("Stage times:", result.metrics.stage_times)


if __name__ == "__main__":
    asyncio.run(main())
