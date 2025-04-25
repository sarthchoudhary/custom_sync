## ----------------------------------------- imported libraries -----------------------------------------
from os import path, listdir, mkdir, remove
import shutil
from time import sleep, perf_counter
import sys
import itertools
import logging
import hashlib

__authors__ = "Sarthak Choudhary"
__repo_url__ = "https://github.com/sarthchoudhary/custom_sync"
__email__ = "sarth8d314@gmail.com"
## command: python custom_sync.py /mnt/c/Users/sarth/Downloads/Test_folder /mnt/c/Users/sarth/Downloads/Replica_folder 15 12 /home/sarthak/my_projects/custom_sync/custom_sync.log

## ----------------------------------------- Arguments -----------------------------------------
src_path, replica_path, sync_interval, sync_attempt_limit, log_path = sys.argv[1:] #TODO: error handling: make sure paths are correct
sync_interval = float(sync_interval)
sync_attempt_limit = int(sync_attempt_limit)
## TODO: verify read write permission for the src and replica directories.

## ----------------------------------------- logging -----------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler()
    ]
)

## ----------------------------------------- Function definitions -----------------------------------------
def sync_dir_changes(src:str, replica:str):
    '''copies directory from src to replica. Also copies changes in files. Delete extra files found in replica.'''
    for element in listdir(src):
        if path.isfile(path.join(src, element)): # for files only
            if not path.exists(path.join(replica, element)):
                logging.info(f'Copying {path.join(replica, element)}')
                shutil.copyfile(path.join(src, element), path.join(replica, element))
            elif path.getmtime(path.join(src, element)) > path.getmtime(path.join(replica, element)):  # compares modification time between replica and src
                logging.info(f'Copying {path.join(replica, element)}')
                shutil.copyfile(path.join(src, element), path.join(replica, element))
                
        else: # for directories only
            if not path.exists(path.join(replica, element)):
                logging.info(f'Copying entire directory: {path.join(replica, element)}')
                shutil.copytree(path.join(src, element), path.join(replica, element))
            else:        # if the directory exists we need to traverse it and copy missing elements
                for replica_element in listdir(path.join(replica, element)):
                    if not path.exists(path.join(src, element, replica_element)):
                        replica_element_path = path.join(replica, element, replica_element)
                        if path.isfile(replica_element_path):
                            logging.info(f'Removing {replica_element_path}')
                            remove(replica_element_path) # delete a single file
                        else:
                            logging.info(f'Removing entire directory: {replica_element_path}')
                            shutil.rmtree(replica_element_path) # delete dir tree

                sync_dir_changes(path.join(src, element), path.join(replica, element)) # recursion to propagate the sync down the directory tree

def create_base_sync_changes(src:str, replica:str):
    ''' Creates the base directory if needed and synchronises changes from the source directory.'''
    if not path.exists(replica):
        logging.info(f'Creating replica directory: {replica}')
        mkdir(replica)
    else: # deletes extra dir from the base folder
        for replica_element in listdir(replica):
            if not path.exists(path.join(src, replica_element)):
                replica_element_path = path.join(replica, replica_element)
                if path.isfile(replica_element_path):
                    logging.info(f'Removing {replica_element_path}')
                    remove(replica_element_path) # delete a single file
                else:
                    logging.info(f'Removing entire directory: {replica_element_path}')
                    shutil.rmtree(replica_element_path) # delete dir tree
    sync_dir_changes(src, replica)

##TODO: hash check at end (see notebook.)

## ----------------------------------------- main -----------------------------------------
def main():
    spinner = itertools.cycle(['-', '/', '|', '\\'])
    sync_cycle = 0
    while sync_cycle < sync_attempt_limit:
        t0 = perf_counter()
        create_base_sync_changes(src_path, replica_path)
        # sleep(sync_interval) 
        
        execution_time = perf_counter() - t0
        sleep_time = sync_interval - execution_time #TODO: error handling. what if processing > sync_interval
        sleep(sleep_time)
        sys.stdout.write(next(spinner)) # TODO: Spinning wheel seems slow. Should be independent of sync speed.
        sys.stdout.flush()
        sys.stdout.write('\b')

        sync_cycle += 1

if __name__ == "__main__":
    main() #TODO: refactoring