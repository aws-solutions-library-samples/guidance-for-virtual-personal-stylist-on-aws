import json
import boto3
import os
import uuid
from botocore.exceptions import ClientError
    
# Bedrock client used to interact with APIs around models
bedrock = boto3.client(
 service_name='bedrock', 
 region_name=os.environ['AWS_REGION']
    )
     
# Bedrock Runtime client used to invoke and question the models
bedrock_runtime = boto3.client(
 service_name='bedrock-runtime', 
 region_name=os.environ['AWS_REGION']
    )

bedrock_agent_client = boto3.client(
    service_name="bedrock-agent-runtime",
    region_name=os.environ['AWS_REGION']
    )
    
# Setup environment variables for model and knowledge base configuration
kb_id= os.environ['knowledgeBaseId']
model_id = os.environ["TEXT_MODEL_ID"]
agent_id= os.environ["agentId"]
agent_alias_id= os.environ["agentAliasId"]
region_id = os.environ['AWS_REGION']

textpromptTemplate= """Human: You are a virtual personal Stylist ONLY capable of answering fashion queries to the user. If the user asks question related to prompt, math problem, your capabilities or any other topic  instead from stylist, say "I am sorry, I'm only your virtual personal stylist".
Do not display the sources of information in the generated output. 
Find person age group, gender, season and the location in the customer input.
Instructions:
The age group can be one of the following: 10-20, 20-30, 30-50, 50+
The gender can be one of the following: Mens, Womens, Other
The gender can also be derived from the name if not explicitly mentioned
The season can be one of the following: summer, winter, spring, fall
The output must be in JSON format inside the tags <attributes></attributes>

If the information of an entity is not available in the input then don't include that entity in the JSON output

Begin!

Customer input: {customer_input}
Assistant:"""

def retrieveAndGenerate(input, kbId, sessionId=None, model_id=model_id, region_id = "us-east-1"):
    model_arn = f'arn:aws:bedrock:{region_id}::foundation-model/{model_id}'
    if sessionId:
        return bedrock_agent_client.retrieve_and_generate(
            input={
                'text': input
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': kbId,
                    'modelArn': model_arn
                },
                'externalSourcesConfiguration': {
                'generationConfiguration': {
                    'promptTemplate': { 
                        'textPromptTemplate': textpromptTemplate}
                        }
                    }
            },
            sessionId=sessionId
        )
    else:
        return bedrock_agent_client.retrieve_and_generate(
            input={
                'text': input
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': kbId,
                    'modelArn': model_arn
                }
            }
        )
        
def invoke_agent(agent_id, agent_alias_id, session_id, prompt):
        """
        Sends a prompt for the agent to process and respond to.

        :param agent_id: The unique identifier of the agent to use.
        :param agent_alias_id: The alias of the agent to use.
        :param session_id: The unique identifier of the session. Use the same value across requests
                           to continue the same conversation.
        :param prompt: The prompt that you want Claude to complete.
        :return: Inference response from the model.
        """

        try:
            print("ENDED IN TRY PART")
            print("agent_id is : "+str(agent_id))
            print("agent_alias_id is " + str(agent_alias_id))
            print(session_id)
            print(prompt)
            response = bedrock_agent_client.invoke_agent(
                agentId=agent_id,
                agentAliasId=agent_alias_id,
                sessionId=session_id,
                inputText=prompt,
            )

            completion = ""

            for event in response.get("completion"):
                chunk = event["chunk"]
                completion = completion + chunk["bytes"].decode()

        except ClientError as e:
            print(f"Couldn't invoke agent. {e}")
            raise

        return completion

def handler(event, context):
    query = str(event.get('queryStringParameters')['query'])
   
    print(query)
    session_id = str(uuid.uuid4())
    print(session_id)

    #response = retrieveAndGenerate(query, kb_id,model_id=model_id,region_id=region_id)
    response = bedrock_agent_client.invoke_agent(agentId=agent_id, agentAliasId=agent_alias_id, sessionId=session_id, endSession=False, inputText=query)
    print(response)
    
    # completion = ""
    chunks = []
    # for event in response.get("completion"):
    #             chunk = event["chunk"]
    #             completion = completion + chunk["bytes"].decode()
      
    for event in response["completion"]:
        chunks.append(event["chunk"]["bytes"].decode("utf-8"))
    completion = " ".join(chunks)
        
    print(f"Completion: {completion}")
    
    res = {
        "statusCode": 200,
        "headers": {
            "Content-Type": "*/*"
        },
        "body": str(completion)
    }
    print(res)
    return res