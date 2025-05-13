# Diagnostic Anonymizer
This module is responsible for separting the different images associated in 
1. *.tiff 
2. *.svs

So that personal information is stripped from the original file and only diagnostic related data is present in the resulting .tiff file

### Note this API currently only integrates with Amazon S3 storage.
##### Here is a short gist of how it works
1. The API expects an Amazon S3 Object URI
2. The API downloads the file from amazon
3. Separates them into separate files
4. Writes them back to Amazon S3 storage in processed folder with folder name matching the input file name
5. Deletes everything on local storage
