# ENA Webin-CLI Bulk Submission Tool
### Introduction
This tool is a wrapper to bulk submit read, un-annotated genome, targeted sequence or taxonomic reference data to the ENA using Webin-CLI. 

The tool requires an appropriate metadata spreadsheet which it uses to generate manifest files for the user and validate or submit their submission. The tool does not handle study and sample registration, therefore visit [ENA Submissions Documentation](https://ena-docs.readthedocs.io/en/latest/submit/general-guide.html) for more information on this. The documentation also provides information on manifest file fields for your type of submission (which correlate to the headers in the spreadsheet file).

An example template spreadsheet has been provided (example_template_input.txt). This file is a tab-delimited text file, however the script also consumes spreadsheets in native MS Excel formats (e.g. .xslx) or comma-separated (.csv).

### Usage

#### Docker
To ease in usage, the tool has been containerised using [Docker](https://www.docker.com/). The only requirement is to have Docker [installed](https://docs.docker.com/get-docker/). Once installed, run the following commands to setup:

1. Clone the repository:
`git clone https://github.com/nadimm-rahman/ena-bulk-webincli.git && cd ena-bulk-webincli`
2. Build the docker image:
`docker build --tag ena-bulk-webincli .`
3. Ready to go! Run the tool using docker using the following command:
`docker run --rm ena-bulk-webincli -h` (for help)

#### Other
To use the tool without Docker:

1. Clone the repository:
`git clone https://github.com/nadimm-rahman/ena-bulk-webincli.git && cd ena-bulk-webincli`
2. Download the latest version of [Webin-CLI](https://github.com/enasequence/webin-cli/releases) installed.
3. Download tool dependencies listed below.
4. Edit the 'Configuration' section at the top of bulk_webincli.py to include the full path to the Webin-CLI jar file and whether parallel processing should be carried out.
5. Run the tool using `python bulk_webincli.py --help`(for help)

Mandatory arguments include Webin submission account username and password, genetic context and metadata spreadsheet. Note that the `--test/-t` flag can be specified to use Webin test submission services.

### Dependencies
The tool runs using [Python3.6+](https://www.python.org/downloads/) and requires installation of [Python Pandas](https://pandas.pydata.org/) and [joblib](https://joblib.readthedocs.io/en/latest/). This can be installed in a [virtual environment](https://docs.python.org/3/tutorial/venv.html).
