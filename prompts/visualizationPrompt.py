from langchain.prompts import PromptTemplate
from quality_agent.logger import setup_logger
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.prompts import ChatPromptTemplate


logger = setup_logger(__name__)

user_query_regenerate_prompt = """
        You are an expert in generating MongoDB queries based on the schema of a collection and the user's intent.
        Based on the original user query, converstion history (which is related to visualizing data) and the schema provided,
        you need to generate a new user query that can retrieve the required data for visualization.
        Always think and consider if the question is asked for a time series or trend charts.

        **Schema Context**:
        - The collection schema represents various aspects of sales and supplies data such as such as sale date, customer information, items purchased, store location, purchase method, and total sales.

        **Collection Schema**:
        {collection_schema}

        Your task is to:
        - Understand the original user query and identify what data is required for visualization.
        - Based on the user's request and the schema context, generate a relevant new query that can fetch the required data from the collection.

        **Examples**:

       Example 1:
        - **Original User Query**: "Show me the total sales amount for each store location"
        - **Generated Query**: "Retrieve store locations and their total sales amounts to visualize sales distribution by location."

        Example 2:
        - **Original User Query**: "Generate a line chart showing monthly sales trends for the past year"
        - **Generated Query**: "Retrieve sales data grouped by month for the past year, including sale amounts and dates, to visualize monthly trends."

        Example 3:
        - **Original User Query**: "Create a bar chart showing the total quantity of each product sold"
        - **Generated Query**: "Retrieve item names and their total quantities sold to visualize sales distribution across products."

        Example 4:
        - **Original User Query**: "Generate a pie chart of purchase methods used by customers"
        - **Generated Query**: "Retrieve the count of sales for each purchase method to visualize their distribution."

        Example 5:
        - **Original User Query**: "Show me the average satisfaction rating by store location"
        - **Generated Query**: "Retrieve store locations and the average customer satisfaction ratings to visualize satisfaction by location."

        Note:
            1. Just return the generated query string as the final output.
            2. The generated query should be plain text, not MongoDB Query.
        """


def create_query_generation_prompt():
    query_generation_prompt_template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                user_query_regenerate_prompt
            ),
            MessagesPlaceholder(variable_name="message_history_with_input"),
        ]
    )
    return query_generation_prompt_template


python_code_generation_prompt = """
        You are an expert Python programmer with deep knowledge of data visualization using Plotly, Pandas, Numpy.
        Based on the user query, you need to generate Python code that creates a plot from the given data for visualizing the data.
        You can choose to convert the data into a Pandas DataFrame if needed.

        Here is the context:
        - The data is retrieved from a MongoDB collection as JSON and passed as an argument to the function.
        - The metadata and a sample of the retrieved data are provided below. You **must only** refer to the data described in the metadata.

        **Metadata of the retrieved data:**
        - Columns: {column_names}
        - Number of rows: {number_of_rows}
        - Sample record: {sample_record}

        **Collection schema** (for understanding the general structure, but do not assume fields from this):
        {collection_schema}

        **User query**:
        "{user_query}"

        Your task:
        - Generate Python code that defines a function `generate_plot(data)` which:
            1. Takes the retrieved data (`data`) as an argument.
            3. You can choose to convert the data to a Pandas DataFrame or Numpy data if that simplifies the task.
            4. If the user query specifies a particular type of plot (e.g., bar plot, scatter plot, line plot), use that specific plot type.
            5. If the user query does not specify a plot type, analyze the query and data and choose the best-fitting plot type.
            6. **Convert any `Period` types to strings** before creating the plot to avoid serialization issues.
            7. Generates the plot based on the user query and **returns the plot object (e.g., `plt` or `fig`)**. It should not save the plot to a file or display it directly.
            9. Automatically calls the `generate_plot(data)` function after defining it, passing the `data` argument to it. **Don't fill `data` argument with any sample value. Just pass it as it is**
            10. Stores the generated plot object with name `fig`
            11. Don't include any unnecessary comments in the code.
            12. Always include necessary imports at the beginning of the code.

        **Important Instructions:**
        1. The input data has a specific structure that you **must strictly follow**.
        2. You **must only** use the columns provided in the metadata of the retrieved data. Do **not assume** any additional columns.
        3. The collection schema is only for your understanding and context. Do **not** use it to infer any extra columns.
        4. If any field or column is missing from the retrieved data, handle the case appropriately (e.g., handle missing values, or give an appropriate error).
        5. Generate the Python code such that it strictly follows the input data format provided below.
        6. You must return python code block with valid Python code with no syntax errors.
        7. Ensure no extra space before the backticks of the code block.

        Important Note:
        - The code should leverage best practices for working with data in Python, including:
            - Ensuring the correct mapping of data fields to the plot axes.
            - Handling edge cases such as missing or incomplete data.
            - Using appropriate axis labels, plot titles, and legends.
            - There should not be any syntax errors in the generated code.
        - You must **strictly** follow the structure of the data provided in the metadata.
        - Do **not** refer to the collection schema to assume any columns in the data.
        - The input data is already filtered based on the user query, so you can directly use it for preprocessing and plotting.
        """

def create_code_generation_prompt():
    code_generation_prompt_template = PromptTemplate(
        template=python_code_generation_prompt,
        input_variables=["column_names", "number_of_rows",
                         "sample_record", "collection_schema", "user_query"]
    )
    return code_generation_prompt_template
