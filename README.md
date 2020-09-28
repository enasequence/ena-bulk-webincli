# ena-read-validator
### Introduction
This script is a wrapper to bulk submit read, un-annotated genome, targeted sequence or taxonomic reference data to the ENA using Webin-CLI.

An example template spreadsheet has been provided (example_template_input.txt). This file is a tab-delimited text file, however the script also consumes spreadsheets in native MS Excel formats (e.g. .xslx) or comma-separated (.csv).

This script creates manifest files for the user using the metadata specified in the spreadsheet. Note that a study or studies and sample(s) must be registered prior to running this script. The study and sample accessions(s) should be defined in the spreadsheet. Visit ENA read the docs (https://ena-docs.readthedocs.io/en/latest/submit/general-guide.html) to obtain information on the manifest file fields for your type of submission which will correlate to the headers in the spreadsheet file.

To run in batch, the script utilises available cores on the host machine.

### Usage

#### Docker
To ease in usage, the tool has been containerised using [Docker](https://www.docker.com/). The only requirement is to have Docker [installed](https://docs.docker.com/get-docker/). Once installed, run the following commands to setup:

1. Pull the codebase using git clone:
`git clone https://github.com/nadimm-rahman/ena-read-validator.git && cd ena-read-validator`
2. Build the docker image:
`docker build --tag ena-bulk-webincli .`
3. Ready to go! Run the tool using docker using the following command:
`docker run --rm ena-bulk-webin-cli`

#### Python
Before running the script, ensure you have Webin-CLI installed (https://github.com/enasequence/webin-cli/releases) and provide the full path to the Webin-CLI .jar file in the configuration section at the top of the read_validatory.py script. Additionally, by default, the script processes runs sequentially, however can be run in parallel by changing the parallel value to 'True' in the configuration section. 

To see the arguments and help in usage of the script:
`python read_validator.py --help`

Mandatory arguments include Webin submission account username and password, genetic context and metadata spreadsheet. Note that the `--test/-t` flag can be specified to use Webin test submission services.

### Requirements
The script runs using Python3.6+ and requires installation of [Python Pandas](https://pandas.pydata.org/) and [joblib](https://joblib.readthedocs.io/en/latest/). This can be installed in a [virtual environment](https://docs.python.org/3/tutorial/venv.html).
