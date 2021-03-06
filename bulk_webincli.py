#!/usr/bin/python3

import argparse, os, subprocess, sys
import pandas as pd
from joblib import Parallel, delayed
from datetime import datetime
import multiprocessing


######## Configuration
WEBIN_CLI_JAR_PATH = 'pathto/webin-cli.jar'        # Full path to Webin-CLI jar file
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
        args.mode = "validate"
    if args.directory is None:
        args.directory=""
    if args.centerName is None:
        args.centerName=""
    if args.parallel is None:
        args.parallel = False
    elif not 0 < args.parallel < 10:
        print('> ERROR: Invalid number of cores/threads provided. This value should be between 1 and 10 (inclusive).')
        sys.exit()
    return args


def spreadsheet_format(spreadsheet_file):
    """
    Open the spreadsheet depending on the file-type
    :param spreadsheet_file: Path to spreadsheet
    :return:
    """
    if spreadsheet_file.endswith(".xlsx") or spreadsheet_file.endswith(".xls"):
        spreadsheet = pd.read_excel(args.spreadsheet, header=0, index_col=False)
    elif spreadsheet_file.endswith(".csv"):
        spreadsheet = pd.read_csv(args.spreadsheet, header=0, sep=",", index_col=False)
    elif spreadsheet_file.endswith(".txt") or spreadsheet_file.endswith(".tsv"):
        spreadsheet = pd.read_csv(args.spreadsheet, header=0, sep="\t", index_col=False)
    return spreadsheet


