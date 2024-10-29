from datetime import date
from langchain.agents import Tool
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field, model_validator
from services.data_service import getAllMissionImages, getSpots, getLastMission, getMissionStatisticsBetweenDates, getMissionStatisticsByDuration, getDefectImage, getMissionReport
from quality_agent.mongo_missions_retriever import get_missions_and_defects


def get_spot_status(parameter1= ""):
    spots = getSpots()
    result = {
        "spot_name": spots[0]['assetName'],
        "spot_status": spots[0]['status'],
        "spot_battery_level": spots[0]['batteryLevel']
    }
    return result

def get_no_context_response(self):
    return "I cannot answer your question as I dont have the context"

class TimeStamp(BaseModel):
    fromDate: date = Field()
    toDate: date =Field()
    pass

class TimeStampInStrings(BaseModel):
    fromDate: str = Field(None, description="From date in YYYY-MM-DD format")
    toDate: str = Field(None, description="To date in YYYY-MM-DD format")
    pass

class TimeStampSchema(BaseModel):
    fromDate: str = Field(description="From date in YYYY-MM-DD format")
    toDate: str = Field(description="To date in YYYY-MM-DD format")

    @model_validator(mode = "before")
    def check_either_dates(cls, values):
        fromDate = values.get('fromDate')
        toDate = values.get('toDate')
        if not (fromDate and toDate):
            raise ValueError('FromDate and toDate must be provided')
        return {"fromDate": fromDate, "toDate": toDate}

class DurationSchema(BaseModel):
    durationInHours: int = Field(None, description="Duration in hours")

    @model_validator(mode = "before")
    def check_duration(cls, values):
        durationInHours = values.get('durationInHours')
        if not durationInHours:
            raise ValueError('durationInHours must be provided')
        return values

class TimeStampOrDurationSchema(BaseModel):
    fromDate: str = Field(None, description="From date in YYYY-MM-DD format")
    toDate: str = Field(None, description="To date in YYYY-MM-DD format")
    durationInHours: int = Field(None, description="Duration in hours")

    @model_validator(mode = "before")
    def check_either_dates_or_duration(cls, values):
        fromDate, toDate, durationInHours = values.get('fromDate'), values.get('toDate'), values.get('durationInHours')
        if not ((fromDate and toDate) or durationInHours):
            raise ValueError('Either fromDate and toDate or durationInHours must be provided')
        return values

class DefectSchema(BaseModel):
    missionId: str = Field(description="The id of the mission.")
    filePath: str = Field(description="The name of the image with extension where the defect is. If you have filePath, consider using it as filePath")

    @model_validator(mode = "before")
    def check(cls, values):
        missionId, filePath = values.get('missionId'), values.get('filePath')
        if not ((missionId and filePath)):
            raise ValueError('Both missionId and filePath must be provided')
        return values

inspectionTools = [
    # Mission Tools
    Tool(
        name="GetMissionsAndDefects",
        func=get_missions_and_defects,
        description="""
        Get missions, defects, images, assets, inspection coverage. Call this tool if its about the missions.
        Args:
            query (str): The user input to send. Accepts user input directly without modification.
        Returns:
            list: List of records
        """
    ),
    Tool(
        name="LastMission",
        func=getLastMission,
        description="Retrieve the details of the last mission (e.g., defects, images, status)."
    ),
     StructuredTool(
        name="ShowDefect",
        func=getDefectImage,
        description="""
         Displays/Shows the single image of the defect from the mission.
        Args:
            missionId (str): The id of the mission.
            filePath (str): The name of the image with extension where the defect is. If you have filePath, consider using it as filePath
        Returns:
            list: List of image details and its url""",
        args_schema=DefectSchema,
    ),
    Tool(
        name="ShowAllMissionImages",
        func=getAllMissionImages,
        description="""
         Displays/Shows all the images of the defects from a mission.
        Args:
            missionId (str): The id of the mission.
        Returns:
            list: List of image details and their urls""",
    ),
    # Spot Tools
    Tool(
        name="SPOTS",
        func=getSpots,
        description="Retrieve the list of spots available, along with their count and battery information."
    ),
    Tool(
        name="SPOTStatus",
        func=get_spot_status,
        description="Retrieve the status or battery level of spot robots."
    ),
    
    # Fallback
    Tool(
        name="NotAbleToParse",
        func=get_no_context_response,
        description="Fallback tool for unrecognized queries or hallucinated responses."
    ) 
]