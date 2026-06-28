#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

# Build LangChain layer if missing
if [ ! -d "layer/langchain/python" ] || [ "${FORCE_LAYER:-0}" = "1" ]; then
  echo "Building LangChain layer into layer/langchain/python..."
  mkdir -p layer/langchain/python
  python -m pip install --upgrade pip
  python -m pip install -r app/lambda/requirements.txt -t layer/langchain/python
fi

# Zip the layer
echo "Packaging layer..."
rm -f layer/langchain.zip || true
(cd layer && zip -r langchain.zip langchain)

# Ensure AWS CLI and SAM are available
if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI not found. Install and configure it first." >&2
  exit 1
fi
if ! command -v sam >/dev/null 2>&1; then
  echo "SAM CLI not found. Install it before continuing." >&2
  exit 1
fi

# Ensure S3 bucket is provided or create one
: ${S3_BUCKET:=}
if [ -z "$S3_BUCKET" ]; then
  TS=$(date +%s)
  S3_BUCKET="savegpt-deploy-$TS"
  echo "Creating S3 bucket $S3_BUCKET in us-east-1..."
  aws s3api create-bucket --bucket "$S3_BUCKET" --region us-east-1 || true
fi

# Build and package
echo "sam build"
sam build --use-container || sam build

echo "sam package"
sam package --s3-bucket "$S3_BUCKET" --output-template-file packaged.yaml

STACK_NAME=${STACK_NAME:-aws-prompt-routing-tool}

echo "sam deploy"
sam deploy --template-file packaged.yaml --stack-name "$STACK_NAME" --capabilities CAPABILITY_IAM --region us-east-1 --no-fail-on-empty-changeset --no-confirm-changeset

# Get API URL output
API_URL=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query "Stacks[0].Outputs[?OutputKey=='PromptApiUrl'].OutputValue" --output text)

echo
s=
if [ -n "$API_URL" ]; then
  echo "Deployment complete. API endpoint: $API_URL"
  echo "Configure your frontend by setting window.PROMPT_ROUTER_API_URL = '$API_URL'"
else
  echo "Deployment complete but couldn't read API URL from CloudFormation outputs. Check the AWS Console."
fi
