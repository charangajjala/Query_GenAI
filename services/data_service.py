from datetime import datetime, timedelta
import os
import json
import requests
from dotenv import load_dotenv
import urllib

load_dotenv()
SUBSCRIPTION_KEY = os.getenv('API_SUBSCRIPTION_KEY')
AQI_API_URL = os.getenv('AQI_API_URL')
# Path to the token cache file
CACHE_FILE_PATH = 'token_cache.json'

# Function to save the token cache to file
def save_cache(token_cache):
    with open(CACHE_FILE_PATH, 'w') as cache_file:
        cache_file.write(token_cache.serialize())

def getSpots(par1= ""):
    headers = fetchHeaders()
    url = f'{AQI_API_URL}/assets'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()

def getMissionPlans(par1= ""):
    headers = fetchHeaders()
    url = f'{AQI_API_URL}/missionPlans?skip=0&limit=1000'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()

def getMissionPlanByName(missionPlanName):
    missionPlan = getMissionPlans()
    for plan in missionPlan['missionPlans']:
        if plan['name'] == missionPlanName:
            return plan
        
def getDefects(par1= ""):
    headers = fetchHeaders()
    url = f'{AQI_API_URL}/defects'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()

def getMissionsBetweenDates(dates):
    fromDate, toDate = dates.split(',')
    if not (fromDate and toDate):
            return "Unable to answer. Please correct your question and pass both the from and to timestamps."
    fromDate = fromDate.strip()
    toDate = toDate.strip()
    headers = fetchHeaders()
    url = f'{AQI_API_URL}/missions?from={fromDate}&to={toDate}&skip=0&limit=100'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        missions = result['missions']
        for mission in missions:
            mission['audits'] = None
        return result
    else:
        response.raise_for_status()

def getMissionsByDuration(durationInHours):
    durationInHours = convert_to_int_if_string(durationInHours)
    headers = fetchHeaders()
    toDate = datetime.now()
    fromDate = toDate - timedelta(hours=durationInHours)
    fromDateString = fromDate.strftime("%Y-%m-%dT%H:%M:%SZ")
    toDateString= toDate.strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f'{AQI_API_URL}/missions?from={fromDateString}&to={toDateString}&skip=0&limit=100'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        missions = result['missions']
        for mission in missions:
            mission['audits'] = None
        return result
    else:
        response.raise_for_status()
        
def getMissionStatisticsBetweenDates(fromDate, toDate):
    if not (fromDate and toDate):
            return "Unable to answer. Please correct your question and pass both the from and to timestamps."
    fromDate = fromDate.strip()
    toDate = toDate.strip()
    headers = fetchHeaders()
    url = f'{AQI_API_URL}/missionStatistics?from={fromDate}&to={toDate}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        return result
    else:
        response.raise_for_status()
        
def getMissionStatisticsByDuration(durationInHours):
    durationInHours = convert_to_int_if_string(durationInHours)
    headers = fetchHeaders()
    toDate = datetime.now()
    fromDate = toDate - timedelta(hours=durationInHours)
    fromDateString = fromDate.strftime("%Y-%m-%dT%H:%M:%SZ")
    toDateString= toDate.strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f'{AQI_API_URL}/missionStatistics?from={fromDateString}&to={toDateString}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        return result
    else:
        response.raise_for_status()

def getLastMission(par1= ""):
    headers = fetchHeaders()
    url = f'{AQI_API_URL}/missions/lastMission'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()

def getDefectImage(missionId, filePath):
    headers = fetchHeaders()
    file_name_with_extension = os.path.basename(filePath)
    encoded_file_name = urllib.parse.quote(file_name_with_extension)

    url = f'{AQI_API_URL}/missions/{missionId}/annotatedImages/{encoded_file_name}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        response_json = response.json()
        del response_json['schema_version']
        for box in response_json['boundingBoxes']:
            del box['x']
            del box['y']
            del box['width']
            del box['height']
        return response_json
    else:
        response.raise_for_status()

def getAllMissionImages(missionId):
    headers = fetchHeaders()
    url = f'{AQI_API_URL}/missions/{missionId}/annotatedImages'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        response_json = response.json()
        for image in response_json:
            del image['schema_version']
            for box in image['boundingBoxes']:
                del box['x']
                del box['y']
                del box['width']
                del box['height']
        return response_json
    else:
        response.raise_for_status()


def getMissionReport(missionId):
    headers = fetchHeaders()
    url = f'{AQI_API_URL}/reports/{missionId}/missionReport'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.content
    else:
        response.raise_for_status()

def getMissionByStatus(status):
    headers = fetchHeaders()
    url = f'{AQI_API_URL}/missions/missions/{status}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        for mission in response.json()['missions']:
            mission['audits'] = None
        return response.json()
    else:
        response.raise_for_status()
             
def fetchHeaders():
    headers = {
        'Ocp-Apim-Subscription-Key': f'{SUBSCRIPTION_KEY}',
        'Content-Type': 'application/json'
    }
    
    return headers

def convert_to_int_if_string(variable):
    if isinstance(variable, str):
        try:
            return int(variable)
        except ValueError:
            print("The string cannot be converted to an integer.")
            return None
    return variable
       