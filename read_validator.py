import argparse, os, subprocess
import pandas as pd
from joblib import Parallel, delayed
from pathlib import Path
import multiprocessing


######## Configuration - Assign these values before running the script
WEBIN_CLI_JAR_PATH = 'pathto/webin-cli-2.2.3.jar'
########

num_cores = multiprocessing.cpu_count()
print('Number of cores to use: {}'.format(num_cores))

# Mapping the field names between the submitted user metadata spreadsheet and the manifest file fields
spreadsheet_column_mapping = {'study_accession': 'study', 'sample_accession': 'sample', 'experiment_name': 'name', 'sequencing_platform': 'platform', 'sequencing_instrument': 'instrument', 'library_description': 'description'}


def get_args():
    """
    Handle script arguments
    :return: Script arguments
    """
    parser = argparse.ArgumentParser(description="Validate runs submitted")
    parser.add_argument('-u', '--username', help='Webin submission account username (e.g. Webin-XXXXX)', type=str, required=True)
    parser.add_argument('-p', '--password', help='password for Webin submission account.', type=str, required=True)
    parser.add_argument('-d', '--directory', help='parent directory of data files', type=str, required=False)
    parser.add_argument('-c', '--centerName', help='FOR BROKER ACCOUNTS ONLY - provide center name', type=str, required=False)
    parser.add_argument('-s', '--spreadsheet', help='name of spreadsheet with metadata', type=str, required=True)
    parser.add_argument('-m', '--mode', type=str, help='options for mode are validate/submit', choices=['validate', 'submit'], nargs='?', required=False)
    args = parser.parse_args()

    if args.mode is None:
        args.mode = "validate"
    if args.directory is None:
        args.directory=""
    if args.centerName is None:
        args.centerName=""
    return args


def create_manifest(row, directory=""):
    """
    Create a manifest file for each submission
    :param experiment_meta: Row of metadata from spreadsheet which will be used for the manifest file(s) in submission/validation
    :param directory: Parent directory of data files, to save manifest files to
    :return: List of successful creations of manifest file
    """
    row = row.dropna()
    experiment_meta = row.to_dict()     # Gets a row of data and keeps name of column as an index

    to_process = experiment_meta.get('uploaded file 1')
    prefix = os.path.splitext(os.path.splitext(to_process)[0])[0]       # Get just the name of the run without the file extensions (indexing 0 required as both are tuples)
    manifest_file = os.path.join(directory, "Manifest_{}.txt".format(prefix))
    successful = set([])        # Created sets to add to, so unique values are kept in this list
    failed = set([])

    for item in experiment_meta.items():
        field = item[0]
        value = item[1]
        if field in spreadsheet_column_mapping:
            field = spreadsheet_column_mapping.get(field)           # Get the manifest file field name for the spreadsheet column header
        elif field == "uploaded file 1" or "uploaded file 2":
            if ".fastq" in str(value) or ".fq" in str(value):
                field = 'fastq'
            elif ".cram" in str(value):
                field = 'cram'
            elif ".bam" in str(value):
                field = 'bam'
        field = field.upper()
        try:
            with open(manifest_file, 'a') as out:
                out.write(str(field)+"\t"+str(value)+"\n")
            if to_process not in successful:
                successful.add(manifest_file)
        except Exception as e:
            if to_process not in set(failed):
                failed.add(to_process)
            print("> ERROR during creation of manifest file: "+str(e))
    return list(successful), list(failed)



