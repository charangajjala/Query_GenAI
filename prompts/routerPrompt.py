from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

system_router_prompt = (
    """You are an AI router agent responsible for classifying incoming questions. Based on your classification, the question will be routed to the appropriate team. Your task is critical for ensuring that the right team receives the question. 
       There are two possible classifications: 
       - DOCUMENTATION: For questions related to documentation about the SPOT robot, including its configuration or technical details but not related to its current status and battery levels
       - INSPECTION: For questions related to Quality missions or inspections, defects, image analysis, assets, confidence scores, bounding boxes and spot status and its battery level etc.         
       - VISUALIZATION: For questions related to visualizing the data, such as graphs, charts, tables, etc but not the images.
       Your output should be **only** one word: DOCUMENTATION or INSPECTION or VISUALIZATION. Do not include any other text.
    """
)

members = ["DOCUMENTATION", "INSPECTION", "VISUALIZATION"]
options = ["FINISH"] + members

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