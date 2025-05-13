import sys

sys.path.append("../src")

from tiff_processor import process_slide_image

input_1 = "/home/ahmed/Pictures/wsi/PR-BP-24-5/PR-BP-24-5.svs"
output_1 = "./test.tiff"

input_2 = "./test.tiff"
output_2 = "./processed.tiff"
process_slide_image(input_1, output_1)
