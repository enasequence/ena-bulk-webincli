# ena-read-validator
This validates read data to be submitted to the ENA using Webin-CLI.

This can be used individually, however has been created to carry out batch processing:
`python read_validator.py --spreadsheet [PATH_TO_SPREADSHEET]`
The spreadsheet should include the run name (e.g. prefix before .fastq), directory housing fastq file(s) and the manifest file:<br>
E.g.<br>
run  directory  manifest<br>
my_run   /pathto/fastqs/  /pathto/manifest.txt<br>

To run in batch, the script utilises available cores on the host machine.

Note:
Script requires adaptation to include Webin submission account credentials and the location of the webin-cli.jar file.
