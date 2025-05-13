import sys
from enum import Enum
from pathlib import Path

import pyvips
import matplotlib.pyplot as plt


class ImageMetadata:
    def __init__(
        self,
        height,
        width,
        xres,
        yres,
        pyramid_depth,
        resunit,
        tile_height,
        tile_width,
        associated_image_names,
        image_description,
    ):
        self.height = height
        self.width = width
        self.xres = xres
        self.yres = yres
        self.depth = pyramid_depth
        self.resunit = resunit
        self.tile_height = tile_height
        self.tile_width = tile_width
        self.associated_image_names = associated_image_names
        self.image_description = image_description

        # These parameters need to be processed a bit more can't be set directly
        self.Q = self.extract_quality_factor()

        self.resunit = self.process_resunit_string()

    # TODO(ahmed.nadeem):
    # This function is kind of a hotfix, here is the problem it patches
    # Let's say we process and save a tiff file
    # It will read the resunit parameter correctly and save it however upon
    # reloading the same file again in the processor the resunit is not saved
    # properly due to shortage of time we are implmeneting this patch that it
    # always saves in one of the recognizable strings so that we don't have to
    # deal with the problem at all
    def process_resunit_string(self):
        print("Resunit is : ", self.resunit)
        lower_string = self.resunit.lower()
        # Most probably inch
        if "in" in lower_string:
            self.resunit = "inch"
        elif "cm" in lower_string or "centimeter" in lower_string:
            self.resunit = "cm"
        else:
            raise Exception("Resunit is not recognized")

        return self.resunit

    def extract_quality_factor(self):
        DEFAULT_Q = 80
        if not self.image_description.strip():
            print("Image Description tag is empty, assuming Q and returning")
            return DEFAULT_Q

        jpeg_index = self.image_description.find("JPEG/RGB")
        if jpeg_index < 0:
            print("JPEG/RGB string not found, Might need to guess Q")
            return DEFAULT_Q

        pipe_index = self.image_description.find("|")
        if pipe_index < 0:
            raise Exception("No | character found this description is not valid")

        if pipe_index < jpeg_index:
            raise Exception("The pipe is coming before jpeg, Not the expected format")

        self.Q = self.image_description[jpeg_index:pipe_index].replace(" ", "")

        equal_sign_index = self.Q.find("=")
        if equal_sign_index < 0:
            raise Exception("No = character found this description is not valid")

        Q = int(self.Q[equal_sign_index + 1 :])
        assert Q > 0

        # A little bit extra quality so we don't lose anything
        return min(Q + 5, 100)

    def print_data(self):
        print(
            "--------------------------------- Valid Metadata --------------------------------"
        )
        print("Height: ", self.height, " Width: ", self.width)
        print("XRes: ", str(self.xres) + "/mm", " YRes: ", str(self.yres) + "/mm")
        print("resunit: ", self.resunit, " unit in the original metadata")
        print("Tile Height: ", self.tile_height, " Tile Width: ", self.tile_width)
        print("Q Factor: ", self.Q)
        print("Associated images: ", self.associated_image_names)
        print("Image Description: ", self.image_description)
        print(
            "--------------------------------- End Metadata --------------------------------"
        )


