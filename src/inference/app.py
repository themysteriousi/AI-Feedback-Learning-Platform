import json
import os
import boto3

# Initialize the Bedrock Runtime client
# Region is automatically picked up from the Lambda environment
bedrock_runtime = boto3.client('bedrock-runtime')

# Using a cost-effective, fast model like Claude 3 Haiku or Llama 3
# You can change this to 'meta.llama3-8b-instruct-v1:0' for Llama 3
MODEL_ID = os.environ.get('MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')

def lambda_handler(event, context):
    try:
        # Parse the incoming request body from API Gateway
        body = json.loads(event.get('body', '{}'))
        user_prompt = body.get('prompt', '')

        if not user_prompt:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Prompt is required'})
            }

        # Format request for Claude 3 Messages API
        if "claude" in MODEL_ID:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 512,
                "messages": [
                    {"role": "user", "content": user_prompt}
                ]
            }
        else:
            # Fallback for Llama 3 format
            request_body = {
                "prompt": f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
                "max_gen_len": 512,
                "temperature": 0.5,
                "top_p": 0.9
            }

        # Invoke Bedrock
        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
            contentType='application/json',
            accept='application/json',
            body=json.dumps(request_body)
        )

        response_body = json.loads(response.get('body').read())
        
        # Parse output based on model type
        if "claude" in MODEL_ID:
            generated_text = response_body.get('content', [])[0].get('text', '')
        else:
            generated_text = response_body.get('generation', '')

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'response': generated_text,
                'model_id': MODEL_ID
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal Server Error', 'details': str(e)})
        }
