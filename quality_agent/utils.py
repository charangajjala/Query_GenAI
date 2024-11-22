from langchain_core.messages import HumanMessage
from quality_agent.logger import setup_logger

logger = setup_logger(__name__)


def agent_node(state, agent, name):
    try:
        logger.info(f"Invoking agent with state: {state} and name: {name}")
        result = agent.invoke(state)
        logger.info(f"Agent invoked successfully with result: {result}")
        return {
            "messages": [HumanMessage(content=result["messages"][-1].content, name=name)]
        }
    except Exception as e:
        logger.error(f"Error invoking agent: {e}")
        raise
