from langchain_core.prompts import ChatPromptTemplate
from langchain.prompts import PromptTemplate
from datetime import datetime
from bson import json_util

missions_query_example1 = json_util.dumps([{"$match": {"status": "In Progress"}}, {
                                          "$match": {"$project": "missionPlanName"}}])
missions_query_example2 = json_util.dumps([{"$sort": {"updatedTimeStamp": -1}}, {
                                          "$limit": 1}, {"$project": {"images.boundingBoxes.label": 1, "_id": 0}}])
collection_schema = """
    1. **_id**: Unique identifier for the listing.
    2. **missionPlanName**: Name of the mission.
    3. **assetName**: Name of the asset or spot robot.
    4. **inspectionCoverage**: The area that the asset or spot robot covers.
    5. **status**: The status of the mission. Allowed statuses are Scheduled,Cancelled,In Progress,Failed,Aborted,Awaiting Review,In Review, Reviewed
    6. **scheduledTimeStamp**: The time when the mission is scheduled. This is in MongoDB date format.
    7. **updatedTimeStamp**: The time when the mission is updated or completed. This is in MongoDB date format.
    8. **noOfImages**: The number of images in the mission.
    9. **noOfDefects**: The number of defects in the mission.
    10. **missionType**: The type of mission i.e. Interior or Exterior.
    11. **carNo**: The car or train car number.
    12. **inProgressWayPoint**: The embedded object contains the waypoint where the mission is in progress. Contains the following properties:
        - **progress**: The progress of the mission.
        - **currentActionPoint**: The current action of the mission.
    13. **images**: Array of images in the mission that also contains the defects found in the image. Each image object contains the following properties:
        - **imageStatus**: The status of the image if reviewed or not.
        - **boundingBoxes**: Array of bounding boxes containing the following properties:
            - **label**: The name of the defect.
            - **confidence**: The confidence of the defect.
    14. **reason**: Reason for mission failure or reason for aborting the mission by the user.
    """
    
missions_mongodb_prompt = """You are a very intelligent AI assitasnt who is expert in identifying relevant questions
       from user and converting into nosql mongodb agggregation pipeline query. 
       Please use the below schema to write the mongodb queries , dont use any other queries.
    Schema:
       The mentioned mongodb collection talks about various quality inspections/missions in a factory. 
       The schema for this document represents the structure of the data, describing various properties related to the missions, inspections, defects, status, assets and inspection coverage. 
    Here is a breakdown of its schema with descriptions for each field:
    {collection_schema}
    Here are some examples:
        Input1: How many missions are in progress and provide their names
        Output1: {missions_query_example1} 
        
        Input2: Tell me the list of all the defects found in the last mission
        Output2: {missions_query_example2} 
    
    Input: {user_question}
    Today's date is {present_date}
    Previous conversation history: {missions_chat_history}
    Important Note:
    1. All dates must be in ISODate bson type and dont use '$date' in queries.
    2. You have to just return the query as to use in aggregation pipeline nothing else. Don't return any other thing.
    3. Always exclude or project the redundant fields in the query.
    """


def get_missions_mongodb_prompt():
    query_with_prompt_template = PromptTemplate(
        template=missions_mongodb_prompt,
        input_variables=["user_question", "missions_query_example1",
                         "missions_query_example2", "missions_chat_history", "collection_schema"]
    ).partial(present_date=datetime.now())
    return query_with_prompt_template


def get_inspection_prompt():
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
                You are a helpful assistant that takes the user input and decides to call a tool to answer the question.
                Format the final answer in markdown format such as title as header 2, paragraphs, bullet points, headers, tables, bold text etc as required based on the data. It must be in commonmark's markdown format.
                Today's date is {present_date}
                """,
            ),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(present_date=datetime.now())
    return prompt
