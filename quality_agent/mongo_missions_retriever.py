from pymongo import MongoClient
from langchain.chains import LLMChain
from llmManager import LLMManager
from langchain.memory import ConversationSummaryMemory
# dont delete this datetime import as it is used in the eval function
from datetime import datetime
import re
import os
import json
from prompts.inspectionPrompt import get_missions_mongodb_prompt, missions_query_example1, missions_query_example2, collection_schema

client = MongoClient(os.getenv('MONGODB_CONNECTION_STRING'))
db = client[os.getenv('MONGODB_DATABASE_NAME')]
collection = db["missions"]
llm = LLMManager().llm
memory = ConversationSummaryMemory(
    llm=llm, input_key="user_question", memory_key="missions_chat_history")

nosql_llm_chain = LLMChain(
    llm=llm, prompt=get_missions_mongodb_prompt(), verbose=True, memory=memory)


def iso_date_replacer(match):
    iso_date_str = match.group(1)
    # Convert the extracted string into a Python datetime object
    return f'datetime.fromisoformat("{iso_date_str[:-1]}")'


def get_missions_and_defects(query):
    response = nosql_llm_chain.invoke(
        {
            "user_question": query,
            "missions_query_example1": missions_query_example1,
            "missions_query_example2": missions_query_example2,
            "collection_schema": collection_schema
        })
    iso_date_pattern = re.compile(r'ISODate\("([^"]+)"\)')
    query_modified = re.sub(
        iso_date_pattern, iso_date_replacer, response['text'])
    query_modified = query_modified.replace('null', 'None').replace(
        '```json', '').replace('```', '').replace('\n', '')
    try:
        # Safely parse the modified query string
        pipeline = eval(query_modified)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(query_modified)
        pipeline = json.loads(query_modified)

    print("Query generated: ", pipeline)
    pipeline.append({
        "$project": {"audit": 0}
    })
    results = collection.aggregate(pipeline)
    documents = []
    for doc in results:
        documents.append(doc)
    return documents
