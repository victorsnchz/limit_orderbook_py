import os
import csv
import glob
import datetime

def get_last_modified_file(path: str):

    """
    Return last modified file in target directory.
    """

    list_of_files = glob.glob(f'{path}')
    latest_file = max(list_of_files, key = os.path.getctime)
    return latest_file

def write_dict_to_csv(writer: csv.writer, state_dict: dict):

    """
    Write dict line by line in csv file.
    """

    for index, values in state_dict.items():
        data = [index] + list(values)
        writer.writerow(data)

def get_results_names_bid_ask(data_dir: str, test_case: str, test_name: str) -> tuple[str, str]:

    """
    Return name format for bid/ask where test results are stored.
    """
    
    timestamp = datetime.datetime.now().time().strftime('%H_%M_%S')

    results_data_directory = f'{data_dir}/{test_case}/{test_name}/results'

    bid = f'{results_data_directory}/bid_{timestamp}'
    ask = f'{results_data_directory}/ask_{timestamp}'

    return bid, ask

def get_target_names_bid_ask(data_dir: str, test_case: str, test_name: str) -> tuple[str, str]:

    """
    Return name format for bid/ask where test targets are stored.
    """
    
    targets_data_directory = f'{data_dir}/{test_case}/{test_name}/targets'

    bid = f'{targets_data_directory}/bid'
    ask = f'{targets_data_directory}/ask'

    return bid, ask

def read_csv_file(target_dir: str, file_name: str):

    """
    Return csv file row-by-row.
    """

    path = f'{target_dir}/{file_name}/'

    with open(f'{path}.csv', 'r') as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            yield row

def read_two_csvs(csv_file_A: str, csv_file_B: str, strict = True):

    """
    Return two-csv files row-by-row simultaneously.
    """

    with open(csv_file_A) as csv_A, open(csv_file_B) as csv_B:
        
        reader_A = csv.reader(csv_A)
        reader_B = csv.reader(csv_B)

        for row_A, row_B in zip(reader_A, reader_B, strict=strict):
            yield (row_A, row_B)