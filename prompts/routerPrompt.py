from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from quality_agent.logger import setup_logger
logger = setup_logger(__name__)

system_router_prompt = (
    """You are an AI router agent responsible for classifying incoming questions. Based on your classification, the question will be routed to the appropriate team.
       
        - Query_Data: For questions about fetching data related to **financial services, financial data, sales, supplies**, such as:
                    Transaction Details: Like sale date, the store locations, and the method of purchase etc.
                    Items Purchased:  Items bought during the sale, including the item name, category tags, price, and quantity.
                    Customer Information:  demographic and feedback data about the customer, such as gender, age, email, and satisfaction rating.

        - Visualization: For questions related to data visualization, like creating or analyzing plots, graphs, charts, and tables (not images). ** Not analysing/describing about plot/graphs/figures **
        - Analyze_Plot: For questions related to analyzing or describing plots, graphs, charts, and tables. ** Not creating or visualizing plots/graphs/figures **
        
        - Record_Sales: For questions about extracting sales data from bill/recipt image and recording/saving sales data to the database

        - Help: For questions related to requesting for help and guidance
        - NoContext: For questions that do not fit into any of the above categories.

                
        Your output should be **only** one of the words: Documentation, Inspection, Visualization, Schedule, Review, Help, or NoContext. 
        Do not include any other text. 

    """
)

members = [
    "Query_Info",
    "Visualization",
    "Schedule",
    "Record_Sale",
    "Analyze_Plot",
    "Help",
    "NoContext",
]

options = [] + members


def get_router_prompt():
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_router_prompt),
            MessagesPlaceholder(variable_name="question"),
            (
                "system",
                "Given the conversation above, who should act next?"
                " Or should we FINISH? Select one of: {options}",
            ),
        ]
    ).partial(options=str(options), members=", ".join(members))
    return prompt

# def get_router_prompt():
#     router_with_prompt_template = PromptTemplate(
#         template=system_router_prompt,
#         input_variables=["question", "router_chat_history"]
#     ).partial()
#     return router_with_prompt_template

# def get_router_prompt():
#     prompt = ChatPromptTemplate.from_messages(
#         [
#              ("user", "{question}"),
#             ("assistant", system_router_prompt),
           
#             # (
#             #     "assistant",
#             #     "Given the conversation above, who should act next?"
#             #     " Or should we FINISH? Select one of: {options}",
#             # ),
#         ]
#         ).partial(options=str(options), members=", ".join(members))
#     return prompt
