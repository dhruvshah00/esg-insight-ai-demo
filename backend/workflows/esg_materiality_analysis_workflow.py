import json
from logging import getLogger
from typing import List, Any
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.llms.llm import LLM

from llama_index.core.workflow import (
    Context,
    Event,
    Workflow,
    step,
)
from llama_index.core.workflow.events import (
    StartEvent,
    StopEvent,
    InputRequiredEvent,
    HumanResponseEvent
)

from llm_prompts import *

from workflows.company_search_workflow import CompanySearchWorkflow
from workflows.gri_workflow import GRIWorkflow, get_gri_workflow
from workflows.company_docs_workflow import CompanyDocsWorkflow



logger = getLogger(__name__)



class CompanyDetailsAvailableEvent(HumanResponseEvent):
    gics_sector: str
    gics_industry_group: str
    gics_industry: str
    company_description: str

    def to_json(self):
        return {"gics_sector":self.gics_sector,
                "gics_industry_group":self.gics_industry_group,
                "gics_industry":self.gics_industry,
                "company_description":self.company_description,
                }

class GRITopicsAvailableEvent(HumanResponseEvent):
    gri_topics: list[str]

class GRIReportingRequirementsAvailableEvent(Event):
    gri_topic: str
    reporting_requirements: str

class TopicAssesmentAvailableEvent(Event):
    gri_topic: str
    reporting_requirements: str
    assesment: str
    source_texts: list[str]

    def to_json(self):
        return {
            "gri_topic": self.gri_topic,
            "reporting_requirements": self.reporting_requirements,
            "assesment": self.assesment,
            "source_texts": self.source_texts
        }
    
class FormattedTopicAssesmentAvailableEvent(Event):
    formatted_assesment:str
    formatted_source_texts: list[str]


class ProgressEvent(Event):
    pass

class InputRequiredOnMaterialityTopicsEvent(InputRequiredEvent):
    pass

class InputRequiredOnCompanyDetailsEvent(InputRequiredEvent):
    pass

class UserInputOnMaterialityTopicsEvent(HumanResponseEvent):
    user_input: str

class UserInputOnCompanyDetailsEvent(HumanResponseEvent):
    company_name: str
    user_input: str



