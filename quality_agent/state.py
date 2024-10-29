from typing import List, Any, Annotated, Dict, Optional, Sequence
from typing_extensions import TypedDict
import operator
from langgraph.prebuilt.chat_agent_executor import AgentState


class MultiAgentState(AgentState):
    messages: Annotated[Sequence[Any], operator.add]
    question: str
    question_type: str
    answer: str
    rephrasedQuestion: Optional[str]
    mongoQueryResult: Optional[list]
    chart: Optional[str]
