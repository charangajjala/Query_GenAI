from typing import Optional
from pydantic import BaseModel, Field


class Query(BaseModel):
    query: str = Field(..., example="Query for NLP")

class QueryResponse(BaseModel):
    answer: str = Field(..., example="Final answer for the user query")
    chart: str = Field(...,
                       example="Chart generated from the user query in json format")


class HelpResponse(BaseModel):
    help_text: str = Field(..., example="Detailed help text for the user")
