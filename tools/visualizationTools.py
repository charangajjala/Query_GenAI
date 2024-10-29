from langchain.agents import Tool
from quality_agent.plot_generator import generate_chart_based_on_query

visualizationTools =   [
    Tool(
        name="GenerateChartBasedOnQuery",
        func=generate_chart_based_on_query,
        description="""
        Generates a chart based on the user's query. The query can be related to mission statistics or defects in the data. Use this tool, if you fell that the user intents to visualize data.
        Args:
            user_query (str): The question or input provided by the user to generate the appropriate chart.
        Returns:
            str: A message indicating that the chart has been generated and saved.
        """
    )
]  