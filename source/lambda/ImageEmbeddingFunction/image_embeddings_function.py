import boto3
import base64
import json
import os
import uuid
from botocore.exceptions import ClientError
from decimal import Decimal

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ['AWS_REGION'])
table = dynamodb.Table(os.environ.get('dynamodb_table'))

def encode_image_to_base64(image_data):
    return base64.b64encode(image_data).decode('utf-8')

def get_embedding(image_base64):
    input_data = {"inputImage": image_base64}
    body = json.dumps(input_data)

    response = bedrock_runtime.invoke_model(
        body=body,
        modelId= os.environ.get("EMBEDDINGS_MODEL_ID"),
        accept="application/json",
        contentType="application/json"
    )

    response_body = json.loads(response.get("body").read())
    return response_body.get("embedding")

def float_to_decimal(obj):
    if isinstance(obj, list):
        return [float_to_decimal(item) for item in obj]
    elif isinstance(obj, float):
        return Decimal(str(obj))
    return obj

def handler(event, context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            image_data = response['Body'].read()
            image_base64 = encode_image_to_base64(image_data)
            
            embedding = get_embedding(image_base64)
            
            item = {
                'id': str(uuid.uuid4()),
                'image_key': key,
                'vector': float_to_decimal(embedding)  # Convert float values to Decimal
            }
            
            table.put_item(Item=item)
            
            print(f"Processed image {key} and stored embedding in DynamoDB")
        
        except ClientError as e:
            print(f"Error processing image {key}: {str(e)}")

    return {
        'statusCode': 200,
        'body': json.dumps('Image processing completed')
    }