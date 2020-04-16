# ena-read-validator
This validates read data to be submitted to the ENA using Webin-CLI.

This can be used individually, however has been created to carry out batch processing:
`python read_validator.py --spreadsheet [PATH_TO_SPREADSHEET]`
See example_template_input.txt to see the the format of the spreadsheet.

To run in batch, the script utilises available cores on the host machine.

Note:
Script requires adaptation to include the location of the webin-cli.jar file.
