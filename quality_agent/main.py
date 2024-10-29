from workflowManager import WorkflowManager
from fastapi import FastAPI, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from models.models import Query, QueryResponse
import getpass
import os
from langchain.globals import set_debug, set_verbose

if os.getenv("ENABLE_DEBUGGING") == "true":
    set_debug(True)
else:
    set_verbose(True)


def _set_if_undefined(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"Please provide your {var}")

    _set_if_undefined("OPENAI_API_KEY")


# for deployment on langgraph cloud
graph = WorkflowManager().generate_graph()

app = FastAPI()
origins = ["http://localhost:4200", "http://localhost:3005"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes -Begin


@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")


@app.post("/query")
async def runQuery(query: Query):
    response = []
    finalResponse = QueryResponse(answer='', chart='')
    # Todo: Get this thread_id from the UI.
    config = {"configurable": {"thread_id": "1"}, "recursion_limit": 100}
    for s in graph.stream(
        {"question": query.query},
        config
    ):
        if "__end__" not in s:
            response.append(s)
            node_response = s.get('inspection_node') or s.get(
                'documentation_node')
            visualization_response = s.get('visualization_node') or s.get('generate_mongo_query_node') or s.get('generate_chart_node')
            if (node_response):
                finalResponse.answer = node_response.get('answer')
            elif (visualization_response):
                finalResponse.chart = visualization_response.get('chart')

    return finalResponse


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
# Routes -End
