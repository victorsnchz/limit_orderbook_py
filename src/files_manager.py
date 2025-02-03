import os
import csv
import glob


def get_last_modified_file(path: str):

    list_of_files = glob.glob(f'{path}')
    latest_file = max(list_of_files, key = os.path.getctime)
    return latest_file

def write_dict_to_csv(writer: csv.writer, state_dict: dict):
    for index, values in state_dict.items():
        data = [index] + list(values)
        writer.writerow(data)
