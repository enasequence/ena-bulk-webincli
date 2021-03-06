# ENA Webin-CLI Bulk Submission Tool
### Introduction
This tool is a wrapper to bulk submit read, un-annotated genome, targeted sequence or taxonomic reference data to the ENA using Webin-CLI. 

The tool requires an appropriate metadata spreadsheet which it uses to generate manifest files for the user and validate or submit their submission. The tool does not handle study and sample registration, therefore visit [ENA Submissions Documentation](https://ena-docs.readthedocs.io/en/latest/submit/general-guide.html) for more information on this. The documentation also provides information on manifest file fields for your type of submission (which correlate to the headers in the spreadsheet file).

An example template spreadsheet has been provided (example_template_input.txt). This file is a tab-delimited text file, however the script also consumes spreadsheets in native MS Excel formats (e.g. .xslx) or comma-separated (.csv).

### Installation

#### Docker
To ease in usage, the tool has been containerised using [Docker](https://www.docker.com/). The only requirement is to have Docker [installed](https://docs.docker.com/get-docker/). Once installed, run the following commands to setup:

1. Clone the repository:
`git clone https://github.com/nadimm-rahman/ena-bulk-webincli.git && cd ena-bulk-webincli`
2. Build the docker image:
`docker build --tag ena-bulk-webincli .`
3. Ready to go! Run the tool using docker using the following command:
`docker run --rm -v <LOCAL_DATA_DIRECTORY>:/data ena-bulk-webincli -h` (for help)

<LOCAL_DATA_DIRECTORY> is recommended to be the directory or parent directory on your machine containing your data files to submit. Below is an example command which would submit read data to the test server:
`docker run --rm -v pathto/data:/data ena-bulk-webincli -u Webin-XXXX -p XXXX -g reads -s example_template_read.txt -d /data -m submit -t`

Note: For data files to be submitted, relative file paths in accordance to `<LOCAL_DATA_DIRECTORY>` must be provided within the input spreadsheet.


#### Other
To use the tool without Docker:

1. Clone the repository:
`git clone https://github.com/nadimm-rahman/ena-bulk-webincli.git && cd ena-bulk-webincli`
2. Download the latest version of [Webin-CLI](https://github.com/enasequence/webin-cli/releases) installed.
3. Download tool dependencies listed below.
4. Edit the 'Configuration' section at the top of bulk_webincli.py to include the full path to the Webin-CLI jar file and whether parallel processing should be carried out.
5. Run the tool using `python bulk_webincli.py --help`(for help)

The script accepts full paths to files (to be submitted e.g. fastq/fasta) within the input spreadsheet. To control location of outputs, a specific directory can be provided using the `--directory/-d` parameter, where the folders listed below will be generated.

### Usage

Mandatory arguments include Webin submission account username and password, genetic context and metadata spreadsheet. Note that the `--test/-t` flag can be specified to use Webin test submission services.

By default, the script utilises two additional directories:
1. 'manifests' - which houses all generated manifest files and report files.
2. 'submissions' - housing all validation and submission related reports and files, includes analysis and receipt XMLs of submissions.

### Dependencies
The tool runs using [Python3.6+](https://www.python.org/downloads/) and requires installation of [Python Pandas](https://pandas.pydata.org/) and [joblib](https://joblib.readthedocs.io/en/latest/). This can be installed in a [virtual environment](https://docs.python.org/3/tutorial/venv.html).
