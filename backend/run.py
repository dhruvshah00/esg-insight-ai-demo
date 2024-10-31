import os
from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import shutil
import asyncio
from dotenv import load_dotenv
from llama_index.utils.workflow import draw_all_possible_flows
from llama_index.llms.nvidia import NVIDIA
from llama_index.embeddings.nvidia import NVIDIAEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding


from workflows.esg_materiality_analysis_workflow import *
from llama_index.core.workflow.handler import WorkflowHandler
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
from phoenix.otel import register
from llama_index.core import Settings


app = FastAPI()

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins, adjust this based on your needs
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

@app.websocket("/query")
async def query_endpoint(websocket: WebSocket):
    await websocket.accept()
    load_dotenv()

    client_headers = os.getenv("PHOENIX_CLIENT_HEADERS")
    if client_headers and client_headers.startswith("api_key="):
        tracer_provider = register(
            project_name="esg-insight-ai-app", 
            verbose=False,
            batch=True
            )
        LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider,skip_dep_check=True)


    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and len(openai_key) > 1:
        llm = OpenAI(model="gpt-4o")
        print("OpenAI")
    else:
        llm = NVIDIA(model="meta/llama-3.2-70b-instruct",base_url=)
    
    embed_model = NVIDIAEmbedding(model="NV-Embed-QA", truncate="END")

    Settings.llm = llm
    Settings.embed_model = embed_model
    workflow = ESGMaterialityAnalysisWorkflow(llm=llm,embed_model=embed_model, timeout=120.0 * 10)

    try:
        query_data = await websocket.receive_json()
        
        handler: WorkflowHandler = workflow.run(company_name=query_data["company_name"])
        async for event in handler.stream_events():

            if isinstance(event, ProgressEvent):
                await websocket.send_json({
                    "type": "progress",
                    "payload": str(event.msg)
                })

            if isinstance(event,InputRequiredOnCompanyDetailsEvent):
                await websocket.send_json({
                    "type": "input_required_company_details",
                    "payload": event.payload
                })
                response = await websocket.receive_json()
                if response["response"].lower() == "yes":
                    gics_sector = await handler.ctx.get("gics_sector")
                    gics_industry_group = await handler.ctx.get("gics_industry_group")
                    gics_industry = await handler.ctx.get("gics_industry")
                    company_description = await handler.ctx.get("company_description")
                    handler.ctx.send_event(CompanyDetailsAvailableEvent(gics_sector=gics_sector,gics_industry_group=gics_industry_group
                                                                        ,gics_industry=gics_industry,company_description=company_description, response=response["response"].lower()))
                elif response["response"].lower() == "no":
                    company_name = await handler.ctx.get("company_name")
                    handler.ctx.send_event(UserInputOnCompanyDetailsEvent(company_name = company_name, user_input=response["comment"], response=response["response"].lower()))
            
            if isinstance(event,CompanyDetailsAvailableEvent):
                await websocket.send_json({
                    "type": "company_details",
                    "payload": event.to_json()
                })
            
            if isinstance(event,GRITopicsAvailableEvent):
                await websocket.send_json({
                    "type": "gri_topics",
                    "payload": event.gri_topics
                })

            if isinstance(event, InputRequiredOnMaterialityTopicsEvent):
                await websocket.send_json({
                    "type": "input_required_gri_topics",
                    "payload": event.payload
                })
                response = await websocket.receive_json()
                if response["response"].lower() == "yes":
                    gri_topics = await handler.ctx.get("gri_topics")
                    handler.ctx.send_event(GRITopicsAvailableEvent(gri_topics = gri_topics, response=response["response"].lower()))
                elif response["response"].lower() == "no":
                    handler.ctx.send_event(UserInputOnMaterialityTopicsEvent(user_input=response["comment"], response=response["response"].lower()))

            if isinstance(event,TopicAssesmentAvailableEvent):
                await websocket.send_json({
                    "type": "topic_assesment",
                    "payload": event.to_json()
                })
        
        result = await handler
        await websocket.send_json({
            "type": "un_sdg_list", 
            "payload": result
        })

    except Exception as e:
        print("ERROR: "+ str(e))
        await websocket.send_json({"type": "error", "payload": str(e)})
    finally:
        await websocket.close()
    

@app.post("/upload")
async def upload_files(
    company_name: str = Form(...),  # Form data
    files: List[UploadFile] = File(...)  # List of files
):
    try:
        # Define the path where the files will be saved
        UPLOAD_DIRECTORY = f"data/company_docs/{company_name}"
        os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

        # List to store information about uploaded files
        uploaded_files = []

        # Loop through the list of files
        for file in files:
            file_location = os.path.join(UPLOAD_DIRECTORY, file.filename)

            # Save the uploaded file to the specified location
            with open(file_location, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            uploaded_files.append(file.filename)

        # Return success message with the list of uploaded files
        return JSONResponse(content={"message": f"Files uploaded successfully!", "files": uploaded_files})

    except Exception as e:
        # Return error message if something goes wrong
        print(f"An error occurred while uploading the files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred while uploading the files: {str(e)}")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