class ESGMaterialityAnalysisWorkflow(Workflow):
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
    async def get_company_details(self, ctx: Context, ev: StartEvent | UserInputOnCompanyDetailsEvent) -> InputRequiredOnCompanyDetailsEvent:
        company_name = ev.get("company_name")
        await ctx.set("company_name", company_name)
        progress_message = f"Retrieving GICS Sector, Industry, and Key Description for {company_name}...."
        ctx.write_event_to_stream(ProgressEvent(msg=progress_message))
        
        if isinstance(ev, StartEvent):
            query = f"Find out GICS Sector, GICS Industry Group, GICS Industry and high level description for company {company_name}"
            company_search_workflow = CompanySearchWorkflow(llm=self.llm,embed_model=self.embed_model, timeout=120.0 * 4)
            result = await company_search_workflow.run(query=query)
            company_details = str(result["response"])
            structured_company_details = await generate_structured_output(context=company_details, schema=CompanyDetailsAvailableEvent.model_json_schema(), llm=self.llm)
            company_details_json = json.loads(structured_company_details)

        elif isinstance(ev, UserInputOnCompanyDetailsEvent):
            company_name = ev.company_name
            user_input = ev.user_input
            query = f"Find out GICS Sector, GICS Industry Group, GICS Industry and high level description for company {company_name}. Make sure you consider user input: {user_input} when formulating a response."
            company_search_workflow = CompanySearchWorkflow(llm=self.llm,embed_model=self.embed_model, timeout=120.0 * 4)
            result = await company_search_workflow.run(query=query)
            company_details = str(result["response"])
            structured_company_details = await generate_structured_output(context=company_details, schema=CompanyDetailsAvailableEvent.model_json_schema(), llm=self.llm)
            company_details_json = json.loads(structured_company_details)

        gics_sector = company_details_json["gics_sector"]
        gics_industry_group = company_details_json["gics_industry_group"]
        gics_industry = company_details_json["gics_industry"]
        company_description = company_details_json["company_description"]

        await ctx.set("gics_sector", gics_sector)
        await ctx.set("gics_industry_group", gics_industry_group)
        await ctx.set("gics_industry", gics_industry)
        await ctx.set("company_description", company_description)

        ctx.write_event_to_stream(CompanyDetailsAvailableEvent(gics_sector=gics_sector,gics_industry_group=gics_industry_group
                                            ,gics_industry=gics_industry,company_description=company_description,response=""))
        
        return InputRequiredOnCompanyDetailsEvent(prefix="",payload=f"Do you agree with GICS classification for {company_name}?")
    
    

    @step
    async def get_prelim_materiality_topics(
        self, ctx: Context, ev: CompanyDetailsAvailableEvent | UserInputOnMaterialityTopicsEvent
    ) -> InputRequiredOnMaterialityTopicsEvent:
        company_name = await ctx.get("company_name")
        progress_message = f"Retrieving applicable GRI topics for {company_name}...."
        ctx.write_event_to_stream(ProgressEvent(msg=progress_message))
        if isinstance(ev, CompanyDetailsAvailableEvent):
            gics_sector = ev.gics_sector
            gics_industry_group = ev.gics_industry_group
            gics_industry = ev.gics_industry
            company_description = ev.company_description
            gri_topics = await get_prelim_gri_topics(gics_sector = gics_sector,gics_industry_group= gics_industry_group,gics_industry = gics_industry,company_description= company_description,topic_count=3,llm=self.llm)
        elif isinstance(ev, UserInputOnMaterialityTopicsEvent):
            gics_sector = await ctx.get("gics_sector")
            gics_industry_group = await ctx.get("gics_industry_group")
            gics_industry = await ctx.get("gics_industry")
            company_description = await ctx.get("company_description")
            prev_gri_topics = await ctx.get("gri_topics")

            user_input = ev.user_input
            gri_topics = await get_revised_gri_topics(gics_sector = gics_sector,gics_industry_group= gics_industry_group,gics_industry = gics_industry,company_description= company_description,prev_gri_topics=prev_gri_topics,user_input=user_input,llm=self.llm)
        
        ctx.write_event_to_stream(GRITopicsAvailableEvent(gri_topics = gri_topics, response=""))
        await ctx.set("gri_topics", gri_topics)
        return InputRequiredOnMaterialityTopicsEvent(prefix="",payload=f"Do you agree with the list of applicable GRI materilaity topics for {company_name}?")
        
    

    @step
    async def get_reporting_requirements_by_topic(
        self, ctx: Context, ev: GRITopicsAvailableEvent
    ) -> GRIReportingRequirementsAvailableEvent:
        gri_topics = ev.gri_topics
        
        gri_workflow = get_gri_workflow(llm=self.llm, embed_model=self.embed_model)
        progress_message = f"Analyzing reporting requirememnts for the chosen GRI Topics..."
        ctx.write_event_to_stream(ProgressEvent(msg=progress_message))
        await ctx.set("num_gri_topics_to_collect", len(gri_topics))
        for gri_topic in gri_topics:
            query = f"""List top 3 reporting requirements for GRI topic: {gri_topic}. 
            Do not include any headings or subheading in the assesment.
            Return reporting requirements as formatted markdown but without ```markdown string."""
            reporting_requirements = await gri_workflow.run(query = query)
            self.send_event(GRIReportingRequirementsAvailableEvent(gri_topic=gri_topic, reporting_requirements=reporting_requirements))

    
    @step
    async def get_topic_assesment(
        self, ctx: Context, ev: GRIReportingRequirementsAvailableEvent
    ) -> TopicAssesmentAvailableEvent:
        gri_topic = ev.gri_topic
        reporting_requirements = ev.reporting_requirements
        company_name = await ctx.get("company_name")
        documents = SimpleDirectoryReader(f"data/company_docs/{company_name}").load_data()
        index = VectorStoreIndex.from_documents(
            documents=documents,
            embed_model=self.embed_model,
        )

        progress_message = f"Preparing assement summary using company documents...."
        ctx.write_event_to_stream(ProgressEvent(msg=progress_message))
        doc_query = f"""Prepare an assesment report in about 200 words on gri topic {gri_topic} covering the reporting requirements listed below: 
        ------------------------------------------------------------------------------------------------------------------------------------
        {reporting_requirements}. 
        ------------------------------------------------------------------------------------------------------------------------------------

        """

        workflow_docs = CompanyDocsWorkflow(index=index,llm=self.llm,embed_model=self.embed_model, timeout=120.0 * 4)
        result_docs = await workflow_docs.run(query=doc_query)
        assesment_docs = str(result_docs)
        source_texts = []
        for source_node in result_docs.source_nodes:

            formatted_source_text = await generate_formatted_markdown_text(context = source_node.node.get_text(), llm=self.llm)
            source_texts.append(formatted_source_text)

        
        progress_message = f"Preparing assement summary using internet search data...."
        ctx.write_event_to_stream(ProgressEvent(msg=progress_message))
        search_query = f"""Prepare an assesment report in about 200 words for company {company_name} on gri topic {gri_topic} covering the reporting requirements listed below: 
        ------------------------------------------------------------------------------------------------------------------------------------
        {reporting_requirements}. 
        ------------------------------------------------------------------------------------------------------------------------------------

        """
        workflow_search = CompanySearchWorkflow(llm=self.llm,embed_model=self.embed_model, timeout=120.0 * 4)
        result_search = await workflow_search.run(query=search_query)
        assesment_search = str(result_search["response"])
        visited_urls = list(result_search["visited_urls"])
        source_texts.extend(visited_urls)
        
        progress_message = f"Finalizing assement summary...."
        ctx.write_event_to_stream(ProgressEvent(msg=progress_message))
        assesment = await consolidate_assesment(assesment_1 = assesment_docs,assesment_2 = assesment_search,llm=self.llm)
        
        
        ctx.write_event_to_stream(TopicAssesmentAvailableEvent(gri_topic=gri_topic,reporting_requirements=reporting_requirements,assesment=assesment,source_texts=source_texts))
        return TopicAssesmentAvailableEvent(gri_topic=gri_topic,reporting_requirements=reporting_requirements,assesment=assesment,source_texts=source_texts)

        
    @step
    async def combine_assesment(
        self, ctx: Context, ev: TopicAssesmentAvailableEvent
    ) -> StopEvent | None:
        company_name = await ctx.get("company_name")
        num_gri_topics_to_collect = await ctx.get("num_gri_topics_to_collect")
        assesments = ctx.collect_events(ev, [TopicAssesmentAvailableEvent] * num_gri_topics_to_collect)
        if assesments is None:
            return None
        
        consolidated_assesment = ""
        for idx, event in enumerate(assesments):
            # topic_assessment_collection.append({""})
            consolidated_assesment += f"""{idx}) GRI Topic: {event.gri_topic} 

            Assesment: {event.assesment}


            """

        un_sdg_list = await get_applicable_un_sdg_list(company_name = company_name,assesment = consolidated_assesment,llm=self.llm)

        return StopEvent(result=un_sdg_list)


    

    
    
    