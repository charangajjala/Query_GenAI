from pymongo import MongoClient
from langchain.chains import LLMChain
from quality_agent.llmManager import LLMManager
from datetime import datetime
from prompts.inspectionPrompt import get_sample_analytics_mongodb_prompt, query_examples, get_fetch_collections_prompt,get_fetch_sales_prompt, all_schemas, sales_schema, sale_query_examples
from quality_agent.logger import setup_logger
import re
import os
import json
from bson.decimal128 import Decimal128
from dotenv import load_dotenv

load_dotenv()

logger = setup_logger(__name__)

client = MongoClient(os.getenv('MONGODB_CONNECTION_STRING'))
db = client[os.getenv('MONGODB_DATABASE_NAME')]
sales_db = client[os.getenv('MONGODB_SALES_DATABASE_NAME')]
# collection = db["movies"]
llm = LLMManager().llm


nosql_llm_chain = LLMChain(
    llm=llm, prompt=get_sample_analytics_mongodb_prompt(), verbose=True)

fetch_collections_llm_chain = LLMChain(llm=llm, prompt=get_fetch_collections_prompt(), verbose=True)

fetch_sales_llm_chain = LLMChain(llm=llm, prompt=get_fetch_sales_prompt(), verbose=True)


def iso_date_replacer(match):
    iso_date_str = match.group(1)
    # Convert the extracted string into a Python datetime object
    return f'datetime.fromisoformat("{iso_date_str[:-1]}")'

def convert_decimal128_to_float(record):
    """
    Recursively converts Decimal128 fields in a MongoDB record to float.
    """
    if isinstance(record, list):
        # Process each element if it's a list
        return [convert_decimal128_to_float(item) for item in record]
    elif isinstance(record, dict):
        # Process each key-value pair if it's a dictionary
        return {
            key: convert_decimal128_to_float(value)
            for key, value in record.items()
        }
    elif isinstance(record, Decimal128):
        # Convert Decimal128 to a float
        return float(record.to_decimal())
    else:
        # Return other types as-is
        return record

def get_sales_data(query):
    try:
        logger.info(f"Executing query: {query}")
        response = fetch_sales_llm_chain.invoke(
            {
                "user_question": query,
                "collection_schema": sales_schema,
                **sale_query_examples
            })
        iso_date_pattern = re.compile(r'ISODate\("([^"]+)"\)')
        query_modified = re.sub(
            iso_date_pattern, iso_date_replacer, response['text'])
        query_modified = query_modified.replace('null', 'None').replace(
            '```json', '').replace('```', '').replace('\n', '')
        
        logger.info(f"Query generated: {query_modified}")

        try:
            # Safely parse the modified query string
            pipeline = eval(query_modified)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Query: {query_modified}")
            pipeline = json.loads(query_modified)

        logger.info(f"Query generated: {pipeline}")
        # pipeline.append({
        #     "$project": {"audit": 0}
        # })

        collection = sales_db["sales"]
        results = collection.aggregate(pipeline)
        documents = []
        for doc in results:
            documents.append(doc)
        converted_records = [
        convert_decimal128_to_float(record) for record in documents
    ]
        return converted_records
    except Exception as e:
        logger.error(f"Error retrieving msales data: {e}")
        raise

def get_analytics_data(query):
    try:
        logger.info(f"Executing query: {query}")

        logger.info("Fetching collections")

        response = fetch_collections_llm_chain.invoke({'user_question': query})

        logger.info(f"Selected Collections: {response['text']}")

        selected_collections = json.loads(response['text'])

        if not selected_collections:
            collection_schemas = all_schemas
        else:
            collection_schemas = {collection_name: all_schemas[collection_name] for collection_name in selected_collections}

        collection_schemas = '\n'.join([f"{collection_name}: {schema}" for collection_name, schema in collection_schemas.items()])

        response = nosql_llm_chain.invoke(
            {
                "user_question": query,
                "collection_schemas": collection_schemas,
                **query_examples
            })
                
                
        response = response['text'].replace(
            '```json', '').replace('```', '').replace('\n', '')
        
        logger.info(f"Final Response: {response}")

        response = json.loads(response)

        base_collection = response['base_collection']

        pipeline = str(response['pipeline'])

        iso_date_pattern = re.compile(r'ISODate\("([^"]+)"\)')
        query_modified = re.sub(
            iso_date_pattern, iso_date_replacer, pipeline)
        query_modified = query_modified.replace('null', 'None').replace(
            '```json', '').replace('```', '').replace('\n', '')
        try:
            # Safely parse the modified query string
            pipeline = eval(query_modified)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Query: {query_modified}")
            pipeline = json.loads(query_modified)

        logger.info(f"Final Query generated: {pipeline}")
        pipeline.append({
            "$project": {"audit": 0}
        })

        collection = db[base_collection]
        logger.info(f"Executing pipeline...")
        results = collection.aggregate(pipeline)
        documents = []
        for doc in results:
            documents.append(doc)
        return documents
    except Exception as e:
        logger.error(f"Error retrieving analytics data: {e}")
        raise
