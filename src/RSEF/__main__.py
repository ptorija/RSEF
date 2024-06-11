# TODO find appropiate names
import json
from RSEF.object_creator.create_downloadedObj import json_to_downloaded_obj
from RSEF.repofrompaper.utils.constants import PROCESSED_PATH, DOWNLOADED_PATH, ASSES_PATH
from .object_creator.pipeline import multi_doi_search, paper_objects_search, single_doi_pipeline
from . import __version__
import click
import os
import logging
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
VALID_EXTENSIONS = ['.txt', '.json']

# Set up logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(__version__)
def cli():
    """
    RRRRRRRRR   SSSSSSSSS  EEEEEEEEE   FFFFFFFFF\n
    RRR   RRR  SSS    SSS  EEE         FFF\n
    RRR   RRR  SSS         EEE         FFF\n
    RRRRRRRRR  SSSSSSSSS   EEEEEEE     FFFFFFF\n
    RRR RRR         SSSS   EEE         FFF\n
    RRR  RRR  SSS    SSS   EEE         FFF\n
    RRR   RRR  SSSSSSSSS   EEEEEEEEE   FFF\n

    Research Software Extraction Framework (RSEF)\n
    Find and assess Research Software within Research papers.\n

    Usage:\n
    1. (assess)     Assess doi for unidirectionality or bidirectionality\n
    2. (download)   Download PDF (paper) from a doi or list\n
    3. (process)    Process downloaded pdf to find urls and abstract\n

    """
    pass

# #TODO
# @cli.command()
# def configure():
#     """This creates a ~/.soca/configure.ini file"""
#     #TODO defaults check
#     url = click.prompt("URL to database",default = "http://localhost:8086")
#     bucket = click.prompt("Bucket", default = "my-bucket")
#     org = click.prompt("Organisation",default = "org_name")
#     token = click.prompt("Token", default = "")
#     if len(token) == 0:
#         click.echo("No token given, please enter token or press enter")
#         token = click.prompt("Token", default = "")
#     try:
#         from soca.commands import create_config
#
#         create_config.create_config(url,bucket,token,org)
#         click.secho(f"Success", fg="green")
#     except Exception as e:
#         click.secho(f"Error: "+str(e),fg="red")
#         exit(1)


@cli.command()
@click.option('--input', '-i', required=True, help="DOI, path to .txt list of DOIs or path to processed_metadata.json",
              metavar='<name>')
