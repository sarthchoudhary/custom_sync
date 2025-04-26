## ----------------------------------------- imported libraries -----------------------------------------
from os import path, listdir, mkdir, remove, access, R_OK, W_OK
import shutil
from time import sleep, perf_counter
import sys
import itertools
import logging
import hashlib

__authors__ = "Sarthak Choudhary"
__repo_url__ = "https://github.com/sarthchoudhary/custom_sync"
## command: python custom_sync.py /mnt/c/Users/sarth/Downloads/Test_folder /mnt/c/Users/sarth/Downloads/Replica_folder 15 12 /home/sarthak/my_projects/custom_sync/custom_sync.log

## ----------------------------------------- DirectorySynchroniser Class -----------------------------------------
class DirectorySynchroniser:
    """Manages synchronisation between a source and replica directory."""

    def __init__(self, src_path: str, replica_path: str, sync_interval: str, sync_attempt_limit: str, log_path: str):
            """Initialise variables."""
            self.src_path = src_path
            self.replica_path = replica_path
            self.sync_interval = float(sync_interval)
            try:
                self.sync_attempt_limit = int(sync_attempt_limit) # sync amount
            except ValueError as e:
                self.sync_attempt_limit = float(sync_attempt_limit)
            self.log_path = log_path
            self._validate_inputs(sync_interval, sync_attempt_limit)
            self._setup_logging()

    def _setup_logging(self):
        """Configure logging to file and console."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_path),
                logging.StreamHandler()
            ]
        )
    
    def _check_permissions(self):
        """Verify read permission for source and read/write permission for replica. Checks write permission for log file."""
        if not access(self.src_path, R_OK):
            raise PermissionError(f"No read permission for source path: {self.src_path}. Please fix permissions and try again.")
        target_path = self.replica_path if path.exists(self.replica_path) else path.dirname(self.replica_path) or '.'
        if not access(target_path, W_OK):
            raise PermissionError(f"No write permission for replica path: {self.replica_path}. Please fix permissions and try again.")
        if path.exists(self.replica_path) and not access(self.replica_path, R_OK):
            raise PermissionError(f"No read permission for replica path: {self.replica_path}. Please fix permissions and try again.")
        # log_file_path = self.log_path if path.exists(self.log_path) else path.dirname(self.log_path) or '.'
        log_file_path = path.dirname(self.log_path)
        if not access(log_file_path, W_OK):
            raise PermissionError(f"No write permission for creating log at {log_file_path}. Please fix permissions and try again.")

    def _validate_inputs(self, sync_interval, sync_attempt_limit):
        """Validate paths, permissions, and configuration.""" # not logged
        if not path.exists(self.src_path):
            logging.error(f"Source path does not exist: {self.src_path}")
            # sys.exit(1) # only logging error; not exiting the program.
        if not path.isdir(self.src_path):
            logging.error(f"Source path is not a directory: {self.src_path}")
            # sys.exit(1)
        if path.exists(self.replica_path) and not path.isdir(self.replica_path):
            logging.error(f"Replica path is not a directory: {self.replica_path}")
            # sys.exit(1)
        if self.sync_interval <= 0:
        # if sync_interval <= 0:
            logging.error("Sync interval must be positive")
            # sys.exit(1)
        if self.sync_attempt_limit <= 0:
        # if sync_attempt_limit <= 0:
            logging.error("Sync attempt limit must be positive integer")
            # sys.exit(1)
        if not isinstance(self.sync_attempt_limit, int):
            self.sync_attempt_limit = round(self.sync_attempt_limit)
            print(f"Rounding sync attempt limit to nearest integer: {self.sync_attempt_limit}.")
        # if not (self.log_path.endswith('.log') or self.log_path.endswith('.txt')):
            # logging.error(f"Log file should either be .log or .txt file.")
        if not path.splitext(self.log_path)[1].lower() in ['.log', '.txt', '.out', '.err', '.dat', '.csv', '.json', '.trc']:
            logging.error(f"Log file does not have a valid extension.")
            # sys.exit(1)
        try:
            self._check_permissions()
        except PermissionError as e:
            logging.error(str(e))
            # sys.exit(1)

    def sync_dir_changes(self, src:str, replica:str):
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
                    self.sync_dir_changes(path.join(src, element), path.join(replica, element)) # recursion to propagate the sync down the directory tree

    def create_base_sync_changes(self, src:str, replica:str):
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
        self.sync_dir_changes(src, replica)

    ##TODO: hash check at end (see notebook.)

    def start_sync(self):
        """Run the synchronisation loop."""
        # spinner = itertools.cycle(['-', '/', '|', '\\'])
        # spinner = itertools.cycle(['*', '**', '***', '****', '*****'])
        logging.info('Beginning synchronisation.')
        sync_cycle = 0
        while sync_cycle < self.sync_attempt_limit:
            t0 = perf_counter()
            self.create_base_sync_changes(self.src_path, self.replica_path)
            # sleep(sync_interval) 
            
            execution_time = perf_counter() - t0
            sleep_time = self.sync_interval - execution_time #TODO: error handling. what if processing > sync_interval
            sleep(sleep_time)
            # sys.stdout.write(next(spinner)) # TODO: Spinning wheel seems slow. Should be independent of sync speed.
            # sys.stdout.flush()
            # sys.stdout.write('\b')

            sync_cycle += 1

## ----------------------------------------- Entry point -----------------------------------------
def main():
    ''' Pass the command-line arguments and start the program.'''
    src_path, replica_path, sync_interval, sync_attempt_limit, log_path = sys.argv[1:]

    sync_object = DirectorySynchroniser(
            src_path, replica_path, sync_interval, sync_attempt_limit, log_path
        )
    sync_object.start_sync()

if __name__ == "__main__":
    main()