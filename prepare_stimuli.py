import os
import random
import csv
import argparse
from typing import List

import pathlib

def prepare_stimuli_list(subject_id: str):
    '''
    Prepare stimuli order for two settings

    Parameters
    ----------
    subject_id: str
        A unique ID for each sucject(participant)
    '''
    path = "stimuli/stimuli_categories"
    categories = os.listdir(path)
    categories.sort()
    random_categories = []
    for category in categories:
        files = os.listdir(os.path.join(path, category))
        random.shuffle(files)
        random_categories.append(files)
    random.shuffle(random_categories)
    f2f_list: List = []
    for category in random_categories:
        f2f_list.extend(category[0:3])
      
    random.shuffle(random_categories)
    remote_list: List = []
    for category in random_categories:
        remote_list.extend(category[3:6])
    

    if not os.path.exists("stimuli/f2f"):
        pathlib.Path("stimuli/f2f").mkdir(parents=True)
    with open("stimuli/f2f/p{0}_stimuli.csv".format(subject_id), "w") as csv_file:
        csv_writer = csv.writer(csv_file)
        for stimuli in f2f_list:
            csv_writer.writerow([stimuli])
    
    if not os.path.exists("stimuli/remote"):
        pathlib.Path("stimuli/remote").mkdir(parents=True)
    with open("stimuli/remote/p{0}_stimuli.csv".format(subject_id), "w") as csv_file:
        csv_writer = csv.writer(csv_file)
        for stimuli in remote_list:
            csv_writer.writerow([stimuli])
    

if __name__ == "__main__":
    path = "stimuli/stimuli_categories"
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--subject_id", help="The subject ID", default=0)
    args = parser.parse_args()
    subject_id: str = args.subject_id
    prepare_stimuli_list(subject_id)