@click.option('--output', '-o', default="output", show_default=True, help="Output csv file", metavar='<path>')
@click.option('--unidir', '-U', is_flag=True, default=False, help="Unidirectionality")
@click.option('--bidir', '-B', is_flag=True, default=False, help="Bidirectionality")
def assess(input, output, unidir, bidir):

    # Clear the content of the url_search_output.json
    url_search_output_path = output + ASSES_PATH
    if os.path.exists(url_search_output_path):        
        with open(url_search_output_path, 'w') as file:
            file.truncate(0)

    if input.endswith(".txt") and os.path.exists(input):
        output_path = multi_doi_search(dois_txt=input, output_dir=output,
                                       unidir=unidir, bidir=bidir)
    elif input.endswith(".json") and os.path.exists(input):
        with open(input, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        if isinstance(data, list) and 'implementation_urls' in data[0]:
            # processed_metadata.json
            output_path = paper_objects_search(
                papers_json=input, output_dir=output, unidir=unidir, bidir=bidir)
            
        elif isinstance(data, list) and 'primary_location' in data[0]:
            # DOI-Extractor-OEG JSON
            existing_oeg_papers = 'src/RSEF/existing_oeg_papers/papers.json'
        
            # Add existing papers from OEG
            merge_json_files(input, existing_oeg_papers)

            processed_papers = process(input= None, json=input, output=output)
            processed_papers_path = processed_papers + PROCESSED_PATH
            output_path = paper_objects_search(
                papers_json=processed_papers_path, output_dir=output, unidir=unidir, bidir=bidir)

        elif isinstance(data, list) and 'file_path' in data:
            # downloaded_metadata.json
            process(input=input, json=None, output=output)
            output_path = paper_objects_search(
                papers_json=input, output_dir=output, unidir=unidir, bidir=bidir)

        else:
            raise ValueError("Unrecognized JSON format")

    else:
        output_path = single_doi_pipeline(
            doi=input, output_dir=output, unidir=unidir, bidir=bidir)

    log.info(f"Output saved to: {output_path}")


@cli.command()
@click.option('--input', '-i', required=True, help="DOI or path to .txt list of DOIs", metavar='<name>')
@click.option('--output', '-o', default="./", show_default=True, help="Output Directory ", metavar='<path>')
def download(input, output):
    from .object_creator.create_downloadedObj import doi_to_downloadedJson, dois_txt_to_downloadedJson

    if input.endswith(".txt") and os.path.exists(input):
        dois_txt_to_downloadedJson(dois_txt=input, output_dir=output)
    else:
        try:
            doi_to_downloadedJson(doi=input, output_dir=output)
        except Exception as e:
            log.error(e)
        return


def process(input, json, output):
    from .object_creator.downloaded_to_paperObj import dwnlddJson_to_paperJson, dwnldd_obj_to_paper_json
    from .object_creator.create_downloadedObj import pdf_to_downloaded_obj, json_to_downloaded_obj

    # Clear the content of the file processed_metadata.json
    processed_metadata_path = output + PROCESSED_PATH
    if os.path.exists(processed_metadata_path):
        with open(processed_metadata_path, 'w') as file:
            file.truncate(0)

    if input and json:
        print("Error: Only one input should be provided.")
        return
    if input and os.path.isdir(input):
        _aux_pdfs_to_pp_json(input= input, output= output)
        return
    if input and input.endswith(".json") and os.path.exists(input):
        output_dir = dwnlddJson_to_paperJson(input, output)
        return output_dir
    if json and json.endswith(".json") and os.path.exists(json):
        downloaded_metadata = json_to_downloaded_obj(json, output)
        output_dir = dwnlddJson_to_paperJson(downloaded_metadata, output)
        return output_dir
    #if input and input.endswith(".pdf") and os.path.exists(input):
    #   TODO
    #   dwnldd = pdf_to_downloaded_obj(pdf= input, output_dir= output)
    #   dwnldd_obj_to_paper_json(download_obj= dwnldd,output_dir= output)
    #   return
    else:
        print("Error")
        return


def _aux_pdfs_to_pp_json(input, output):
    from .object_creator.create_downloadedObj import pdf_to_downloaded_obj
    from .object_creator.downloaded_to_paperObj import dwnldd_obj_to_paper_dic
    import json
    try:
        result = {}
        for pdfFile in os.listdir(input):
            log.info(pdfFile)
            try:
                if os.path.isfile(pdfFile) and pdfFile.endswith(".pdf"):
                    dwnldd = pdf_to_downloaded_obj(
                        pdf=pdfFile, output_dir=output)
                    pp_dic = dwnldd_obj_to_paper_dic(downloaded_obj=dwnldd)
                    try:
                        result.update(pp_dic)
                    except Exception as update_error:
                        log.error(
                            f"Error updating result with pp_dic: {str(update_error)}")
                        continue
                        print(pp_dic)
                        print(pdfFile)
            except Exception as file_error:
                log.error(f"Error processing file: {str(file_error)}")
                continue
        output_path = output + "/" + "processed_metadata.json"
        with open(output_path, 'w+') as out_file:
            json.dump(result, out_file, sort_keys=True, indent=4,
                      ensure_ascii=False)
        return output_path
    except Exception as e:
        log.error(f"an error occurred: {str(e)}")
        log.error(str(e))


def merge_json_files(input_path, existing_oeg_papers):
    """
    Merges existing OEG papers into an input JSON file.
    
    @Param input_path (str): Path to the input JSON file.
    @Param existing_path (str): Path to the existing papers JSON file.
    """
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            input_data = json.load(f)    
        with open(existing_oeg_papers, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)

        if isinstance(input_data, list) and isinstance(existing_data, list):
            input_data.extend(existing_data)
        elif isinstance(input_data, dict) and isinstance(existing_data, dict):
            input_data.update(existing_data)
        else:
            raise ValueError("JSON structures do not match for merging")

        with open(input_path, 'w', encoding='utf-8') as f:
            json.dump(input_data, f, ensure_ascii=False, indent=4)  
    except Exception as e:
        log.error(f"Error while merging the JSONs: {e}")
