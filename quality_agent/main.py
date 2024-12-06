from quality_agent.workflowManager import WorkflowManager
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from models.models import Query, QueryResponse
from langchain.globals import set_debug, set_verbose
from quality_agent.llmManager import LLMManager
from typing import List
from quality_agent.logger import setup_logger
import json
import getpass
import os
from dotenv import load_dotenv

logger = setup_logger(__name__)


load_dotenv()


if os.getenv("ENABLE_DEBUGGING") == "true":
    set_debug(True)
else:
    set_verbose(True)


def _set_if_undefined(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"Please provide your {var}")


# _set_if_undefined("OPENAI_API_KEY")

# Initialize managers
try:
    logger.info("Initializing managers")
    llm_manager = LLMManager()

    workflow_manager = WorkflowManager(
        llm_manager=llm_manager)
    logger.info("Managers initialized successfully")
except Exception as e:
    logger.error(f"Error initializing managers: {e}")
    raise

# Create workflow with managers
try:
    logger.info("Generating workflow graph")
    graph = workflow_manager.generate_graph()
    logger.info("Workflow graph generated successfully")
except Exception as e:
    logger.error(f"Error generating workflow graph: {e}")
    raise

app = FastAPI()

origins = ["http://localhost:4200", "http://localhost:3005"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")


@app.post("/query")
async def runQuery(query: Query) -> QueryResponse:
    try:
        logger.info(f"Processing query: {query.query}")
        response = []
        finalResponse = QueryResponse(answer='', chart='', reviewImage=None)
        config = {"configurable": {"thread_id": "1"}, "recursion_limit": 100}
        input = {"question": query.query}
        state = graph.get_state(config)
        input = handleInterrupts(query, config, state, input)

        for stream_data in graph.stream(input, config):
            if "__end__" not in stream_data:
                response.append(stream_data)
                node_response = (
                    stream_data.get('query_data_node') or
                    stream_data.get('record_sales_node') or
                    stream_data.get('human_record_sales_confirmation_node') or
                    stream_data.get('help_node') or
                    stream_data.get('no_context_node')
                )
               
                visualization_response = (
                    stream_data.get('visualization_node') or
                    stream_data.get('generate_mongo_query_node') or
                    stream_data.get('generate_chart_node') or
                    stream_data.get('analyze_plot_node')
                )
                # analyzing_plot_response =  stream_data.get('analyze_plot_node')
                # interrupt_responses = stream_data.get('__interrupt__')
                if node_response:
                    finalResponse.answer = node_response.get('answer')
                elif visualization_response:
                    finalResponse.chart = visualization_response.get('chart')
                    finalResponse.answer = visualization_response.get('answer')
                # elif analyzing_plot_response:
                #     finalResponse.answer = analyzing_plot_response.get('answer')
                # elif interrupt_responses:
                #     finalResponse.answer = '\n'.join(
                #         message.value for message in interrupt_responses)

        if finalResponse.answer == '' and finalResponse.chart == '':
            finalResponse.answer = "Unable to process the query. Could you provide more information?"
        logger.info(f"Query processed successfully: {finalResponse.answer}")
        return finalResponse
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def handleInterrupts(query, config, state, input):
    try:
        logger.info("Handling interrupts")
        for task in state.tasks:
            # Checks if there are any interrupts or breakpoints in the earlier
            # call.
            if (
                task.name == "record_sales_node" or
                task.name == "human_record_sales_confirmation_node"
            ):
                input = None
                graph.update_state(config=config, values={
                    "question": query.query})
        logger.info("Interrupts handled successfully")
        return input
    except Exception as e:
        logger.error(f"Error handling interrupts: {e}")
        raise


if __name__ == "__main__":
    try:
        logger.info("Starting the application")
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        logger.error(f"Error starting the application: {e}")
        raise


#uvicorn quality_agent.main:app --host 0.0.0.0 --port 8000