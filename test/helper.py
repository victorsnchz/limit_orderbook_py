import csv
import pathlib
import os

def read_csv_file(target_dir: str, file_name: str):

    path = f'{target_dir}/{file_name}/'

    with open(f'{path}.csv', 'r') as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            yield row


def read_two_csvs(csv_file_A: str, csv_file_B: str, strict = True):

    with open(f'{csv_file_A}.csv') as csv_A, open(f'{csv_file_B}.csv') as csv_B:
        
        reader_A = csv.reader(csv_A)
        reader_B = csv.reader(csv_B)

        for row_A, row_B in zip(reader_A, reader_B, strict=strict):
            yield (row_A, row_B)