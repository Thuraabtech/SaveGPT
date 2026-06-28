# AWS Prompt Routing Tool

A serverless prompt router that classifies incoming prompts as `HIGH`, `MEDIUM`, or `LOW`, then sends each prompt to the appropriate Amazon Bedrock Claude model.

## Architecture

- Static frontend hosted on S3 + CloudFront
- HTTP API through API Gateway
- Lambda router/classifier in Python 3.12
- DynamoDB for request/response logs
- CloudWatch for logs and metrics

## Repository Structure

- `template.yaml` - AWS SAM infrastructure
- `app/lambda/handler.py` - Lambda router and classifier
- `app/static/` - static frontend assets
- `.github/workflows/ci.yml` - GitHub Actions validation

## Prerequisites

- AWS account with Bedrock model access in `us-east-1`
- AWS CLI configured
- AWS SAM CLI installed
- Python 3.12

## Deploy

```bash
sam build
sam deploy --guided
```

During guided deployment, provide:

- Stack name: `aws-prompt-routing-tool`
- Region: `us-east-1`
- Confirm IAM capabilities: `CAPABILITY_IAM`
- Accept creation of the CloudFormation stack outputs

## Local validation

Run the Lambda unit tests:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## GitHub workflow

This repo includes a GitHub Actions workflow that validates Python syntax and runs tests on push and pull requests.

## Next steps after deployment

- Upload the frontend assets to S3 and point CloudFront at the bucket
- Configure the frontend with the deployed HTTP API URL
- Enable AWS Budgets and a CloudWatch billing alarm
- Tighten IAM permissions before production use
