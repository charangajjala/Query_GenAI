import json
import matplotlib.pyplot as plt
from langchain.chains import LLMChain
from llmManager import LLMManager
from mongo_missions_retriever import get_missions_and_defects
from prompts.inspectionPrompt import collection_schema
from prompts.visualizationPrompt import create_query_generation_prompt, create_code_generation_prompt
import re
from langchain_core.tools import tool
llm = LLMManager().llm


def rephrase_user_query_for_visualization(state):
    """
    Rephrases the user's query for visualization purposes by generating a new query.
    Args:
        state (dict): A dictionary containing the user's original question under the key 'question'.
    Returns:
        dict: A dictionary containing the rephrased question under the key 'rephrasedQuestion'.
    """
    query_generation_prompt = create_query_generation_prompt()
    query_generation_chain = LLMChain(
        llm=llm, prompt=query_generation_prompt, verbose=True)

    new_user_query = query_generation_chain.invoke({
        "user_query": state['question'],
        "collection_schema": collection_schema
    })['text']

    print("Generated Query:", new_user_query)
    return {"rephrasedQuestion": new_user_query}


def generate_mongo_query(state):
    """
    Generates a MongoDB query based on the provided state and retrieves data.
    This function uses the `get_missions_and_defects` function to fetch data from MongoDB
    using the 'rephrasedQuestion' key from the provided state dictionary. It checks if 
    the retrieved data is empty and returns an appropriate message or the retrieved data.
    Args:
        state (dict): A dictionary containing the 'rephrasedQuestion' key used to generate the query.
    Returns:
        dict or str: A dictionary with the key 'mongoQueryResult' containing the retrieved data,
                     or a string message indicating no data was retrieved.
    """
    retrieved_data = get_missions_and_defects(state['rephrasedQuestion'])

    # Check if retrieved_data is empty
    if not retrieved_data:
        return {"mongoQueryResult": []}
    else:
        print("Retrieved Data:", retrieved_data)
    return {"mongoQueryResult": retrieved_data}


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

    retrieved_data = state['mongoQueryResult']
    # Extract relevant information from the data (e.g., column names, a sample record, and count)
    # Get the column names from the first document
    column_names = list(retrieved_data[0].keys())
    number_of_rows = len(retrieved_data)  # Count the number of rows/documents
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
        "user_query": state['question']
    })

    generated_code = re.sub(r'```python|```', '',
                            code_response['text']).strip()

    # Step 6: Display the generated code (optional for debugging)
    print("Generated Python Code:\n", generated_code, sep='')

    # Pass the data into the local context
    local_context = {"data": retrieved_data}

    try:
        # Execute the generated code to produce `fig`
        exec(generated_code, local_context, local_context)
        
        # Retrieve the plot if it exists
        final_response_plot = local_context.get('fig')
        if not final_response_plot:
            print("No plot was generated.")
            return {"chart": None}
        
        # Convert the plot to JSON
        chart_response = final_response_plot.to_json()
        # responseInJsonString = json.dumps(chart_response)
        print('Final response plot:', chart_response)
        return {"chart": chart_response}    

    except KeyError:
        print("No plot object named 'fig' was found in the generated code.")
        return {"chart": None}  

    except Exception as e:
        print(f"Error occurred while executing the generated code: {str(e)}")
        return {"chart": None}  