def prepare_directories(directory):
    """
    Prepare directories for processing of submissions
    :return:
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


def create_manifest(row, directory=""):
    """
    Create a manifest file for each submission
    :param row: Row of metadata from spreadsheet which will be used for the manifest file(s) in submission/validation
    :param directory: Parent directory of data files, to save manifest files to
    :return: List of successful creations of manifest file
    """
    row = row.dropna()
    experiment_meta = row.to_dict()     # Gets a row of data and keeps name of column as an index
    manifest_dir = os.path.join(directory, "manifests")
    submission_dir = os.path.join(directory, "submissions")

    if 'uploaded file 1' in experiment_meta.keys():
        to_process = experiment_meta.get('uploaded file 1')  # If reads are being submitted, get the name of the file to obtain a prefix
    elif 'fasta' in experiment_meta.keys():
        to_process = experiment_meta.get('fasta')  # If an un-annotated genome is being submitted get the name of the fasta file to obtain a prefix

    prefix = os.path.splitext(os.path.splitext(os.path.basename(to_process))[0])[0]       # Get just the name of the run without the file extensions (indexing 0 required as both are tuples)
    manifest_file = os.path.join(manifest_dir, "Manifest_{}.txt".format(prefix))
    successful = []
    failed = []

    first_col = []
    second_col = []
    for item in experiment_meta.items():
        field = item[0]
        value = item[1]
        if field in spreadsheet_column_mapping:
            field = spreadsheet_column_mapping.get(field)
        elif field == "insert_size":
            value = int(value)      # Required to remove any decimal points for the insert size value
        elif field == "uploaded file 1" or "uploaded file 2":
            if ".fastq" in str(value) or ".fq" in str(value):
                field = 'fastq'
            elif ".cram" in str(value):
                field = 'cram'
            elif ".bam" in str(value):
                field = 'bam'
        field = field.upper()
        first_col.append(str(field))
        second_col.append(str(value))
    manifest_content = {'field': first_col, 'value': second_col}
    manifest_content = pd.DataFrame.from_dict(manifest_content)

    prepare_directories(manifest_dir)
    prepare_directories(submission_dir)

    try:
        out = manifest_content.to_csv(manifest_file, sep='\t', index=False, header=False)
        successful.append(manifest_file)
    except Exception as e:
        failed.append(to_process)
        print("> ERROR during creation of manifest file: "+str(e))
    return successful, failed



def webin_cli_validate_submit(WEBIN_USERNAME, WEBIN_PASSWORD, manifest_file, context, mode, test, upload_file_dir="", center_name=""):
    """
    Run Webin-CLI validation of reads
    :param WEBIN_USERNAME: Webin submission account username (e.g. Webin-XXXXX)
    :param WEBIN_PASSWORD: Webin submission account password
    :param manifest_file: Path to manifest file used when submitting reads
    :param context: The context of submission, e.g. reads
    :param mode: Mode of action for Webin-CLI (e.g. validate or submit)
    :param test: Specify usage of test Webin-CLI
    :param upload_file_dir: Path of directory housing data files
    :param center_name: Center name (for brokered submissions only)
    :return:
    """
    manifest_prefix = os.path.splitext(os.path.basename(manifest_file))[0]        # Get the file name first and then from this, get everything except the extension
    now = datetime.now()

    if upload_file_dir == "":
        upload_file_dir = "."       # To represent the current working directory

    output_dir = os.path.join(upload_file_dir, 'manifests', manifest_prefix + '-report')      # Directory to house validation report files
    log_path_err = os.path.join(output_dir, manifest_prefix + '.err')
    log_path_out = os.path.join(output_dir, manifest_prefix + '.out')
    print(log_path_err, log_path_out)
    all_error_runs = os.path.join(upload_file_dir, 'failed_validation.txt')      # File to note runs that did not pass validation
    submissions = os.path.join(upload_file_dir, 'submissions')

    if center_name == "":
        command = "mkdir -p {} && java -jar {} -context {} -userName {} -password {} -manifest {} -inputDir {} -outputDir {} -{}".format(
            output_dir, WEBIN_CLI_JAR_PATH, context, WEBIN_USERNAME, WEBIN_PASSWORD, manifest_file, upload_file_dir, submissions, mode
        )
    else:
        command = "mkdir -p {} && java -jar {} -context {} -userName {} -password {} -manifest {} -inputDir {} -outputDir {} -centerName '{}' -{}".format(
            output_dir, WEBIN_CLI_JAR_PATH, context, WEBIN_USERNAME, WEBIN_PASSWORD, manifest_file, upload_file_dir, output_dir, center_name,
            mode
        )

    if test is True:
        command = command + " -test"

    print("*" * 100)
    print("""Command to be executed:
    {}""".format(command))
    print("*" * 100)
    p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    out, err = p.communicate()
    with open(log_path_err, 'w') as err_file, open(log_path_out, 'w') as out_file, open(all_error_runs, 'a') as all_errors:
        if err:
            err_file.write(str(err.decode('UTF-8')))
            err_file.write('[{}] VALIDATION FAILED\n'.format(now))

            all_errors.write('*' * 100 + "\n")
            all_errors.write("[{}] {}\n".format(now, manifest_file))
            all_errors.write(str(err.decode('UTF-8')) + "\n")
            all_errors.write('*' * 100 + "\n")

        if out:
            if 'The submission has been validated successfully.' in str(out):
                out_file.write('*' * 100 + "\n")
                out_file.write(str(out.decode('UTF-8')))
                out_file.write('[{}] VALIDATION SUCCESSFUL\n'.format(now))
                out_file.write('*' * 100)
            else:
                err_file.write(str(out.decode('UTF-8')))
                err_file.write('[{}] VALIDATION FAILED\n'.format(now))

                all_errors.write('*' * 100 + "\n")
                all_errors.write("[{}] {}\n".format(now, manifest_file))
                all_errors.write(str(out.decode('UTF-8')))
                all_errors.write('*' * 100 + "\n")



if __name__ == '__main__':
    args = get_args()
    webin_username = args.username
    webin_password = args.password

    to_process = spreadsheet_format(args.spreadsheet)

    all_successful_files = []
    all_failed_files = []
    for index, row in to_process.iterrows():
        successful_files, failed_files = create_manifest(row, args.directory)       # Create manifest files for each run to be submitted (represented by a row in the user spreadsheet)
        all_successful_files.append(successful_files)
        all_failed_files.append(failed_files)

    if args.parallel is not False:
        print('Number of cores to use: {}'.format(args.parallel))
        Parallel(n_jobs=args.parallel)(delayed(webin_cli_validate_submit)(webin_username, webin_password, file[0], args.geneticContext, args.mode, args.test, args.directory, args.centerName) for file in all_successful_files)
    else:
        for file in all_successful_files:
            webin_cli_validate_submit(webin_username, webin_password, file[0], args.geneticContext, args.mode, args.test, args.directory, args.centerName)     # Validate/submit runs
