import requests


test_1 = "s3://diagnostic-images-bucket/ahmed_test/Kidney-49098.tif"
test_2 = "s3://diagnostic-images-bucket/PR-BP-HP-21865-D.tif"
test_3 = "s3://diagnostic-images-bucket/ahmed_test/tiff_output.tiff"
test_4 = "s3://diagnostic-images-bucket/ahmed_test/2011485216.50872.17545.132222030122055233064080.0"
test_5 = "s3://diagnostic-images-bucket/SKM-C-T-138a.tif"
# S3 URI of the image you want to process
s3_uri = test_5

# Create request payload
payload = {"s3_uri": s3_uri}

# URL of your FastAPI server
API_URL = "http://localhost:8001/process-image/"
# Send POST request
response = requests.post(API_URL, json=payload)

# Print response
if response.status_code == 200:
    print("Processed image URL:", response.json()["processed_s3_uris"])
else:
    print("Error:", response.text)

