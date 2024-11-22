from pydantic import BaseModel
from typing import Literal


class RouteResponse(BaseModel):
    content: Literal["Documentation", "Inspection",
                     "Visualization", "Schedule", "Review", "Help"]
