from logging import getLogger
from typing import List, Any
from llama_index.core.schema import Document
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.llms.llm import LLM
from llama_index.core.workflow import (
    Context,
    Event,
    Workflow,
    StartEvent,
    StopEvent,
    step,
)

from subquery import get_sub_queries
from tavily import get_docs_from_tavily_search
from compress import get_compressed_context
from llm_prompts import generate_response_from_context



logger = getLogger(__name__)


class CompanyQueriesCreatedEvent(Event):
    company_queries: List[str]

class ToProcessCompanyQueryEvent(Event):
    company_query: str


class DocsScrapedEvent(Event):
    company_query: str
    docs: List[Document]

class ToCombineContextEvent(Event):
    company_query: str
    context: str

class ResultPromptCreatedEvent(Event):
    context: str


class LLMResponseEvent(Event):
    response: str


class CompanySearchWorkflow(Workflow):
    def __init__(
        self,
        *args: Any,
        llm: LLM,
        embed_model: BaseEmbedding,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.llm = llm
        self.embed_model = embed_model
        self.visited_urls: set[str] = set()

    @step
    async def get_company_details(self, ctx: Context, ev: StartEvent) -> CompanyQueriesCreatedEvent | None:
        
        query = ev.get("query")
        await ctx.set("query", query)
        company_queries = await get_sub_queries(query, self.llm, num_sub_queries=2)
        await ctx.set("num_company_queries", len(company_queries))
        return CompanyQueriesCreatedEvent(company_queries=company_queries)
    

    @step
    async def deligate_sub_queries(
        self, ctx: Context, ev: CompanyQueriesCreatedEvent
    ) -> ToProcessCompanyQueryEvent:
        for company_query in ev.company_queries:
            ctx.send_event(ToProcessCompanyQueryEvent(company_query=company_query))
        return None
    
    @step
    async def get_docs_for_subquery(
        self, ev: ToProcessCompanyQueryEvent
    ) -> DocsScrapedEvent:
        company_query = ev.company_query
        docs, visited_urls = await get_docs_from_tavily_search(
            company_query, self.visited_urls
        )
        self.visited_urls = visited_urls
        return DocsScrapedEvent(company_query=company_query, docs=docs)
    
    @step(num_workers=3)
    async def compress_docs(self, ev: DocsScrapedEvent) -> ToCombineContextEvent:
        company_query = ev.company_query
        docs = ev.docs
        print(f"\n> Compressing docs for sub query: {company_query}\n")
        compressed_context = await get_compressed_context(
            company_query, docs, self.embed_model
        )
        return ToCombineContextEvent(company_query=company_query, context=compressed_context)
   
    @step
    async def combine_contexts(
        self, ctx: Context, ev: ToCombineContextEvent
    ) -> ResultPromptCreatedEvent:
        events = ctx.collect_events(
            ev, [ToCombineContextEvent] * await ctx.get("num_company_queries")
        )
        if events is None:
            return None

        context = ""

        for event in events:
            context += (
                f'Response for topic "{event.company_query}":\n{event.context}\n\n'
            )

        return ResultPromptCreatedEvent(context=context)

    @step
    async def write_report(
        self, ctx: Context, ev: ResultPromptCreatedEvent
    ) -> StopEvent:
        context = ev.context
        query = await ctx.get("query")
        result = {}
        result["response"] = await generate_response_from_context(query, context, self.llm)
        result["visited_urls"] = self.visited_urls
        
        return StopEvent(result=result)