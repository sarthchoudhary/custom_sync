## ----------------------------------------- imported libraries -----------------------------------------
from os import path, listdir, mkdir, remove
import shutil
from time import sleep
import sys
import itertools

## ----------------------------------------- Function definitions -----------------------------------------
def sync_dir_changes(src:str, replica:str):
    '''This only copies directory from src to replica. Also copies changes in files. Delete extra files found in replica.'''
    for element in listdir(src):
        if path.isfile(path.join(src, element)): # for files only
            if not path.exists(path.join(replica, element)):
                print(f'Copying {path.join(replica, element)}')
                shutil.copyfile(path.join(src, element), path.join(replica, element))
            elif path.getmtime(path.join(src, element)) > path.getmtime(path.join(replica, element)):  # compare for modification time between replica and src
                print(f'Copying {path.join(replica, element)}')
                shutil.copyfile(path.join(src, element), path.join(replica, element))
                
        else: # for directories only
            if not path.exists(path.join(replica, element)):
                print(f'Copying entire directory: {path.join(replica, element)}')
                shutil.copytree(path.join(src, element), path.join(replica, element))
            else:        # if the directory exists we need to traverse it and copy missing elements
                for replica_element in listdir(path.join(replica, element)):
                    if not path.exists(path.join(src, element, replica_element)):
                        replica_element_path = path.join(replica, element, replica_element)
                        if path.isfile(replica_element_path):
                            print(f'Removing {replica_element_path}')
                            remove(replica_element_path) # delete a single file
                        else:
                            print(f'Removing entire directory: {replica_element_path}')
                            shutil.rmtree(replica_element_path) # delete dir tree

                sync_dir_changes(path.join(src, element), path.join(replica, element)) # recursion to propagate the sync down the directory tree

def create_base_sync_changes(src:str, replica:str):
    if not path.exists(replica):
        print(f'Creating replica directory: {replica}')
        mkdir(replica)
    else: # deletes extra dir from the base folder
        for replica_element in listdir(replica):
            if not path.exists(path.join(src, replica_element)):
                replica_element_path = path.join(replica, replica_element)
                if path.isfile(replica_element_path):
                    print(f'Removing {replica_element_path}')
                    remove(replica_element_path) # delete a single file
                else:
                    print(f'Removing entire directory: {replica_element_path}')
                    shutil.rmtree(replica_element_path) # delete dir tree
    sync_dir_changes(src, replica)

## ----------------------------------------- Arguments -----------------------------------------
src_path, replica_path, sync_interval, sync_attempts_num, log_path = sys.argv[1:]
sync_interval = float(sync_interval)
sync_attempts_num = int(sync_attempts_num)
# print(f'src_path: {src_path}')
# print(f'replica_path: {replica_path}')

# print(f'sync_interval: {sync_interval}')
# print(f'sync_attempts: {sync_attempts}')

# print(f'log_path: {log_path}')

## ----------------------------------------- main -----------------------------------------
def main():
    spinner = itertools.cycle(['-', '/', '|', '\\'])
    sync_attempts = 0
    while sync_attempts < sync_attempts_num: #TODO: spinning wheel or some othe waiting icon
        create_base_sync_changes(src_path, replica_path)
        sleep(sync_interval) # sync interval
        sys.stdout.write(next(spinner))
        sys.stdout.flush()
        sys.stdout.write('\b')
        sync_attempts += 1

if __name__ == "__main__":
    main()