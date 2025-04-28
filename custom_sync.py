## ----------------------------------------- imported libraries -----------------------------------------
from os import path, listdir, mkdir, remove, access, R_OK, W_OK, walk
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
                self.sync_attempt_limit = int(sync_attempt_limit) # referred to as sync amount in original problem statement
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
        # for element in listdir(src):
        dir_elements_ls = [f for f in listdir(src) if not f.startswith('.')]
        for element in dir_elements_ls:
            if path.isfile(path.join(src, element)): # for files only
                if not path.exists(path.join(replica, element)):
                    logging.info(f'Copying {path.join(replica, element)}')
                    shutil.copyfile(path.join(src, element), path.join(replica, element))
                elif path.getmtime(path.join(src, element)) > path.getmtime(path.join(replica, element)):  # copies src to replica if src has newer modification timestamp
                    logging.info(f'Copying {path.join(replica, element)}')
                    shutil.copyfile(path.join(src, element), path.join(replica, element))
                    
            else: # for directories only
                if not path.exists(path.join(replica, element)):
                    logging.info(f'Copying entire directory: {path.join(replica, element)}')
                    shutil.copytree(path.join(src, element), path.join(replica, element))
                else:        # if the directory exists we need to traverse it and copy missing elements
                    # for replica_element in listdir(path.join(replica, element)):
                    replica_elements_ls = [f for f in listdir(path.join(replica, element)) if not f.startswith('.')] # we don't care about hidden files
                    for replica_element in replica_elements_ls:
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
            # for replica_element in listdir(replica):
            replica_elements_ls = [f for f in listdir(replica) if not f.startswith('.')]
            for replica_element in replica_elements_ls:
                if not path.exists(path.join(src, replica_element)):
                    replica_element_path = path.join(replica, replica_element)
                    if path.isfile(replica_element_path):
                        logging.info(f'Removing {replica_element_path}') #TODO: should not remove recent swp files.
                        remove(replica_element_path) # delete a single file
                    else:
                        logging.info(f'Removing entire directory: {replica_element_path}')
                        shutil.rmtree(replica_element_path) # delete dir tree
        self.sync_dir_changes(src, replica)

    def start_sync(self):
        """Run the synchronisation loop."""
        # spinner = itertools.cycle(['-', '/', '|', '\\'])
        # spinner = itertools.cycle(['*', '**', '***', '****', '*****'])
        spinner = itertools.cycle(['←', '↖', '↑', '↗', '→', '↘', '↓', '↙'])
        logging.info('Beginning synchronisation.')
        sync_cycle = 0
        while sync_cycle < self.sync_attempt_limit:
            t0 = perf_counter()
            self.create_base_sync_changes(self.src_path, self.replica_path)
            # sleep(sync_interval) # TODO: cleaning
            
            execution_time = perf_counter() - t0
            sleep_time = max(0, self.sync_interval - execution_time) # sleep_time always >= 0
            # sleep(sleep_time)
            # sys.stdout.write(next(spinner)) # could make spinner slow. New implementation below
            # sys.stdout.flush()
            # sys.stdout.write('\b') # not logged
            elapsed_time = 0
            while elapsed_time < sleep_time:
                sys.stdout.write(next(spinner))
                sys.stdout.flush()
                sleep(0.1)
                elapsed_time += 0.1
                sys.stdout.write('\b')

            sys.stdout.write(' ')# clear spinner
            sys.stdout.write('\b')
            sys.stdout.flush()
            sync_cycle += 1
        logging.info('Stopping synchronisation.')

    def calc_md5_for_directory(self, dir_path:str)-> str: #TODO: what if directory is too large to be hash checked?
        """"
        Calculate a single MD5 checksum for the entire directory tree at dir_path.
        This will change if any file's contents, path, or empty directories change.
        """
        dir_path = path.abspath(dir_path) # ensure path formatting
        md5 = hashlib.md5()
        follow_symlinks =  False

        for root, dir_ls, file_ls in walk(dir_path, followlinks=follow_symlinks):
            dir_ls.sort()
            file_ls.sort()
            
            # Include directory names in the hash so empty dirs are accounted for
            for dir_variable in dir_ls:
                dir_relative_path = path.relpath(path.join(root, dir_variable), dir_path)
                # appending D| as chatgpt suggested to avoid collision between filenames and directories
                md5.update(f"D|{dir_relative_path}".encode('utf-8')) 
            
            for fname in file_ls:
                full_file_path = path.join(root, fname)
                file_relative_path = path.relpath(full_file_path, dir_path)
                
                # Update hash with the file's path (so renaming changes the checksum)
                md5.update(f"F|{file_relative_path}".encode('utf-8')) # appending F|
                
                # Read file in chunks to avoid memory issues
                with open(full_file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        md5.update(chunk)

        return md5.hexdigest()
    
    def verify_integrity(self):
        '''
        Verify whether source and replica match using MD5 checksum. Performed only once after the sync cycle.    
        '''
        if self.calc_md5_for_directory(self.src_path) == self.calc_md5_for_directory(self.replica_path):
            logging.info(f"Integrity between the synchronisation source and replica confirmed with MD5 checksum.")
        else:
            logging.error(f"Integrity between the synchronisation source and replica could NOT be confirmed with MD5 checksum.")

## ----------------------------------------- Entry point -----------------------------------------
def main():
    ''' Pass the command-line arguments, start the program, and perform integrity check.'''
    src_path, replica_path, sync_interval, sync_attempt_limit, log_path = sys.argv[1:]

    sync_object = DirectorySynchroniser(
            src_path, replica_path, sync_interval, sync_attempt_limit, log_path
        )
    sync_object.start_sync()

    sync_object.verify_integrity()

if __name__ == "__main__":
    main()