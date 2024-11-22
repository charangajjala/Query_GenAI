from datetime import date
from langchain.agents import Tool
from quality_agent.mongo_data_retriever import get_analytics_data, get_sales_data
from quality_agent.logger import setup_logger

logger = setup_logger(__name__)


def get_no_context_response(self):
    try:
        logger.info("Generating no context response")
        return "I cannot answer your question as I don't have the context"
    except Exception as e:
        logger.error(f"Error generating no context response: {e}")
        raise




inspectionTools = [
    # Tool(
    #     name="GetAnalyticsData",
    #     func=get_analytics_data,
    #     description="""
    #     Get details about financial servives like customers, accounts, or transactions. Call this tool if it's about the financial database.
    #     Args:
    #         query (str): The user input to send. Accepts user input directly without modification.
    #     Returns:
    #         list: List of records
    #     """
    # ),
        Tool(
        name="GetSalesData",
        func=get_sales_data,
        description="""
        Get details about sales related data like transaction data, including items purchased, customer information, store location, and purchase details. Call this tool if it's about the sales and supplies.
        Args:
            query (str): The user input to send. Accepts user input directly without modification.
        Returns:
            list: List of records
        """
    ),
   
    # Tool(
    #     name="NotAbleToParse",
    #     func=get_no_context_response,
    #     description="Fallback tool for unrecognized queries or hallucinated responses."
    # )
]
