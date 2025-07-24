import csv
import json
import re

def custom_replace(s):
    # Replace '(' and '+' with ', '
    s = s.replace('(', ', ').replace('+', ', ')
    # Replace ')' with ', ' only if not preceded by ','
    s = re.sub(r'(?<!\,)\)', ', ', s)
    # Remove unicode characters
    s = s.encode('ascii', 'ignore').decode('ascii')
    # strip extra spaces and trailing commas
    return s.strip().rstrip(',')

data = []

with open('data/boolean.csv', mode='r', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        new_row = {k: custom_replace(v) if isinstance(v, str) else v for k, v in row.items()}
        data.append(new_row)

with open('output.json', mode='w', encoding='utf-8') as jsonfile:
    json.dump(data, jsonfile, indent=4)