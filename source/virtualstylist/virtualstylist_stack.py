# SO9506 - Virtual Personal Stylist Guidance Stack deployed using AWS CDK 

import os
import aws_cdk
from aws_cdk import (
    Duration,
    Stack,
    CfnResource,
    aws_s3 as s3,
    aws_logs as logs,
    aws_s3_deployment as s3_deployment,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_ecr as ecr,
    aws_ecs as ecs, 
    aws_ec2 as ec2,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,   
    aws_ecs_patterns as ecs_patterns,
    aws_secretsmanager as secretsmanager,
    aws_ecr_assets as ecr_assets,
    RemovalPolicy,
    aws_s3_notifications as s3_notifications,
    aws_certificatemanager as acm,
    aws_elasticloadbalancingv2 as elbv2,
    aws_bedrock as bedrock,
    aws_cloudformation as cfn,
    aws_dynamodb as dynamodb,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_apigatewayv2 as apigatewayv2,
    CfnParameter,
    aws_cognito as cognito,
    SecretValue,
    Fn,
    CfnOutput
)
from aws_cdk.aws_ecs_patterns import ApplicationLoadBalancedFargateService  # Import from aws_ecs_patterns


from constructs import Construct
from constructs import Node

class VirtualstylistStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Prefix for naming conventions
        prefix = "VirtualStylist"

        # Create Cognito user pool
        user_pool = cognito.UserPool(self, f"{prefix}UserPool")

        # Create Cognito client
        user_pool_client = cognito.UserPoolClient(self, f"{prefix}UserPoolClient",
                                                  user_pool=user_pool,
                                                  generate_secret=True
                                                  )
        
        
        # Store Cognito parameters in a Secrets Manager secret
        cognito_secret = secretsmanager.Secret(self, f"{prefix}ParamCognitoSecret",
                                       secret_object_value={
                                           "pool_id": SecretValue.unsafe_plain_text(user_pool.user_pool_id),
                                           "app_client_id": SecretValue.unsafe_plain_text(user_pool_client.user_pool_client_id),
                                           "app_client_secret": user_pool_client.user_pool_client_secret
                                       },
                                       # secret_name=Config.SECRETS_MANAGER_ID
                                        secret_name=f"{prefix}CognitoSecrets",
                                        description='Cognito Key Secrets'
                                       )
                                       

        # Get the current account ID and region from the CDK context
        account_id = Stack.of(self).account
        region = Stack.of(self).region

        # Define S3 bucket
        s3_bucket = s3.Bucket(self, "VirtualStylistAppBucketCDK", versioned=True, removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True, enforce_ssl=True)

        # Specify the local directory containing the CSV files
        local_asset_dir = os.path.join(os.getcwd(), "csv_files")

        # Deploy the CSV files to the S3 bucket
        s3_deployment.BucketDeployment(
            self, "DeployCSVFiles",
            sources=[s3_deployment.Source.asset(local_asset_dir)],
            destination_bucket=s3_bucket
            )
        

        # Define the policy statement
        bedrock_policy_statement = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:InvokeModel","bedrock:ListFoundationModels","bedrock:RetrieveAndGenerate",
                "bedrock:Retrieve","bedrock:StartIngestionJob", "logs:CreateLogGroup",
                "logs:CreateLogStream","logs:PutLogEvents", 'secretsmanager:GetSecretValue', 'secretsmanager:DescribeSecret', 'kms:Decrypt',"bedrock:StartIngestionJob"],
            resources=[
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
                "arn:aws:bedrock:*::foundation-model/stability.stable-diffusion-xl-v1",
                "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v1",
                "arn:aws:bedrock:*::foundation-model/cohere.embed-english-v3", 
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
            ]
        )

        bedrock_agent_policy_statement = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:InvokeAgent","bedrock:GetAgent"],
            resources=[f"arn:aws:bedrock:{region}:{account_id}:agent-alias/*"])

        # Define the Text Generation Lambda function
        text_lambda = lambda_.Function(
            self, "TextFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(900),
            code=lambda_.Code.from_asset("lambda/TextFunction"),  # Path to your Lambda code
            handler="text_function.handler",  # File name.function name
            environment= {
                "IMAGE_MODEL_ID": "stability.stable-diffusion-xl-v1",  # Replace with your desired model ID
                "TEXT_MODEL_ID" : "anthropic.claude-3-sonnet-20240229-v1:0",
                "knowledgeBaseId": "ENTER KNOWLEDGE BASE ID",
                "agentId": "ENTER BEDROCK AGENT ID",
                "agentAliasId": "ENTER AGENT ALIAS ID"
            },
        )

        # You can grant specific permissions using IAM statements
        text_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
                resources=[s3_bucket.bucket_arn, f"{s3_bucket.bucket_arn}/*"]
            )
        )

        # Add the policy statement to the Lambda function's role
        text_lambda.role.add_to_principal_policy(bedrock_policy_statement)
        text_lambda.role.add_to_principal_policy(bedrock_agent_policy_statement)

        # Define the Image Generation Lambda function
        image_lambda = lambda_.Function(
            self, "ImageFunction",
            timeout=Duration.seconds(900),
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset("lambda/ImageFunction"),  # Path to your Lambda code
            handler="image_function.handler",  # File name.function name
            environment= {
                "IMAGE_MODEL_ID": "stability.stable-diffusion-xl-v1",  # Replace with your desired model ID
                "TEXT_MODEL_ID" : "anthropic.claude-3-haiku-20240307-v1:0"
            },
        )
        
        # You can grant specific permissions using IAM statements
        image_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
                resources=[s3_bucket.bucket_arn, f"{s3_bucket.bucket_arn}/*"]
            )
        )
        
        image_lambda.role.add_to_principal_policy(bedrock_policy_statement)

        # Define the Ingestion Pipeline function
        ingestion_lambda = lambda_.Function(
            self, "IngestionFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(900),
            code=lambda_.Code.from_asset("lambda/IngestionFunction"),  # Path to your Lambda code
            handler="ingestion_function.handler",  # File name.function name
            environment= {
                "DATASOURCEID": "ENTER DATASOURCE ID",
                "KNOWLEDGEBASEID": "ENTER KNOWLEDGEBASE ID"},
        )


        # Add S3 event notification to trigger the Lambda function
        s3_bucket.add_event_notification(s3.EventType.OBJECT_CREATED, s3_notifications.LambdaDestination(ingestion_lambda))

        # You can grant specific permissions using IAM statements
        ingestion_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
                resources=[s3_bucket.bucket_arn, f"{s3_bucket.bucket_arn}/*"]
            )
        )

        ingestion_lambda.role.add_to_principal_policy(bedrock_policy_statement)

        ingestion_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:StartIngestionJob","bedrock:invokeModel"],
                resources=[f"arn:aws:bedrock:{region}:{account_id}:knowledge-base/*"],
            )
        )

        # Define the weather Generation Lambda function
        weather_lambda = lambda_.Function(
            self, "WeatherFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(900),
            code=lambda_.Code.from_asset("lambda/WeatherFunction"),  # Path to your Lambda code
            handler="weather_function.handler",  # File name.function name
            environment= {
                "YOUR_OPENWEATHERMAP_API_KEY": "ENTER OPENWEATHERMAP API_KEY"
            },
        )

        # Grant specific permissions using IAM statements
        weather_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                ],
                resources=[f"arn:aws:logs:{region}:{account_id}:*"],
            )
        )

        weather_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=[
                    f"arn:aws:logs:{region}:{account_id}:log-group:/aws/lambda/*:*"
                ],
            )
        )
        
        # Add the resource-based policy permission
        weather_lambda.add_permission(
            "BedrockInvokePermission",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:invokeFunction",
        )
        
        # Define dynamo DB for storing vector embeddings
        product_embeddings_table = dynamodb.Table(
            self, "EmbeddingsTable",
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
            )
            
        # Define Image embeddings Lambda function for generating embeddings and storing in DynamoDB
        imageembeddings_lambda = lambda_.Function(
            self, "ImageEmbeddingsFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(900),
            code=lambda_.Code.from_asset("lambda/ImageEmbeddingFunction"),  # Path to your Lambda code
            handler="image_embeddings_function.handler",  # File name.function name
            environment= {
                "EMBEDDINGS_MODEL_ID" : "amazon.titan-embed-image-v1",
                "dynamodb_table" : product_embeddings_table.table_name
            },
        )
        
        # Define new s3 bucket for Images Catalog
        s3_imagebucket = s3.Bucket(self, "s3Imagebucket", versioned=True, removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True, enforce_ssl=True) 
        
        # Create an IAM policy for Bedrock InvokeModel
        bedrock_policy_embeddings = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:InvokeModel"],
            resources=[f"arn:aws:bedrock:{region}::foundation-model/amazon.titan-embed-image-v1"]
        )

        # Add the policy to the Lambda function's role
        imageembeddings_lambda.add_to_role_policy(bedrock_policy_embeddings)

        # If you need to grant permissions to other Bedrock actions, you can add them like this:
        bedrock_list_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:ListFoundationModels"],
            resources=["*"]  # You might want to restrict this further
        )
        
        imageembeddings_lambda.add_to_role_policy(bedrock_list_policy)
        
        # Add s3 permissions to imageembeddings_lambda
        imageembeddings_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
                resources=[s3_imagebucket.bucket_arn, f"{s3_imagebucket.bucket_arn}/*"]
            )
        )

        
        s3_imagebucket.add_event_notification(s3.EventType.OBJECT_CREATED, s3_notifications.LambdaDestination(imageembeddings_lambda))

        # Image Query Lambda Function  
        imagequery_lambda = lambda_.Function(
            self, "ImageQueryFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(900),
            code=lambda_.Code.from_asset("lambda/ImageQueryHandlingFunction"),  # Path to your Lambda code
            handler="imagequery_function.handler",  # File name.function name
            environment= {
                "dynamodb_table" : product_embeddings_table.table_name, # Replace with your desired dynamodb table 
                "EMBEDDINGS_MODEL_ID" : "amazon.titan-embed-image-v1",
                "bucket": s3_imagebucket.bucket_name
            },
            )
            
         # Add the policy to the Lambda function's role
        imagequery_lambda.add_to_role_policy(bedrock_policy_embeddings)
        
        # Add dynamodb permissions to imagequery_lambda
        imagequery_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:Query",
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Scan"
                ],
                resources=[f"arn:aws:dynamodb:{region}:{account_id}:table/*"],
            )
            )

        # add dynamodb permissions to imageembeddings_lambda
        imageembeddings_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:Query",
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem"
                ],
                resources=[f"arn:aws:dynamodb:{region}:{account_id}:table/*"],
            )
            )
        
        
        # Add s3 permissions to imagequery_lambda function
        imagequery_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
                resources=[s3_imagebucket.bucket_arn, f"{s3_imagebucket.bucket_arn}/*"]
            ))

        
        apigw_log_group = logs.LogGroup(self, "ApiGatewayStylistLogs")
        
        api = apigateway.RestApi(self, "virtual-stylist-api",
                  rest_api_name="virtual-stylist-api",
                  cloud_watch_role=True,
                  description="This service serves the Virtual Stylist API",
                  endpoint_types=[apigateway.EndpointType.REGIONAL],
                  deploy_options=apigateway.StageOptions(
                    access_log_destination=apigateway.LogGroupLogDestination(apigw_log_group),
                    access_log_format=apigateway.AccessLogFormat.json_with_standard_fields(
                        caller=False,
                        http_method=True,
                        ip=True,
                        protocol=True,
                        request_time=True,
                        resource_path=True,
                        response_length=True,
                        status=True,
                        user=True
                    ),
                    stage_name="dev"
                )
        )
        
        api_key_secret = secretsmanager.Secret(
                    self, 'stylistapikeysecret',  # Logical ID of the secret
                    secret_name='stylistapikeysecret',  # Name of the secret in Secrets Manager
                    description='API Key Secret',  # Description of the secret
                    generate_secret_string=secretsmanager.SecretStringGenerator(
                        exclude_punctuation=True,  # Exclude punctuation characters from the secret
                        password_length=32  # Length of the secret string
                    )
                )
        
        
        # Create Api Key and add it to the api. Names must be unique independent of stage
        get_api_secret = secretsmanager.Secret.from_secret_name_v2(self, "GetStylistApiSecret", secret_name=api_key_secret.secret_name)
        api_key = apigateway.ApiKey(self, "VirtualStylistApiKeyCDK", api_key_name="VirtualStylistApiKeyCDK", value=get_api_secret.secret_value.unsafe_unwrap())
        

        # Create Usage Plan and associate it with the API Key
        usage_plan = apigateway.UsagePlan(self, "VirtualStylistUsagePlan", name="VirtualStylistUsagePlan",
                                   throttle=apigateway.ThrottleSettings(
                                        rate_limit=10,
                                        burst_limit=10))
        usage_plan.add_api_key(api_key)
        usage_plan.add_api_stage(api=api, stage=api.deployment_stage)

        # Store the API key and URL in Secrets Manager
        api_key_secret = secretsmanager.Secret(
                            self, 'virtualstylistapikeysecret',
                            secret_name='virtualstylistapikeysecret',
                            description='API Key Secret',
                            generate_secret_string=secretsmanager.SecretStringGenerator(
                            secret_string_template='{"api_key": "%s", "apiurl": "%s"}' % (api_key.key_id, api.url),
                            generate_string_key="ignore",
                            exclude_punctuation=True,
                            password_length=32
                    )
                )


        # Add the /text resource and integrate with the first Lambda function
        text_resource = api.root.add_resource("text")
        text_resource.add_method("GET", apigateway.LambdaIntegration(text_lambda), api_key_required=True, 
                                 method_responses=[apigateway.MethodResponse(
                                                    status_code="200",
                                                    response_models={
                                                    "application/json": apigateway.Model.EMPTY_MODEL
                                                    }
                                    )])

        
        # Add the /image resource and integrate with the second Lambda function
        image_resource = api.root.add_resource("image")
        image_resource.add_method("GET", apigateway.LambdaIntegration(image_lambda), api_key_required=True, 
                                  method_responses=[apigateway.MethodResponse(
                                                    status_code="200",
                                                    response_models={
                                                    "application/json": apigateway.Model.EMPTY_MODEL
                                                    }
                                    )])

        search_resource = api.root.add_resource("search")
        search_resource.add_method("GET", apigateway.LambdaIntegration(imagequery_lambda), api_key_required=True,
                                  method_responses=[apigateway.MethodResponse(
                                                    status_code="200",
                                                    response_models={
                                                    "application/json": apigateway.Model.EMPTY_MODEL
                                                    }
                                    )])
        
        
        # !--------------Virtual Stylist APP DEPLOYMENT ASSETS----------------!

        # Create a VPC with public subnets only and 2 max availability zones
        vpc = ec2.Vpc(
            self, "VirtualStylistVPC",
            max_azs=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    cidr_mask=24,
                    name="public-subnet",
                    subnet_type=ec2.SubnetType.PUBLIC,
                )
            ],
        )
        
        # Create an ECS Cluster named "VirtualStylistCluster"
        cluster = ecs.Cluster(
            self, "VirtualStylistCluster",
            vpc=vpc,
            cluster_name="VirtualStylistCluster",
        )

        # Create ECR repository
        # ecr_repo = ecr.Repository(self, "VirtualStylistStreamlitRepo")

        # Build and push Docker image to ECR
        app_image_asset = ecr_assets.DockerImageAsset(
            self, "VirtualStylistAppImage",
            directory="./stylistdockerapp",
        )
        
        # Create a new Fargate service with the image from ECR and specify the service name
        app_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "VirtualStylistFargateService",
            cluster=cluster,
            service_name="ecs-virtualstylist-service",
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_registry(app_image_asset.image_uri),
                container_port=8501,
            ),
            public_load_balancer=True,
            assign_public_ip=True,
            #protocol=elbv2.ApplicationProtocol.HTTPS,
            runtime_platform=ecs.RuntimePlatform(
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
                #cpu_architecture=ecs.CpuArchitecture.ARM64 # If running on Mac, use ARM64, otherwise use x86_64 when creating docker image from linux 
            ),
        )
        
        # Create a security group for the ECS service
        service_security_group = ec2.SecurityGroup(
            self, "ServiceSecurityGroup",
            vpc=vpc,
            description="Security group for the Virtual Stylist ECS service",
            allow_all_outbound=True
        )
        
        # Add an inbound rule to allow access on port 8501 from the load balancer
        service_security_group.add_ingress_rule(
            peer=ec2.Peer.security_group_id(app_service.load_balancer.connections.security_groups[0].security_group_id),
            connection=ec2.Port.tcp(8501),
            description="Allow HTTP traffic on port 8501 from load balancer"
        )
        
        # Create a security group for the load balancer
        lb_security_group = ec2.SecurityGroup(
            self, "VirtualStylistLoadBalancerSecurityGroup",
            vpc=vpc,
            description="Security group for the Virtual Stylist load balancer",
            allow_all_outbound=True
        )

        # Add an inbound rule to allow access from your IP address
        my_ip = Node.of(self).try_get_context("my_ip")
        if my_ip:
            lb_security_group.add_ingress_rule(
                peer=ec2.Peer.ipv4(aws_cdk.Fn.join("", [my_ip, "/32"])),
                connection=ec2.Port.tcp(80),
                description="Allow HTTP traffic from my IP"
            )
        else:
            print("Warning: 'my_ip' context value not provided.")

        # Associate the security group with the load balancer
        app_service.load_balancer.add_security_group(lb_security_group)
        
        # Attach the security group to the ECS service
        app_service.service.connections.add_security_group(service_security_group)
        
        # Create a CloudFront distribution
        distribution = cloudfront.Distribution(
            self, "VirtualStylistDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.LoadBalancerV2Origin(app_service.load_balancer),
                #viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
            )
        )

        # # CDK to create a new ACM certificate for ALB
        # certificate = acm.Certificate(
        #     self, "VirtualStylistCertificate",
        #     domain_name= app_service.load_balancer.load_balancer_dns_name,
        #     validation=acm.CertificateValidation.from_dns(),
        # )
        
        secrets_manager_policy = iam.Policy(
            self, "SecretsManagerPolicy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["secretsmanager:GetSecretValue"],
                    resources=["*"],
                )
            ],
        )
        
        # Attach Secrets manager policy
        app_service.task_definition.task_role.attach_inline_policy(secrets_manager_policy)
        
        #bedrock policy permissions 
        bedrock_iam = iam.Policy(
            self, "BedrockPermissionsPolicy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "bedrock:InvokeModel",
                        "bedrock:InvokeModelWithResponseStream",
                    ],
                    resources=[
                        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
                        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
                        "arn:aws:bedrock:*::foundation-model/stability.stable-diffusion-xl-v0",
                        "arn:aws:bedrock:*::foundation-model/stability.stable-diffusion-xl-v1",
                        "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v1",
                        "arn:aws:bedrock:*::foundation-model/cohere.embed-english-v3"
                    ],
                )
            ],
        )
        

        # Add the Bedrock permissions to the task role
        app_service.task_definition.task_role.attach_inline_policy(bedrock_iam)

        # Grant ECR repository permissions for the task execution role
        app_image_asset.repository.grant_pull_push(app_service.task_definition.execution_role)
        
        
        # Grant permissions for CloudWatch Logs
        log_group = logs.LogGroup(
            self, "MyLogGroup",
            log_group_name="/ecs/my-fargate-service",
            removal_policy=RemovalPolicy.DESTROY,
        )

        log_group.grant_write(app_service.task_definition.execution_role)
        
        # add cloudfront to load balancer defined above
        

        # Output the API Gateway invoke URL
        # CfnOutput(
        #     self, "ApiGatewayUrl",
        #     value=api.url,
        #     description="API Gateway endpoint URL for dev stage",
        #     export_name="ApiGatewayUrl"
        # )
        
        # output Load balancer dns
        CfnOutput(
            self, "LoadBalancerDNS",
            value=app_service.load_balancer.load_balancer_dns_name,
            description="DNS name of the Virtual Stylist load balancer"
        )
        
        # Output CloudFront URL
        CfnOutput(self, "CloudFrontURL",
        value=f"https://{distribution.distribution_domain_name}",
        description="URL of the CloudFront distribution")

        # Output the user pool and client IDs
        # CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
        # CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id)
