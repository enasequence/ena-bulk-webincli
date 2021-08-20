#!/usr/bin/python3

__author__ = "Nadim Rahman"

import argparse, os, subprocess, sys
import pandas as pd
from joblib import Parallel, delayed
from datetime import datetime
import multiprocessing


######## Configuration - DOES NOT REQUIRE CHANGES IF USING DOCKER/SINGULARITY
WEBIN_CLI_JAR_PATH = '/webin-cli.jar'        # Full path to Webin-CLI jar file
########


# Mapping the field names between the submitted user metadata spreadsheet and the manifest file fields
spreadsheet_column_mapping = {'study_accession': 'study', 'sample_accession': 'sample', 'experiment_name': 'name', 'sequencing_platform': 'platform', 'sequencing_instrument': 'instrument', 'library_description': 'description'}


def get_args():
    """
    Handle script arguments
    :return: Script arguments
    """
    parser = argparse.ArgumentParser(prog='bulk_webincli.py', formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="""
        + =========================================================== +
        |  ENA Webin-CLI Bulk Submission Tool:                        |
        |  Python script to handle bulk submission of data through    |
        |  Webin-CLI.                                                 |    
        + =========================================================== +
        """)
    parser.add_argument('-u', '--username', help='Webin submission account username (e.g. Webin-XXXXX)', type=str, required=True)
    parser.add_argument('-p', '--password', help='password for Webin submission account', type=str, required=True)
    parser.add_argument('-g', '--geneticContext', help='Context for submission, options: genome, transcriptome, sequence, reads, taxrefset', choices=['genome', 'transcriptome', 'sequence', 'reads', 'taxrefset'], nargs='?', required=True)
    parser.add_argument('-s', '--spreadsheet', help='name of spreadsheet with metadata', type=str, required=True)
    parser.add_argument('-d', '--directory', help='parent directory of data files', type=str, required=False)
    parser.add_argument('-c', '--centerName', help='FOR BROKER ACCOUNTS ONLY - provide center name', type=str, required=False)
    parser.add_argument('-m', '--mode', type=str, help='options for mode are validate/submit', choices=['validate', 'submit'], nargs='?', required=False)
    parser.add_argument('-pc', '--parallel', help='Run submissions in parallel and specify the number of cores/threads to use, maximum cores/threads=10', type=int, required=False)
    parser.add_argument('-t', '--test', help='specify usage of test submission services', action='store_true')
    args = parser.parse_args()

    if args.mode is None:
        args.mode = "validate"      # If no mode is provided, default to Webin-CLI validate mode
    if args.directory is None:
        args.directory=""
    if args.centerName is None:
        args.centerName=""
    if args.parallel is None:
        args.parallel = False
    elif not 0 < args.parallel <= 10:
        print('> ERROR: Invalid number of cores/threads provided. This value should be between 1 and 10 (inclusive).')
        sys.exit()
    return args


def spreadsheet_format(spreadsheet_file):
    """
    Open the spreadsheet depending on the file-type
    :param spreadsheet_file: Path to spreadsheet
    :return: spreadsheet: Spreadsheet as a data frame to be manipulated
    """
    if spreadsheet_file.endswith(".xlsx") or spreadsheet_file.endswith(".xls"):
        spreadsheet = pd.read_excel(spreadsheet_file, header=0, index_col=False)
    elif spreadsheet_file.endswith(".csv"):
        spreadsheet = pd.read_csv(spreadsheet_file, header=0, sep=",", index_col=False)
    elif spreadsheet_file.endswith(".txt") or spreadsheet_file.endswith(".tsv"):
        spreadsheet = pd.read_csv(spreadsheet_file, header=0, sep="\t", index_col=False)
    return spreadsheet