def webin_cli_validate_submit(WEBIN_USERNAME, WEBIN_PASSWORD, manifest_file, mode, upload_file_dir="", center_name=""):
    """
    Run Webin-CLI validation of reads
    :param WEBIN_USERNAME: Webin submission account username (e.g. Webin-XXXXX)
    :param WEBIN_PASSWORD: Webin submission account password
    :param manifest_file: Path to manifest file used when submitting reads
    :param mode: Mode of action for Webin-CLI (e.g. validate or submit)
    :param upload_file_dir: Path of directory housing data files
    :return:
    """
    manifest_prefix = os.path.splitext(manifest_file)[0]        # Get a prefix to create unique manifest file names

    output_dir = os.path.join(upload_file_dir, manifest_prefix+ '-report')      # Directory to house validation report files
    log_path_err = os.path.join(output_dir, manifest_prefix + '.err')
    log_path_out = os.path.join(output_dir, manifest_prefix + '.out')
    all_error_runs = os.path.join(upload_file_dir, 'failed_validation.txt')      # File to note runs that did not pass validation

    if center_name == "":
        command = "mkdir -p {} && java -jar {} -context reads -userName {} -password {} -manifest {} -inputDir {} -outputDir {} -{}".format(
            output_dir, WEBIN_CLI_JAR_PATH, WEBIN_USERNAME, WEBIN_PASSWORD, manifest_file, upload_file_dir, output_dir, mode
        )
    else:
        command = "mkdir -p {} && java -jar {} -context reads -userName {} -password {} -manifest {} -inputDir {} -outputDir {} -centerName {} -{}".format(
            output_dir, WEBIN_CLI_JAR_PATH, WEBIN_USERNAME, WEBIN_PASSWORD, manifest_file, upload_file_dir, output_dir, center_name,
            mode
        )

    print("*" * 100)
    print("""Command to be executed:
    {}""".format(command))
    print("*" * 100)
    p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    out, err = p.communicate()
    with open(log_path_err, 'w') as err_file, open(log_path_out, 'w') as out_file, open(all_error_runs, 'w') as run_file:
        if err:
            err_file.write(str(err))
            err_file.write('VALIDATION FAILED')
            run_file.write(manifest_file+"\n")
        if out:
            if 'The submission has been validated successfully.' in str(out):
                out_file.write(str(out))
                out_file.write('VALIDATION SUCCESSFUL')
            else:
                err_file.write(str(out))
                err_file.write(str(err))
                err_file.write('VALIDATION FAILED')
                run_file.write(manifest_file+"\n")



if __name__ == '__main__':
    args = get_args()
    webin_username = args.username
    webin_password = args.password

    to_process = pd.read_excel(args.spreadsheet, header=1)
    spreadsheet = to_process[~to_process['Unnamed: 0'].str.contains("#", na=False)]     # Remove rows which contain '#' in their column values (i.e. the guide rows)
    if 'Unnamed: 0' in spreadsheet.columns:
        runs = spreadsheet.drop('Unnamed: 0', axis='columns')      # Drop the first empty column
    else:
        print('Column does not exist, does not require dropping...')

    all_successful_files = []
    all_failed_files = []
    for index, row in runs.iterrows():
        successful_files, failed_files = create_manifest(row, args.directory)       # Create manifest files for each run to be submitted (represented by a row in the user spreadsheet)
        all_successful_files.append(successful_files)
        all_failed_files.append(failed_files)

    for file in all_successful_files:
        # Need to extract the file path as all_successful_files is a list of lists
        webin_cli_validate_submit(webin_username, webin_password, file[0], args.mode, args.directory, args.centerName)     # Validate/submit runs


    # if args.spreadsheet:
    #     # Batch validate runs using spreadsheet
    #     to_validate = pd.read_csv(args.spreadsheet, sep='\t')
    #     # for index, row in to_validate.iterrows():
    #     #     webin_cli_validate(row[0], row[1], row[2])      # Parallelise this
    #     results = Parallel(n_jobs=num_cores)(delayed(webin_cli_validate)(webin_username, webin_password, row[0], row[2], row[1]) for index,row in to_validate.iterrows())
    # else:
    #     # Run validation on script arguments
    #     run_id = args.run
    #     manifest_file = args.manifest
    #     upload_file_dir = args.directory
    #     webin_cli_validate(run_id, manifest_file, upload_file_dir)      # Validate the run files in a folder



# MANIFEST FILE FIELDS:
# STUDY
# SAMPLE
# NAME
# PLATFORM
# INSTRUMENT
# INSERT_SIZE
# LIBRARY_NAME
# LIBRARY_SOURCE
# LIBRARY_SELECTION
# LIBRARY_STRATEGY
# DESCRIPTION
# FASTQ/BAM/CRAM

# INSTALLATION
# python pandas
# xlrd-1.2.0
