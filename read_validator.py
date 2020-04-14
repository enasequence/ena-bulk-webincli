import argparse, os, subprocess
import pandas as pd
from joblib import Parallel, delayed
import multiprocessing


######## Configuration - Assign these values before running the script
WEBIN_CLI_JAR_PATH = 'pathto/webin-cli-2.1.0.jar'

num_cores = multiprocessing.cpu_count()
print('Number of cores to use: {}'.format(num_cores))
########



def get_args():
    """
    Handle script arguments
    :return: Script arguments
    """
    parser = argparse.ArgumentParser(description="Validate runs submitted")
    parser.add_argument('-u', '--username', help='Webin submission account username (e.g. Webin-XXXXX)', type=str, required=True)
    parser.add_argument('-p', '--password', help='password for Webin submission account.', type=str, required=True)
    parser.add_argument('-d', '--directory', help='parent directory of runs to be submitted')
    parser.add_argument('-r', '--run', help='accession of run to be processed', type=str, required=False)
    parser.add_argument('-m', '--manifest', help='manifest file used to submit the run', type=str, required=False)
    parser.add_argument('-s', '--spreadsheet', help="spreadsheet (TSV file) with stored values for batch processing", type=str, required=False)
        # If using spreadsheet, these are columns used:
        #       1. Run (Name of the run (everything minus the suffix - e.g.fastq.gz))
        #       2. Directory (Directory where fastq files are housed)
        #       3. Manifest (Full path to manifest file - including name of manifest)
    args = parser.parse_args()
    return args


def webin_cli_validate(WEBIN_USERNAME, WEBIN_PASSWORD, run_id, manifest_file, upload_file_dir):
    """
    Run Webin-CLI validation of reads
    :param manifest_file: Path to manifest file used when submitting reads
    :return:
    """
    output_dir = os.path.join(upload_file_dir, run_id + '-report')      # Directory to house validation report files
    log_path_err = os.path.join(output_dir, run_id + '.err')
    log_path_out = os.path.join(output_dir, run_id + '.out')
    all_error_runs = os.path.join(upload_file_dir, 'failed_validation.txt')      # File to note runs that did not pass validation
    command = "mkdir -p {} && java -jar {} -context reads -userName {} -password {} -manifest {} -inputDir {} -outputDir {} -validate".format(
        output_dir, WEBIN_CLI_JAR_PATH, WEBIN_USERNAME, WEBIN_PASSWORD, manifest_file, upload_file_dir, output_dir
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
            run_file.write(run_id+"\n")
        if out:
            if 'The submission has been validated successfully.' in str(out):
                out_file.write(str(out))
                out_file.write('VALIDATION SUCCESSFUL')
            else:
                err_file.write(str(out))
                err_file.write(str(err))
                err_file.write('VALIDATION FAILED')
                run_file.write(run_id+"\n")



if __name__ == '__main__':
    args = get_args()
    webin_username = args.username
    webin_password = args.password


    if args.spreadsheet:
        # Batch validate runs using spreadsheet
        to_validate = pd.read_csv(args.spreadsheet, sep='\t')
        # for index, row in to_validate.iterrows():
        #     webin_cli_validate(row[0], row[1], row[2])      # Parallelise this
        results = Parallel(n_jobs=num_cores)(delayed(webin_cli_validate)(webin_username, webin_password, row[0], row[2], row[1]) for index,row in to_validate.iterrows())
    else:
        # Run validation on script arguments
        run_id = args.run
        manifest_file = args.manifest
        upload_file_dir = args.directory
        webin_cli_validate(run_id, manifest_file, upload_file_dir)      # Validate the run files in a folder
