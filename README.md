# ena-read-validator
### Introduction
This script validates and/or submits read data to the ENA using Webin-CLI.

An example template spreadsheet has been provided (example_template_input.txt). This file is a tab-delimited text file, however the script also consumes spreadsheets in native MS Excel formats (e.g. .xslx) or comma-separated (.csv).

This script creates manifest files for the user using the metadata specified in the spreadsheet. Note that a study or studies and sample(s) must be registered prior to running this script. The study and sample accessions(s) should be defined in the spreadsheet.

To run in batch, the script utilises available cores on the host machine.

### Usage
Before running the script, ensure you have Webin-CLI installed (https://github.com/enasequence/webin-cli/releases) and provide the full path to the Webin-CLI .jar file in the configuration section at the top of the read_validatory.py script. Additionally, by default, the script processes runs in parallel, however can be run sequentially by changing the parallel value to 'False' in the configuration section. 

To see the arguments and help in usage of the script:
`python read_validator.py --help`

Mandatory arguments include Webin submission account username and password and metadata spreadsheet. Note that the `--test/-t` flag can be specified to use Webin test submission services.

###Requirements
The script requires installation of Python Pandas (https://pandas.pydata.org/). This can be installed in a virtual environment (https://docs.python.org/3/tutorial/venv.html).
