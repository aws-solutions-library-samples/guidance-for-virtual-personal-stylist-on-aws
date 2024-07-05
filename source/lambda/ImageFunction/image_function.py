# Use the native inference API to create an image with Stability.ai Stable Diffusion
import base64
import boto3
import json
import os
from base64 import b64decode
from botocore.exceptions import ClientError

NEGATIVE_PROMPTS = ["bad anatomy", "distorted", "blurry","pixelated", "dull", "unclear","poorly rendered","poorly Rendered face","poorly drawn face","poor facial details","poorly drawn hands","poorly rendered hands","low resolution","Images cut out at the top, left, right, bottom.",
    "bad composition","mutated body parts","blurry image","disfigured","oversaturated","bad anatomy","deformed body features",]

# Create a Bedrock Runtime client in the AWS Region of your choice.
bedrock_runtime = boto3.client("bedrock-runtime", region_name=os.environ['AWS_REGION'])

# Set the model ID, e.g., Stable Diffusion XL 1.
image_model_id = os.environ['IMAGE_MODEL_ID']

def handler(event, context): 

    query = str(event.get('queryStringParameters')['query'])
    print(query)
    
    if "queryStringParameters" not in event:
        return  {
        'statusCode': 400,
        'body': 'No query string parameters passed in'
        }

    style = query
    
    # Added the option to invoke Text model to refine the style and feed to Image generation model based on user's choice. 
    text_model_output= text_model(style)

    image_strip = ""
    request = json.dumps({
        "text_prompts": [
            {"text": f"Full body view without a face in " + str(style) + "dslr, ultra quality, dof, film grain, Fujifilm XT3, crystal clear, 8K UHD", "weight": 1.0},
            {"text": "poorly rendered", "weight": -1.0}
        ],
        "cfg_scale": 10,
        "seed": 4000,
        "steps": 50,
        "style_preset": "photographic",
        "negative_prompts": NEGATIVE_PROMPTS
    })
    accept = "application/json"
    contentType = "application/json"
    
    response = bedrock_runtime.invoke_model(body=request, modelId=image_model_id, accept=accept, contentType=contentType)
    response_body = json.loads(response.get("body").read())
    print(response_body)
    
    base_64_img_str = response_body["artifacts"][0].get("base64")
    print("base_64_img_str: " + str(base_64_img_str))
    image_data = base64.b64decode(base_64_img_str.encode())
    print("image_data : " + str(image_data))
    
    return {
            'headers': { "Content-Type": "image/png" },
            'statusCode': 200,
            'body': base64.b64encode(image_data).decode('utf-8'),
            'isBase64Encoded': True
            }


def text_model(prompt):
    
    # Set the model ID, e.g., Claude 3 Haiku.
    text_model_id = os.environ["TEXT_MODEL_ID"]
            
    # Start a conversation with the user message.
    user_message = "You are a personal virtual stylist. Convert the styles provided here: " + str(prompt) + "into properly defined photorealistic clothing recommendation"
    
    native_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "temperature": 0.5,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": user_message}],
                }
            ],
    }

    # Convert the native request to JSON.
    request = json.dumps(native_request)
    
    try:
        # Invoke the model with the request.
        response = bedrock_runtime.invoke_model(modelId=text_model_id, body=request)
    
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{text_model_id}'. Reason: {e}")
        exit(1)
    
    # Decode the response body.
    model_response = json.loads(response["body"].read())
    
    # Extract and print the response text.
    response_text = model_response["content"][0]["text"]
    print(response_text)

    return response_text