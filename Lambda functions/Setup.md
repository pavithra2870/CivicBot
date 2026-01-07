We need 2 layers

# Layer 1: Twilio SDK Layer

Purpose: Provides the necessary libraries for the Lambda to communicate with the Twilio API (used by WhatsApp_Connector and StatusNotifier). 

Contains: twilio, urllib3, requests.

Steps to Create:

1. Prepare the environment:

```console
mkdir twilio-layer && cd twilio-layer
mkdir python
```

2. Install dependencies:
```console
pip install twilio==7.13.0 requests -t python/
```
3. Package the layer:
```console
zip -r twilio_layer.zip python
```
4. Deploy to AWS:

- Go to Lambda > Layers > Create layer.

- Upload twilio_layer.zip.

- Compatible Runtimes: Python 3.11, Python 3.12, Python 3.13.

# Layer 2: CivicBot Utilities Layer

Purpose: Contains common utility code and heavier dependencies used for AI processing and data handling. 

Contains: boto3 (specifically for newer Bedrock features), requests, and any custom shared logic.

Steps to Create:

1. Prepare the environment:
```console
mkdir utility-layer && cd utility-layer
mkdir python
```
2. Install dependencies: (Even though Lambda has boto3, we include a specific version to ensure Bedrock Titan features are supported)
```console
pip install boto3 requests -t python/
```
3. Package the layer:
```console
zip -r utility_layer.zip python
```
4. Deploy to AWS:

- Go to Lambda > Layers > Create layer.

- Upload utility_layer.zip.

# How to Attach Layers to Your Functions:

To make your code work, you must attach these layers to your specific Lambda functions in the AWS Console:

- WhatsApp_Connector  -  Twilio SDK Layer

- CivicBot_Handler  -  CivicBot Utilities Layer

- LayerStatusNotifier  -  Twilio SDK Layer
