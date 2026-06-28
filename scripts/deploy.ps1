Param(
  [string]$S3Bucket = $env:S3_BUCKET,
  [string]$StackName = "aws-prompt-routing-tool"
)

Set-Location -Path (Join-Path $PSScriptRoot "..")

if (-not (Test-Path "layer\langchain\python`)" -or $env:FORCE_LAYER -eq "1") {
  Write-Host "Building LangChain layer into layer/langchain/python..."
  New-Item -ItemType Directory -Force -Path layer\langchain\python | Out-Null
  & "C:/Program Files/Python313/python.exe" -m pip install --upgrade pip
  & "C:/Program Files/Python313/python.exe" -m pip install -r app/lambda/requirements.txt -t layer\langchain\python
}

Write-Host "Packaging layer..."
if (Test-Path layer\langchain.zip) { Remove-Item layer\langchain.zip -Force }
Compress-Archive -Path layer\langchain\* -DestinationPath layer\langchain.zip -Force

if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
  Write-Error "aws CLI not found. Install and configure it first."
  exit 1
}
if (-not (Get-Command sam -ErrorAction SilentlyContinue)) {
  Write-Error "SAM CLI not found. Install it before continuing."
  exit 1
}

if (-not $S3Bucket) {
  $ts = [int][double]::Parse((Get-Date -UFormat %s))
  $S3Bucket = "savegpt-deploy-$ts"
  Write-Host "Creating S3 bucket $S3Bucket in us-east-1..."
  aws s3api create-bucket --bucket $S3Bucket --region us-east-1 | Out-Null
}

Write-Host "sam build"
sam build --use-container 2>$null
if ($LASTEXITCODE -ne 0) { sam build }

Write-Host "sam package"
sam package --s3-bucket $S3Bucket --output-template-file packaged.yaml

Write-Host "sam deploy"
sam deploy --template-file packaged.yaml --stack-name $StackName --capabilities CAPABILITY_IAM --region us-east-1 --no-fail-on-empty-changeset --no-confirm-changeset

$apiUrl = aws cloudformation describe-stacks --stack-name $StackName --query "Stacks[0].Outputs[?OutputKey=='PromptApiUrl'].OutputValue" --output text

if ($apiUrl) {
  Write-Host "Deployment complete. API endpoint: $apiUrl"
  Write-Host "Configure your frontend by setting window.PROMPT_ROUTER_API_URL = '$apiUrl'"
} else {
  Write-Host "Deployment complete but couldn't read API URL from CloudFormation outputs. Check the AWS Console."
}