def prepare_directories(directory):
    """
    Prepare directories for processing of submissions
    :param directory: Directory to be created
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


class GenerateManifests:
    """
    Class object that coordinates the generation of manifest files
    """
    def __init__(self, df, directory, context):
        self.df = df
        self.directory = directory
        self.context = context      # The context that Webin-CLI is to be used in (e.g. reads)
        self.manifest_dir = os.path.join(directory, "manifests")        # Define directory to hold all manifest files
        self.submission_dir = os.path.join(directory, "submissions")        # Define directory to hold all submission related files and sub-directories

    def row_processing(self, row):
        """
        Processing a row of data to obtain a dictionary of metadata in a row and a prefix for naming purposes
        :param row: A row of metadata for submission
        :return: manifest_file: Location and name of manifest file
        """
        row = row.dropna()      # Drop any fields with N/A in specified.
        row_meta = row.to_dict()        # Gets a row of metadata and keeps name of column as an index

        if self.context == 'reads':     # If reads are being submitted, get the name of the file to obtain a prefix
            prefix_field = row_meta.get('uploaded file 1')
        elif self.context == 'genome':      # If an un-annotated genome is being submitted get the name of the fasta file to obtain a prefix
            prefix_field = row_meta.get('fasta')

        prefix = os.path.splitext(os.path.splitext(os.path.basename(prefix_field))[0])[0]       # Get just the name of the run without the file extensions (indexing 0 required as both are tuples)
        manifest_file = os.path.join(self.manifest_dir, "Manifest_{}.txt".format(prefix))
        return manifest_file

    def create_manifest(self, metadata_content):
        """
        Create manifest file from metadata
        :param metadata_content: Dictionary of metadata to be converted into a dataframe before submission
        :return: manifest_content: Dataframe of the manifest file for submission
        """
        first_col = []
        second_col = []

        for item in metadata_content.items():
            field = item[0]
            value = item[1]
            if field in spreadsheet_column_mapping:
                field = spreadsheet_column_mapping.get(field)       # Convert the name of the field to one that is accepted by Webin-CLI
            elif field == "insert_size":
                value = int(value)
            elif field == "uploaded file 1" or "uploaded file 2":       # Specify the appropriate file type
                if ".fastq" in str(value) or ".fq" in str(value):
                    field = "fastq"
                elif ".cram" in str(value):
                    field = "cram"
                elif ".bam" in str(value):
                    field = "bam"
            field = field.upper()
            first_col.append(str(field))
            second_col.append(str(value))
        manifest_content = {'field': first_col, 'value': second_col}
        manifest_content = pd.DataFrame.from_dict(manifest_content)
        return manifest_content

    def write_manifests(self, manifest_file, manifest_content):
        """
        Write out the manifest file
        :param manifest_file: Path and name of manifest file
        :param manifest_content: Content of the manifest file
        :return: successful: List of successfully processed file(s)
        :return: failed: List of unsuccessfully processed file(s)
        """
        # Prepare manifest and submission directories
        prepare_directories(self.manifest_dir)
        prepare_directories(self.submission_dir)

        successful = []
        failed = []

        try:
            out = manifest_content.to_csv(manifest_file, sep="\t", index=False, header=False)
            successful.append(manifest_file)
        except Exception as e:
            failed.append(manifest_file)
            print('> ERROR during creation of manifest file: '+str(e))
        return successful, failed

    def generate_manifests(self):
        """
        Coordinate the generation of the manifest files for Webin-CLI submissions
        :return:
        """
        all_successful_files = []
        all_failed_files = []
        for index, row in self.df.iterrows():
            manifest_file = self.row_processing(row)       # Process the row of data - define some variables and files, etc.
            manifest_content = self.create_manifest(row)       # Create a dataframe of the manifest file content
            successful_files, failed_files = self.write_manifests(manifest_file, manifest_content)     # Write the dataframe to a file to generate a manifest file
            all_successful_files.append(successful_files)
            all_failed_files.append(failed_files)
        return all_successful_files, all_failed_files


class SubmissionWebinCLI:
    """
    Class object to submit or validate using Webin-CLI
    """
    def __init__(self, file, args):
        self.file = file
        self.args = args
        self.submission_dir = os.path.join(self.args.directory, "submissions")        # Define directory to hold all submission related files and sub-directories

    def file_prep(self):
        """
        Prepare and define files
        :return: output_dir: Directory to house report files.
        :return: log_path_err, log_path_out: Directory and file to store error and output
        :return: all_error_runs: File which will contain IDs of failed submissions
        """
        self.manifest_prefix = os.path.splitext(os.path.basename(self.file))[0]

        if self.args.directory == "":
            self.args.directory = "."

        self.output_dir = os.path.join(self.args.directory, 'manifests', self.manifest_prefix + '-report')
        self.log_path_err = os.path.join(self.output_dir, self.manifest_prefix + '.err')
        self.log_path_out = os.path.join(self.output_dir, self.manifest_prefix + '.out')
        print(self.log_path_err, self.log_path_out)

        self.all_error_runs = os.path.join(self.args.directory, 'failed_validation.txt')

    def construct_command(self):
        """
        Construct the command that is to be run for submission
        :return: command: String with command to be run for submission
        """
        if self.args.centerName == "":
            command = "mkdir -p {} && java -jar {} -context {} -userName {} -password {} -manifest {} -inputDir {} -outputDir {} -{}".format(
                self.output_dir, WEBIN_CLI_JAR_PATH, self.args.geneticContext, self.args.username, self.args.password, self.file, self.args.directory, self.submission_dir, self.args.mode
            )
        else:
            command = "mkdir -p {} && java -jar {} -context {} -userName {} -password {} -manifest {} -inputDir {} -outputDir {} -centerName '{}' -{}".format(
                self.output_dir, WEBIN_CLI_JAR_PATH, self.args.geneticContext, self.args.username, self.args.password, self.file, self.args.directory, self.submission_dir, self.args.centerName, self.args.mode
            )

        if self.args.test is True:
            command = command + " -test"
        return command

    def run_command(self, command):
        """
        Run the command
        :param command: Constructed command to be run
        :return: Standard output and error from the run command
        """
        print("*" * 100)
        print("""Command to be executed:
        {}""".format(command))
        print("*" * 100)
        p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        out, err = p.communicate()
        return out, err

    def post_process(self, output, error, timestamp):
        """
        Post process the output of the run command
        :param output: The standard output from the run command (.stdout)
        :param error: The standard error from the run command (.stderr)
        :param timestamp: The timestamp of the run command
        """
        with open(self.log_path_err, 'w') as err_file, open(self.log_path_out, 'w') as out_file, open(self.all_error_runs, 'a') as all_errors:
            if error:
                err_file.write(str(error.decode('UTF-8')))
                err_file.write('[{}] VALIDATION FAILED - {}\n'.format(timestamp, self.file))

                all_errors.write('*' * 100 +"\n")
                all_errors.write('[{}] {}\n'.format(timestamp, self.manifest_prefix))
                all_errors.write(str(error.decode('UTF-8')) + "\n")
                all_errors.write('*' * 100 + "\n")

            if output:
                if 'The submission has been validated successfully.' in str(output):
                    out_file.write('*' * 100 + "\n")
                    out_file.write(str(output.decode('UTF-8')))
                    out_file.write('[{}] VALIDATION SUCCESSFUL - {}\n'.format(timestamp, self.file))
                    out_file.write('*' * 100)
                else:
                    err_file.write(str(output.decode('UTF-8')))
                    err_file.write('[{}] VALIDATION FAILED - {}\n'.format(timestamp, self.file))

                    all_errors.write('*' * 100 + "\n")
                    all_errors.write("[{}] {}\n".format(timestamp, self.manifest_prefix))
                    all_errors.write(str(output.decode('UTF-8')))
                    all_errors.write('*' * 100 + "\n")


def submit_validate(file, args):
    """
    Coordinate the submission or validation using Webin-CLI
    :param file: File that has been successfully pre-processed - manifest file had been generated successfully
    :param args: Arguments provided to the tool
    """
    webincli_process = SubmissionWebinCLI(file, args)
    now = datetime.now()
    webincli_process.file_prep()     # Define files used during the submission process
    command = webincli_process.construct_command()      # Create the command to be processed
    out, err = webincli_process.run_command(command)        # Run the command and obtain output and error
    webincli_process.post_process(out, err, now)        # Post-process - save output accordingly



if __name__ == "__main__":
    args = get_args()       # Get arguments provided to the tool
    to_process = spreadsheet_format(args.spreadsheet)       # Create a dataframe of data to be processed (submitted or validated)

    # Generate the manifest files
    create_manifests = GenerateManifests(to_process, args.directory, args.geneticContext)
    processed, failed = create_manifests.generate_manifests()

    # Webin-CLI submission
    if args.parallel is not False:
        print('> Number of cores to use: {}'.format(args.parallel))
        Parallel(n_jobs=args.parallel)(delayed(submit_validate)(process[0], args) for process in processed)
    else:
        for process in processed:
            submit_validate(process[0], args)
