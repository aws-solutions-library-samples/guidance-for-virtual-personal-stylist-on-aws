import datetime
import json
import sys
import os
import urllib.parse
import urllib.request
import subprocess
import requests # imported from layers

# Replace with your OpenWeatherMap API key
API_KEY = os.environ.get('YOUR_OPENWEATHERMAP_API_KEY')

def handler(event, context):

    print("event ", event)
    city = event["parameters"][0]["value"]
    print(city)
    
    
    # Get the location name from the input event
    #location = event.get('location', 'Seattle')
    
    # Construct the API request URL
    base_url = 'https://api.openweathermap.org/data/2.5/weather'
    params = {
        'q': city,
        'appid': API_KEY,
        'units': 'metric'
    }
    url = f'{base_url}?{urllib.parse.urlencode(params)}'
    
    # Make the API request
    response = requests.get(url)
    response.raise_for_status()  # Raise an exception for HTTP errors
        
    # Parse JSON response
    weather_data = response.json()
    # response = urllib.request.urlopen(url)
    # data = response.read().decode('utf-8')
    # weather_data = json.loads(data)
        
    # Extract the relevant weather information
    city = weather_data['name']
    temperature = weather_data['main']['temp']
    description = weather_data['weather'][0]['description']

    # Construct the response
    response_body = {
        'city': city,
        'temperature': temperature,
        'condition': description
        }

   
    # response_str = requests.get(api_url).text
    # response_json = {"temperature": str(response_str)}
    # response_body = {"application/json": {"body": json.dumps(response_json)}}
    
    action_response = {
        "actionGroup": event["actionGroup"],
        "apiPath": event["apiPath"],
        "httpMethod": event["httpMethod"],
        "parameters": event["parameters"],
        "httpStatusCode": 200,
        "responseBody": response_body,
    }

    session_attributes = event["sessionAttributes"]
    prompt_session_attributes = event["promptSessionAttributes"]

    return {
        "messageVersion": "1.0",
        "response": action_response,
        "sessionAttributes": session_attributes,
        "promptSessionAttributes": prompt_session_attributes,
    }