def construct_metadata(image, input_image_path):
    # This maps each file type to the loader type
    class Loader(Enum):
        TIFF = "tiffload"
        SVS = "openslideload"

    resunit = ""
    pyramid_depth = 0
    input_image = None
    image_description = ""
    associated_image_names = ""

    associated_fields = image.get_fields()
    loader = image.get("vips-loader")
    if loader == Loader.TIFF.value:
        resunit_key = "resolution-unit"
        if resunit_key in associated_fields:
            resunit = image.get(resunit_key)
        else:
            print("resunit not found in file, setting to cm")
            resunit = "cm"

        pyramid_depth = image.get("n-pages")
        try:
            # Load it for extra info from openslide as tiffload does not support it
            input_image = pyvips.Image.openslideload(input_image_path, level=0)
        except pyvips.error.Error as e:
            ERROR_MESSAGE = "openslide2vips: unsupported slide format"
            # It is in a custom tif format we can support it
            if ERROR_MESSAGE in str(e):
                input_image = None
            else:
                print("Exception: \n", str(e))
                sys.exit(0)

    elif loader == Loader.SVS.value:
        resunit = image.get("tiff.ResolutionUnit")
        pyramid_depth = image.get("openslide.level-count")
        input_image = image

    if input_image:
        tile_height = input_image.get("openslide.level[0].tile-height")
        tile_width = input_image.get("openslide.level[0].tile-width")

        description_tag = "tiff.ImageDescription"
        image_description = (
            input_image.get(description_tag)
            if description_tag in input_image.get_fields()
            else ""
        )
        associated_image_names = input_image.get("slide-associated-images")
    else:
        image_description = ""
        associated_image_names = []

        DEFAULT_TILE_SIZE = 256
        print("Unconventinal tiff image assuming tile size ", DEFAULT_TILE_SIZE)

        tile_width = DEFAULT_TILE_SIZE
        tile_height = DEFAULT_TILE_SIZE

    return ImageMetadata(
        image.height,
        image.width,
        image.xres,
        image.yres,
        pyramid_depth,
        resunit,
        tile_height,
        tile_width,
        associated_image_names,
        image_description,
    )


def write_associated_images(metadata, input_image_path, output_image_path):
    image_names = metadata.associated_image_names
    if not image_names:
        print(
            "There are not associated images for this file returning, here is the string for reference"
        )
        print(image_names)
        return []

    # Split the string by the delimiter and strip spaces
    delimiter = ","
    image_names_list = [word.strip() for word in image_names.split(delimiter)]

    output_image_path_object = Path(output_image_path)
    # determine output file name before extension
    if "." not in output_image_path_object.name:
        raise Exception("File extension not present in path given: ", output_image_path)

    output_image_name = output_image_path_object.stem
    parent_dir = str(output_image_path_object.parent) + "/"

    written_files = []
    for associated_image_name in image_names_list:
        input_image = pyvips.Image.openslideload(
            input_image_path, associated=associated_image_name
        )

        write_file_path = (
            parent_dir + output_image_name + "_" + associated_image_name + ".tiff"
        )
        input_image.tiffsave(
            write_file_path,
            tile=False,  # Enable tiling
            pyramid=False,  # Generate a pyramidal TIFF
            compression="jpeg",  # Use JPEG compression (Should come from metadata as well but need more data to confirm as Q is linked)
        )

        written_files.append(write_file_path)

    return written_files


def process_slide_image(input_image_path, output_image_path):
    input_image = pyvips.Image.new_from_file(input_image_path)

    metadata = construct_metadata(input_image, input_image_path)
    metadata.print_data()

    # Only print the data and move on
    if not output_image_path:
        return

    # Create private copy necessary for pyvips
    xxres = input_image.get("xres")
    yyres = input_image.get("yres")
    out_image = input_image.copy(xres=xxres, yres=yyres)

    image_description_key = "tiff.ImageDescription"
    if out_image.get_typeof(image_description_key) == 0:
        out_image.set_type(
            pyvips.GValue.gstr_type, image_description_key, metadata.image_description
        )

    out_image.set(image_description_key, metadata.image_description)

    written_files = write_associated_images(
        metadata, input_image_path, output_image_path
    )
    # Save as a pyramidal TIFF with tiles
    out_image.tiffsave(
        output_image_path,
        tile=True,  # Enable tiling
        pyramid=True,  # Generate a pyramidal TIFF
        compression="jpeg",  # Use JPEG compression (Should come from metadata as well but need more data to confirm as Q is linked)
        Q=metadata.Q,  # JPEG quality
        tile_width=metadata.tile_width,  # Tile size (adjust as needed)
        tile_height=metadata.tile_height,
        resunit=metadata.resunit,
        strip=False,
        properties=True,
    )

    written_files.append(output_image_path)
    return written_files


if __name__ == "__main__":
    input_image_path = sys.argv[1]
    output_image_path = ""

    # We decrement from length because we have file name also included
    if (len(sys.argv) - 1) >= 2:
        output_image_path = sys.argv[2]

    process_slide_image(input_image_path, output_image_path)
