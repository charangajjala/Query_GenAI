from typing import Literal
from langgraph.graph import StateGraph, END
from quality_agent.state import MultiAgentState
from quality_agent.llmManager import LLMManager
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables.graph import MermaidDrawMethod
from tools.inspectionTools import inspectionTools
from langchain.agents import AgentExecutor, create_tool_calling_agent
from prompts.routerPrompt import get_router_prompt
from prompts.inspectionPrompt import get_inspection_prompt
from prompts.actionsPrompt import get_schedule_prompt
from langgraph.checkpoint.memory import MemorySaver
from quality_agent.plot_generator import rephrase_user_query_for_visualization, generate_mongo_query, generate_chart_based_on_query
from langgraph.errors import NodeInterrupt
from dateutil.parser import isoparse
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from quality_agent.logger import setup_logger
import os
import ntpath
import json
from pymongo import MongoClient
import base64
import plotly.io as pio
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()


logger = setup_logger(__name__)

store = {}

client = MongoClient(os.getenv('MONGODB_CONNECTION_STRING'))
db = client[os.getenv('MONGODB_DATABASE_NAME')]
sales_db = client[os.getenv('MONGODB_SALES_DATABASE_NAME')]

class WorkflowManager:
    def __init__(self, llm_manager: LLMManager):
        try:
            logger.info("Initializing WorkflowManager")
            self.llm_manager = llm_manager
            self.llm = llm_manager.llm
            self.vision_llm = llm_manager.vision_llm
            self.llm_for_router = llm_manager.llm_for_router
            logger.info("WorkflowManager initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing WorkflowManager: {e}")
            raise

    def router_agent(self, state: MultiAgentState):
        try:
            logger.info(f"Routing question: {state['question']}")
            supervisor_chain = get_router_prompt() | self.llm_for_router
            messages = state['messages']

            human_msg = HumanMessage(state['question'])
            # print('human_msg', human_msg, type(human_msg))
            messages = messages + [human_msg]
            # logger.info(f"Input to router agent: {messages}")

            response = supervisor_chain.invoke({"question": messages})

            # Check if the response was filtered
            if 'content_filter_result' in response:
                logger.warning(
                    "The response was filtered due to content management policy.")
                return {"question_type": "Error", 'messages': human_msg }

            logger.info(f"Routing to: {response.content}")
            return {"question_type": response.content, 'messages': [human_msg]}
        except Exception as e:
            logger.error(f"Error in router_agent: {e}")
            raise

    def get_session_history(session_id: str) -> BaseChatMessageHistory:
        if session_id not in store:
            store[session_id] = ChatMessageHistory()
        return store[session_id]

    def query_data_node(self, state: MultiAgentState):
        try:
            logger.info(
                f"Processing inspection node for question: {state['question']}")
            inspectionAgent = create_tool_calling_agent(
                llm=self.llm,
                prompt=get_inspection_prompt(inspectionTools),
                tools=inspectionTools,
            )
            inspection_agent_executor = AgentExecutor(
                agent=inspectionAgent,
                tools=inspectionTools,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=10,
                return_intermediate_steps=False)
            
            logger.info(f"Input to agent executor: {state['question']}")

            response = inspection_agent_executor.invoke(
                {"message_history_with_input": state['messages']})
            
            ai_msg = AIMessage(response["output"])

            return {'answer': response["output"], 'messages':[ai_msg]}
        except Exception as e:
            logger.error(f"Error in inspection_node: {e}")
            raise

    def record_sales_node(self, state: MultiAgentState):
        try:
            logger.info(
                f"Processing sales recording for question: {state['question']}")
            if state['question'].lower() == "cancel":
                return {"answer": "Sales Recording process has been cancelled."}
            

            extractor_chain = get_schedule_prompt() | self.vision_llm

            # Path to the PNG image
            image_path = "bill_receipt.png"

            # Read and encode the image to Base64
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode("utf-8")


            messages = [
                HumanMessage(
                    content=[
                        {"type": "text", "text": "Extract information from this receipt image..."},
                        {
                            "type": "image_url",
                            "image_url": f"data:image/png;base64,{image_data}",
                        },
                    ]
                )
            ]

            logger.info(f"Extracting information from receipt image...")
            response = extractor_chain.invoke(messages)

            response = response.content.replace(
            '```json', '').replace('```', '').replace('\n', '')
            
            logger.info(f"Response from schedule node: {response}")


            return {"newSale": response, "answer": "Do you want to save the sales records with the following details? \n\n" + response}
        except Exception as e:
            logger.error(f"Error in record_sales_node: {e}")
            raise

    def analyze_plot_node(self, state: MultiAgentState):
        try:
            logger.info(
                f"Processing analyze plot node for question: {state['question']}")
            

            logger.info(f'Converting the plotly object from JSON ...')
            
            # Assuming `state['chart']` contains the Plotly figure JSON
            fig = pio.from_json(state['chart'])
            
            chart_json=fig
            return {
            "chart": chart_json,  # Send chart JSON directly
            "answer": "The requested plot has been generated successfully.",
           }

            # # Optimize for lower quality and faster processing
            # pio.kaleido.scope.default_width = 400  # Reduce width
            # pio.kaleido.scope.default_height = 300  # Reduce height
            # pio.kaleido.scope.default_scale = 0.5  # Reduce scale for less quality

            # logger.info(f'Converting the plotly object to a low-quality PNG ...')
            # # Convert Plotly figure to a low-quality PNG and encode to Base64
            # img_bytes = fig.to_image(format="png", engine="kaleido")

            # logger.info(f'Encoding the plot image to Base64 ...')


            # plot_base64 = base64.b64encode(img_bytes).decode("utf-8")
            

            def plotly_to_base64(fig, buffer=None):
                if buffer is None:
                    buffer = BytesIO()  # Create buffer only if not provided
                buffer.truncate(0)  # Clear existing buffer
                buffer.seek(0)
                logger.info(f'Writing the plot image to buffer png ...')
                fig.write_image(buffer, format="png")  # Render the figure to buffer
                encoded_string = base64.b64encode(buffer.getvalue()).decode("utf-8")  # Base64 encode directly
                return encoded_string
            
            logger.info(f'Encoding the plot image to Base64 ...')

            # Convert Plotly figure to a low-quality PNG and encode to Base64
            plot_base64 = plotly_to_base64(fig)

            human_msg = HumanMessage(
                    content=[
                        {"type": "text", "text": "Based on the provided image and the previous conservations, give answer"},
                        {
                            "type": "image_url",
                            "image_url": f"data:image/png;base64,{plot_base64}",
                        },
                    ]
                )

            messages = state['messages'] +  [human_msg]

            logger.info(f"Analyzing the plot image...")

            response = self.llm.invoke(messages)
            
            return {"answer": response.content}
        except Exception as e:
            logger.error(f"Error in anlyze_plot_node: {e}")
            raise

    def human_record_sales_confirmation_node(self, state: MultiAgentState):
        try:
            logger.info(
                f"Processing human confirmation node for question: {state['question']}")
            if state['question'].lower(
            ) == "cancel" or state['question'].lower() != "yes":
                return {"answer": "Sales Recording process has been cancelled."}


            sale_document = state['newSale']
            sale_document = json.loads(sale_document)
            document = sales_db["sales"].insert_one(sale_document)
            if document is None:
                return {"answer": "Failed to save the sales records. Please try again."}


            return {"answer": f"The sales transactions are recorded successfully with document id", "newSale": None}
        except Exception as e:
            logger.error(
                f"Error in human confirmation node: {e}")
            raise

 
    def help_node(self, state: MultiAgentState):
        try:
            logger.info("Processing help node")
            docs_path = os.path.join(
                os.path.dirname(__file__),
                '..',
                'docs',
                'help_content.md')
            with open(docs_path, "r", encoding="utf-8") as file:
                help_text = file.read()
            return {"answer": help_text}
        except FileNotFoundError:
            logger.error("Help documentation file not found")
            return {
                "answer": "Error: Help documentation file not found. Please ensure the docs/help_content.md file exists."}
        except Exception as e:
            logger.error(f"Error reading help documentation: {e}")
            return {"answer": f"Error reading help documentation: {str(e)}"}

    def no_context_node(self, state: MultiAgentState):
        logger.info("Processing no context node")
        return {"answer": "I'm sorry, I don't understand the question. Please provide more context or rephrase your question."}

    def route_question(self, state: MultiAgentState):
        try:
            logger.info(f"Routing question: {state['question_type']}")
            return state['question_type']
        except Exception as e:
            logger.error(f"Error in route_question: {e}")
            raise

    def create_workflow(self) -> StateGraph:
        try:
            logger.info("Creating workflow graph")
            workflow = StateGraph(MultiAgentState)
            workflow.add_node("router_node", self.router_agent)
            workflow.set_entry_point("router_node")
            workflow.add_node("query_data_node", self.query_data_node)
            # workflow.add_node("analyze_plot_node", self.analyze_plot_node)
            workflow.add_node(
                "visualization_node",
                rephrase_user_query_for_visualization)
            # workflow.add_node(
            #     "record_sales_node",
            #     self.record_sales_node)
            # workflow.add_node(
            #     "human_record_sales_confirmation_node",
            #     self.human_record_sales_confirmation_node)
            workflow.add_node(
                "generate_mongo_query_node",
                generate_mongo_query)
            workflow.add_node(
                "generate_chart_node",
                generate_chart_based_on_query)
           
            workflow.add_node("help_node", self.help_node)
            workflow.add_node("no_context_node", self.no_context_node)

            workflow.add_conditional_edges(
                "router_node",
                self.route_question,
                {
                  
                    'Visualization': 'visualization_node',
                    'Query_Data': 'query_data_node',
                    # 'Record_Sales': 'record_sales_node',
                    'Help': 'help_node',
                    'NoContext': 'no_context_node',
                    # 'Analyze_Plot': 'analyze_plot_node'
                }
            )

            workflow.add_edge("query_data_node", END)
            # workflow.add_edge(
            #     "record_sales_node",
            #     'human_record_sales_confirmation_node')
            # workflow.add_edge("human_record_sales_confirmation_node", END)
            workflow.add_edge(
                "visualization_node",
                "generate_mongo_query_node")
            workflow.add_edge(
                "generate_mongo_query_node",
                "generate_chart_node")
            workflow.add_edge("generate_chart_node", END)
            # workflow.add_edge("analyze_plot_node", END)
            workflow.add_edge("help_node", END)
            workflow.add_edge("no_context_node", END)

            logger.info("Workflow graph created successfully")
            return workflow
        except Exception as e:
            logger.error(f"Error creating workflow graph: {e}")
            raise

    def generate_graph(self):
        try:
            logger.info("Generating workflow graph")
            memory = MemorySaver()
            enableDebugging = os.getenv("ENABLE_DEBUGGING") == "true"
            graph = self.create_workflow().compile(checkpointer=memory, debug=enableDebugging,
                                                   )
            graph.name = "Text to NoSQL Agent Graph"
            # Draw the graph and get the bytes
            image_bytes = graph.get_graph().draw_mermaid_png(
                draw_method=MermaidDrawMethod.API,
            )

            # Save the bytes to an image file
            with open("workflow_graph.png", "wb") as image_file:
                image_file.write(image_bytes)
            logger.info("Workflow graph generated successfully")
            return graph
        except Exception as e:
            logger.error(f"Error generating workflow graph: {e}")
            raise
