import json
import matplotlib.pyplot as plt
from langchain.chains import LLMChain
from llmManager import LLMManager
from quality_agent.mongo_data_retriever import get_sales_data
from prompts.inspectionPrompt import sales_schema as collection_schema
from prompts.visualizationPrompt import create_query_generation_prompt, create_code_generation_prompt
from langchain_core.tools import tool
from quality_agent.logger import setup_logger
import re
import base64
from io import BytesIO
from langchain_core.messages import  AIMessage

logger = setup_logger(__name__)

llm = LLMManager().llm
vision_llm = LLMManager().vision_llm


def rephrase_user_query_for_visualization(state):
    """
    Rephrases the user's query for visualization purposes by generating a new query.
    Args:
        state (dict): A dictionary containing the user's original question under the key 'question'.
    Returns:
        dict: A dictionary containing the rephrased question under the key 'rephrasedQuestion'.
    """
    try:
        query_generation_prompt = create_query_generation_prompt()
        query_generation_chain = query_generation_prompt | llm

        new_user_query = query_generation_chain.invoke({
           "message_history_with_input": state['messages'],
            "collection_schema": collection_schema
        })

        logger.info(f"Rephrased Question: {new_user_query.content}")

        return {"rephrasedQuestion": new_user_query.content}
    except Exception as e:
        logger.error(f"Error rephrasing user query for visualization: {e}")
        raise


def generate_mongo_query(state):
    """
    Generates a MongoDB query based on the provided state and retrieves data.
    This function uses the `get_sales_data` function to fetch data from MongoDB
    using the 'rephrasedQuestion' key from the provided state dictionary. It checks if
    the retrieved data is empty and returns an appropriate message or the retrieved data.
    Args:
        state (dict): A dictionary containing the 'rephrasedQuestion' key used to generate the query.
    Returns:
        dict or str: A dictionary with the key 'mongoQueryResult' containing the retrieved data,
                     or a string message indicating no data was retrieved.
    """
    try:
        retrieved_data = get_sales_data(state['rephrasedQuestion'])

        # Check if retrieved_data is empty
        if not retrieved_data:
            return {"mongoQueryResult": []}
        else:
            logger.info(f"Retrieved Data: {retrieved_data}")
        return {"mongoQueryResult": retrieved_data}
    except Exception as e:
        logger.error(f"Error generating MongoDB query: {e}")
        raise


def generate_chart_based_on_query(state):
    """
    Generates a chart based on the provided query state.
    This function retrieves data from the state, extracts relevant information,
    generates Python code for plotting using a language model, and executes the
    generated code to produce a plot.
    Args:
        state (dict): A dictionary containing the following keys:
            - 'mongoQueryResult': The result of a MongoDB query, expected to be a list of documents.
            - 'question': The user's query or question that guides the chart generation.
    Returns:
        dict or str: A dictionary containing the generated chart in JSON format if successful,
                     or an error message string if an error occurs during code execution.
    """
    try:
        retrieved_data = state['mongoQueryResult']
        # Extract relevant information from the data (e.g., column names, a sample record, and count)
        # Get the column names from the first document
        column_names = list(retrieved_data[0].keys())
        # Count the number of rows/documents
        number_of_rows = len(retrieved_data)
        id = "_id"
        for record in retrieved_data:
            for key in record:
                if key == id:
                    record[key] = str(record[key])
        sample_record = retrieved_data[0]  # Show the full sample record
        code_generation_prompt = create_code_generation_prompt()
        code_generation_chain = LLMChain(
            llm=llm, prompt=code_generation_prompt, verbose=True)

        # Use the LLM chain to generate Python code for plotting
        code_response = code_generation_chain.invoke({
            "column_names": column_names,
            "number_of_rows": number_of_rows,
            "sample_record": sample_record,
            "collection_schema": collection_schema,
            "user_query": state['rephrasedQuestion']
        })

        generated_code = re.sub(r'```python|```', '',
                                code_response['text']).strip()

        # Step 6: Display the generated code (optional for debugging)
        logger.info(f"Generated Python Code:\n{generated_code}")

        # Pass the data into the local context
        local_context = {"data": retrieved_data}

        try:
            # Execute the generated code to produce `fig`
            exec(generated_code, local_context, local_context)

            # Retrieve the plot if it exists
            final_response_plot = local_context.get('fig')
            if not final_response_plot:
                logger.error("No plot was generated.")
                return {"chart": None}
            
            final_response_plot.show()


            # Convert the plot to JSON
            chart_response = final_response_plot.to_json()
            logger.info(f'Final response plot: {chart_response}')
            ai_msg = "The requested plot has been generated successfully."

            return {"chart": chart_response, "answer": ai_msg, "messages":[AIMessage(ai_msg)]}

        except KeyError as e:
            logger.error(
                "No plot object named 'fig' was found in the generated code.")
            return {"chart": None}

        except Exception as e:
            logger.error(
                f"Error occurred while executing the generated code: {str(e)}")
            return {"chart": None}

    except Exception as e:
        logger.error(f"Error generating chart based on query: {e}")
        raise
