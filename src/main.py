from pathlib import Path
import tempfile
import os
import traceback


from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import boto3

from tiff_processor import process_slide_image
from dicom_processor import process_dicom


app = FastAPI()

# Configure your AWS S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.environ.get("AMAZON_S3_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AMAZON_S3_SECRET_ACCESS_KEY"),
    region_name=os.environ.get("AMAZON_S3_REGION_NAME"),
)


class S3ImageRequest(BaseModel):
    s3_uri: str  # Example: "s3://my-bucket/path/to/image.tiff"


def parse_s3_uri(s3_uri: str):
    """Parses S3 URI and extracts bucket name and key."""
    if not s3_uri.startswith("s3://"):
        raise ValueError("Invalid S3 URI format.")
    parts = s3_uri[5:].split("/", 1)
    if len(parts) != 2:
        raise ValueError("Invalid S3 URI format.")
    return parts[0], parts[1]


def find_file_extension(image_uri):
    dot_index = image_uri.rfind(".")
    if dot_index < 0:
        raise Exception("No extension found in uri: ", image_uri)

    return image_uri[dot_index:]


def find_file_name(image_uri):
    dot_index = image_uri.rfind(".")
    if dot_index < 0:
        raise Exception("No extension found in uri: ", image_uri)

    slash_index = image_uri.rfind("/")
    if dot_index < 0:
        raise Exception("No / found in uri: ", image_uri)
    return image_uri[slash_index + 1 : dot_index]


def calculate_file_name_without_prefix(filename):
    underscore_index = filename.rfind("_")
    if underscore_index < 0:
        raise Exception("No _ found in file: ", filename)

    return filename[underscore_index + 1 :]


@app.post("/process-image/")
async def process_image(request: S3ImageRequest):
    try:
        print("------------------------ Request Received ---------------------")
        print("S3 URI: ", request.s3_uri)
        bucket, key = parse_s3_uri(request.s3_uri)

        # Download image to a temp file
        with tempfile.NamedTemporaryFile(
            delete=True,
            suffix=find_file_extension(request.s3_uri),
        ) as tmp_file:
            print("Downloading image: ", tmp_file.name)

            s3_client.download_file(bucket, key, tmp_file.name)
            temp_image_path = tmp_file.name

            output_image_path_object = Path(temp_image_path)
            file_name = output_image_path_object.stem + "_processed"

            output_dir = os.environ.get("OUTPUT_DIRECTORY", "")
            if not output_dir:
                print(
                    "OUTPUT Directory not set, files will be written in the same folder in which program is running"
                )
            else:
                output_dir += "/"

            # Placeholder for image processing
            written_files = process_slide_image(
                temp_image_path, output_dir + file_name + ".tiff"
            )

            original_name = find_file_name(request.s3_uri)
            OUTPUT_FOLDER = "processed/" + original_name + "/"

            uploaded_files = []
            # Upload processed image back to S3
            for file_path in written_files:
                new_key = OUTPUT_FOLDER + calculate_file_name_without_prefix(
                    os.path.basename(file_path)
                )

                print("Uploading: ", file_path)
                s3_client.upload_file(file_path, bucket, new_key)

                os.remove(file_path)
                print("Removed: ", file_path)

                uploaded_files.append(new_key)

        # Return new S3 URL
        return {"processed_s3_uris": uploaded_files}

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-dicom/")
async def process_dicom_image(request: S3ImageRequest):
    try:
        print("------------------------ Request Received ---------------------")
        print("S3 URI: ", request.s3_uri)
        bucket, key = parse_s3_uri(request.s3_uri)

        # Download image to a temp file
        with tempfile.NamedTemporaryFile(
            delete=True,
            suffix=find_file_extension(request.s3_uri),
        ) as tmp_file:
            print("Downloading image: ", tmp_file.name)

            s3_client.download_file(bucket, key, tmp_file.name)
            temp_image_path = tmp_file.name

            output_image_path_object = Path(temp_image_path)
            file_name = output_image_path_object.stem + "_processed"

            output_dir = os.environ.get("OUTPUT_DIRECTORY", "")
            if not output_dir:
                print(
                    "OUTPUT Directory not set, files will be written in the same folder in which program is running"
                )
            else:
                output_dir += "/"

            # Placeholder for image processing
            written_files = process_dicom(
                temp_image_path, output_dir + file_name + ".tiff"
            )

            original_name = find_file_name(request.s3_uri)
            OUTPUT_FOLDER = "processed/" + original_name + "/"

            uploaded_files = []
            # Upload processed image back to S3
            for file_path in written_files:
                new_key = OUTPUT_FOLDER + calculate_file_name_without_prefix(
                    os.path.basename(file_path)
                )

                print("Uploading: ", file_path)
                s3_client.upload_file(file_path, bucket, new_key)

                os.remove(file_path)
                print("Removed: ", file_path)

                uploaded_files.append(new_key)

        # Return new S3 URL
        return {"processed_s3_uris": uploaded_files}

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
