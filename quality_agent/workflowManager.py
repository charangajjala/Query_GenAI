from langgraph.graph import StateGraph
from state import MultiAgentState
from llmManager import LLMManager
from pydantic import BaseModel
from typing import Literal
from langgraph.graph import END, StateGraph
from langchain_core.messages import HumanMessage
from langchain_core.runnables.graph import MermaidDrawMethod
from tools.documentationTools import documentationTools
from tools.inspectionTools import inspectionTools
from langchain.agents import AgentExecutor, create_tool_calling_agent
from prompts.routerPrompt import get_router_prompt
from prompts.inspectionPrompt import get_inspection_prompt
from langgraph.checkpoint.memory import MemorySaver
from plot_generator import rephrase_user_query_for_visualization, generate_mongo_query, generate_chart_based_on_query


class routeResponse(BaseModel):
    content: Literal["FINISH", "DOCUMENTATION", "INSPECTION", "VISUALIZATION"]


llm = LLMManager().llm


def router_agent(state: MultiAgentState):
    supervisor_chain = get_router_prompt() | llm.with_structured_output(routeResponse)
    messages = [HumanMessage(state['question'])]
    response = supervisor_chain.invoke(messages)
    print("Routing to ", response.content)
    return {"question_type": response.content, 'messages': messages}


def documentation_node(state: MultiAgentState):
    llm_with_tools = llm.bind_tools(documentationTools)
    messages = [HumanMessage(state['question'])]
    ai_msg = llm_with_tools.invoke(messages)
    messages.append(ai_msg)
    for tool_call in ai_msg.tool_calls:
        selected_tool = {tool.name: tool for tool in documentationTools}[
            tool_call["name"]]
        tool_msg = selected_tool.invoke(tool_call)
        messages.append(tool_msg)
    return {'answer': messages[2].content}


inspectionAgent = create_tool_calling_agent(
    llm=llm,
    prompt=get_inspection_prompt(),
    tools=inspectionTools,
)
inspection_agent_executor = AgentExecutor(
    agent=inspectionAgent,
    tools=inspectionTools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=10,
    return_intermediate_steps=False).with_config({"run_name": "Agent"})


def inspection_node(state: MultiAgentState):
    response = inspection_agent_executor.invoke(
        {"input": [HumanMessage(state['question'])]})
    return {'answer': response["output"]}


def route_question(state: MultiAgentState):
    return state['question_type']


class WorkflowManager:
    def __init__(self):
        self.llm = LLMManager()

    def create_workflow(self) -> StateGraph:
        """Create and configure the workflow graph."""
        workflow = StateGraph(MultiAgentState)
        workflow.add_node("router_node", router_agent)
        workflow.set_entry_point("router_node")
        workflow.add_node("documentation_node", documentation_node)
        workflow.add_node("inspection_node", inspection_node)
        workflow.add_node("visualization_node",
                          rephrase_user_query_for_visualization)
        workflow.add_node("generate_mongo_query_node", generate_mongo_query)
        workflow.add_node("generate_chart_node", generate_chart_based_on_query)

        workflow.add_conditional_edges(
            "router_node",
            route_question,
            {
                'DOCUMENTATION': 'documentation_node',
                'INSPECTION': 'inspection_node',
                'VISUALIZATION': 'visualization_node',
            }
        )

        workflow.add_edge("documentation_node", END)
        workflow.add_edge("inspection_node", END)
        workflow.add_edge("visualization_node", "generate_mongo_query_node")
        workflow.add_edge("generate_mongo_query_node", "generate_chart_node")
        workflow.add_edge("generate_chart_node", END)

        return workflow

    def generate_graph(self):
        """Run the workflow."""
        memory = MemorySaver()
        graph = self.create_workflow().compile(checkpointer=memory)
        graph.name = "AQI Graph"
        # Draw the graph and get the bytes
        image_bytes = graph.get_graph().draw_mermaid_png(
            draw_method=MermaidDrawMethod.API,
        )

        # Save the bytes to an image file
        with open("workflow_graph.png", "wb") as image_file:
            image_file.write(image_bytes)
        return graph
