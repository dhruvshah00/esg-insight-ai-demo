from llama_index.core.llms.llm import LLM
from llama_index.core.prompts.base import PromptTemplate


async def generate_structured_output(context:str, schema:str, llm: LLM) -> str:
    extraction_prompt = PromptTemplate("""
    Context information is below:
    ---------------------
    {context}
    ---------------------

    Given the context information and not prior knowledge, create a JSON object from the information in the context.
    The JSON object must follow the JSON schema:
    ----------------------------------------------
    {schema}
    ----------------------------------------------
                                       
    Return ONLY JSON without any markdown or extra string.

    """)

    response = await llm.apredict(
        extraction_prompt,
        context = context,
        schema = schema
    )

    return response

async def generate_formatted_markdown_text(context: str, llm: LLM) -> str:
    extraction_prompt = PromptTemplate("""
    Context information is below:
    ---------------------
    {context}
    ---------------------

    Return the exact same text as neatly formatted markdown but without ```markdown string. 
    Do not include any headings or subheading in the response.

    """)

    response = await llm.apredict(
        extraction_prompt,
        context = context,
    )

    return str(response)

async def consolidate_assesment(assesment_1: str,assesment_2: str,llm: LLM) -> str:
    prompt = PromptTemplate("""
    Rewrite a final 150 word assesment summary using the below 2 assesments. 
    
    Assesment 1:
    -----------------------------------------------------------------------------
    {assesment_1}
    -----------------------------------------------------------------------------
                            
    Assesment 2:
    -----------------------------------------------------------------------------
    {assesment_2}
    -----------------------------------------------------------------------------

    Do not include any headings or subheading in the assesment. Return assesment as formatted markdown but without ```markdown string.

    """)

    response = await llm.apredict(
        prompt,
        assesment_1 = assesment_1,
        assesment_2 = assesment_2,
    )

    return str(response)

async def generate_response_from_context(query: str, context: str, llm: LLM) -> str:
    print("context")
    print(len(context))
    prompt = PromptTemplate(
        """Information:
--------------------------------
{context}
--------------------------------
Using the above information, answer the following query or task: "{question}" in less than 100 words.
"""
    )
    response = await llm.apredict(
        prompt,
        context=context,
        question=query,
    )

    return response

async def get_prelim_gri_topics(gics_sector:str,gics_industry_group:str,gics_industry:str,company_description:str, topic_count : int, llm: LLM) -> list[str]:
    prompt = PromptTemplate(
        """
List Top {topic_count} applicable GRI topics for below company profile.

GICS Sector: {gics_sector}
GICS Industry Group: {gics_industry_group}
GICS Industry: {gics_industry}
Company Description: {company_description}

You must respond with the GRI topics separated by comma in the following format: topic code 1 - topic name 1, topic code 2 - topic name 2, topic code 3 - topic name 3

Return nothing before or after the comma seperate values of GRI topics
"""
    )
    response = await llm.apredict(
        prompt,
        gics_sector=gics_sector,
        gics_industry_group=gics_industry_group,
        gics_industry=gics_industry,
        company_description=company_description,
        topic_count=str(topic_count),
    )

    gri_topics = list(
        map(lambda x: x.strip().strip('"').strip("'"), response.split(","))
    )

    return gri_topics

async def get_revised_gri_topics(gics_sector:str,gics_industry_group:str,gics_industry:str,company_description:str, prev_gri_topics : list[str], user_input : str, llm: LLM) -> list[str]:
    prompt = PromptTemplate(
        """
Previously you return below applicable gri topics list for given company profile.

GICS Sector: {gics_sector}
GICS Industry Group: {gics_industry_group}
GICS Industry: {gics_industry}
Company Description: {company_description}

Previous GRI Topics: {prev_gri_topics}

User provided below feedback. Incorporate the user feedback and return an updated list again.

------------------------------------------------------------------------------------------------
User feedback: {user_input}
------------------------------------------------------------------------------------------------

You must respond with the GRI topics separated by comma in the following format: topic code 1 - topic name 1, topic code 2 - topic name 2, topic code 3 - topic name 3

Return nothing before or after the comma seperate values of GRI topics
"""
    )
    response = await llm.apredict(
        prompt,
        gics_sector=gics_sector,
        gics_industry_group=gics_industry_group,
        gics_industry=gics_industry,
        company_description=company_description,
        last_gri_topics=str(prev_gri_topics),
        user_input=user_input
    )

    gri_topics = list(
        map(lambda x: x.strip().strip('"').strip("'"), response.split(","))
    )

    return gri_topics

async def get_applicable_un_sdg_list(company_name:str,assesment:str,llm:LLM):
    prompt = PromptTemplate(
        """
List applicable UN SDG for company {company_name} based on below assesment by GRI topics.

{assesment}

You must respond with the UN SDG name separated by comma in the following format: goal name 1, goal name 2, goal name 3

Return nothing before or after the comma seperate values of UN SDG goals
"""
    )
    response = await llm.apredict(
        prompt,
        company_name=company_name,
        assesment=assesment,
    )

    un_sdg_list = list(
        map(lambda x: x.strip().strip('"').strip("'"), response.split(","))
    )

    return un_sdg_list