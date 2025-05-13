import argparse
import math

import pydicom
from pydicom.pixel_data_handlers.util import apply_modality_lut, apply_voi_lut, apply_voi
import cv2
import numpy as np

def auto_window_image(input_image, low_perc=1, high_perc=99):
    # Clip based on percentiles
    image = np.asarray(input_image)
    low = np.percentile(image, low_perc)
    high = np.percentile(image, high_perc)
    image = np.clip(image, low, high)
    image = (image - low) / (high - low) * 255.0
    return image.astype(np.uint8)

def normalize_values(input_image):
    # Step 4: Normalize pixel values to 0-255 (for saving with OpenCV)
    # Convert to float32 to avoid clipping during normalization
    pixels = input_image.astype(np.float32)
    pixels -= pixels.min()
    pixels /= pixels.max()
    pixels *= 255.0
    has_nan = np.isnan(pixels).any() or math.isnan(float(pixels.max())) or math.isnan(float(pixels.min()))

    return pixels, has_nan


def process_dicom(dicom_path: str, output_tiff_path: str):
    ds = pydicom.dcmread(dicom_path)

    # Step 1: Get the raw pixel data
    pixels = ds.pixel_array

    # Step 2: Apply Modality LUT (maps stored values to meaningful units like Hounsfield)
    modality_pixels = apply_modality_lut(pixels, ds)

    # Step 3: Apply VOI LUT (windowing - contrast/brightness adjustment)
    #pixels = auto_window_image(pixels)
    pixels = apply_voi_lut(modality_pixels, ds)
    pixles, has_nan = normalize_values(pixels)
    if has_nan:
        print("Auto windowing")
        # If we have nan means the metadata and windowing failed
        pixels = auto_window_image(modality_pixels)
        pixles, _ = normalize_values(pixels)


    # Step 5: Convert to uint8 for OpenCV
    image = cv2.normalize(pixels, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    if ds.PhotometricInterpretation == "MONOCHROME1":
        image = cv2.bitwise_not(image)  # Inverts the grayscale image

    # Step 6: Save with OpenCV
    cv2.imwrite(output_tiff_path, image)

    return [output_tiff_path]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert a dicom xray file to png")
    parser.add_argument("dicom_path", help="Full path to the mri file")
    parser.add_argument("output_tiff_path", help="Full path to the generated tiff file")

    args = parser.parse_args()
    process_dicom(args.dicom_path, args.output_tiff_path)
