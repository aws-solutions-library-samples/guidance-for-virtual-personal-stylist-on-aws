import boto3
import json
import base64
import math
from decimal import Decimal
import os

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ['AWS_REGION'])
table = dynamodb.Table(os.environ.get('dynamodb_table')) #product_embeddings

def get_embedding(text_description):
    input_data = {"inputText": text_description}
    body = json.dumps(input_data)
    response = bedrock_runtime.invoke_model(
        body=body,
        modelId=os.environ.get("EMBEDDINGS_MODEL_ID"),
        accept="application/json",
        contentType="application/json"
    )
    response_body = json.loads(response.get("body").read())
    return response_body.get("embedding")

def cosine_similarity(v1, v2):
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))
    return dot_product / (norm_v1 * norm_v2)

def handler(event, context):
    query = event['queryStringParameters']['query']
    query_embedding = get_embedding(query)
    
    response = table.scan()
    items = response['Items']
    
    results = []
    for item in items:
        vector = [float(x) for x in item['vector']]  # Convert Decimal to float
        score = cosine_similarity(query_embedding, vector)
        results.append({
            'image_key': item['image_key'],
            'score': score
        })
    
    # Sort results by score in descending order
    results.sort(key=lambda x: x['score'], reverse=True)
    top_3_results = results[:3]
    
    # Fetch and encode images for top 2 results
    for result in top_3_results:
        image_key = result['image_key']
        image_data = s3.get_object(Bucket=os.environ.get('bucket'), Key=image_key)['Body'].read()            
        result['image_base64'] = base64.b64encode(image_data).decode('utf-8')
    
    return {
        'statusCode': 200,
        'body': json.dumps(top_3_results, default=str),  # Use default=str to handle Decimal serialization
        'headers': {
            'Content-Type': 'application/json'
        }
    }