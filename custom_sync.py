## ----------------------------------------- imported libraries -----------------------------------------
from os import path, listdir, mkdir, remove, access, R_OK, W_OK, walk, symlink
import shutil
from time import sleep, perf_counter
import sys
import itertools
import logging
import hashlib
import argparse
from filecmp import cmp

__authors__ = "Sarthak Choudhary"
__repo_url__ = "https://github.com/sarthchoudhary/custom_sync"

## ----------------------------------------- DirectorySynchroniser Class -----------------------------------------
class DirectorySynchroniser:
    """Manages synchronisation between a source and replica directory."""

    def __init__(self, src_path: str, replica_path: str, sync_interval: float, sync_attempt_limit: int, log_path: str):
            """Initialise variables."""
            self.src_path = src_path
            self.replica_path = replica_path
            self.sync_interval = sync_interval
            self.sync_attempt_limit = sync_attempt_limit
            self.log_path = log_path
            self._validate_inputs()
            self._setup_logging()
            # directories exceeding this threshold will be skipped for integrity testing.
            self.size_threshold = 3*1024**3  # bytes # TODO: we could increase the threshold ~5 GB.

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

    def _validate_inputs(self):
        """Validate paths, permissions, and configuration."""
        if not path.exists(self.src_path):
            # logging.error(f"Source path does not exist: {self.src_path}")
            # sys.exit(1) # not exiting as per the test environment requirement.
            raise FileNotFoundError(f"Source path does not exist: {self.src_path}")
        if not path.isdir(self.src_path):
            # logging.error(f"Source path is not a directory: {self.src_path}")
            # sys.exit(1)
            raise NotADirectoryError(f"Source path is not a directory: {self.src_path}")
        if path.exists(self.replica_path) and not path.isdir(self.replica_path):
            # logging.error(f"Replica path is not a directory: {self.replica_path}")
            # sys.exit(1)
            raise NotADirectoryError(f"Replica path is not a directory: {self.replica_path}")
        if self.sync_interval <= 0:
        # if sync_interval <= 0:
            raise ValueError("Sync interval must be positive")
            # logging.error("Sync interval must be positive")
            # sys.exit(1)
        if self.sync_attempt_limit <= 0:
        # if sync_attempt_limit <= 0:
            raise ValueError("Sync attempt limit must be positive integer")
            # logging.error("Sync attempt limit must be positive integer")
            # sys.exit(1)
        if not path.splitext(self.log_path)[1].lower() in ['.log', '.txt', '.out', '.err', '.dat', '.csv', '.json', '.trc']:
            # logging.error(f"Log file does not have a valid extension.")
            # sys.exit(1)
            raise ValueError(f"Log file does not have a valid extension. Must be one of: .log, .txt, .out, .err, .dat, .csv, .json, .trc")
        log_dir = path.dirname(self.log_path) or '.'
        if not path.exists(log_dir):
            raise FileNotFoundError(f"Log directory does not exist: {log_dir}")
        self._check_permissions()

    def calc_MD5(self, dir_path:str)->str:
        ''' Calculates MD5 checksum for a single file.'''
        md5 = hashlib.md5()
        try:
            with open(dir_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''): # read file in chunks # TODO: try changing chunk size
                    md5.update(chunk)
        except (IOError, PermissionError) as e:
            raise IOError(f"Error reading file for MD5: {e}")
        return md5.hexdigest()

    def sync_dir_changes(self, src:str, replica:str):
        '''copies directory from src to replica. Also copies changes in files. Delete extra files found in replica.'''
        try:
            # for element in listdir(src):
            dir_elements_ls = [f for f in listdir(src) if not f.startswith('.')]
            for element in dir_elements_ls:
                src_element_path = path.join(src, element)
                dst_element_path = path.join(replica, element)
                if path.isfile(src_element_path): # for files only
                    if not path.exists(dst_element_path):
                        logging.info(f'Copying to: {dst_element_path}')
                        shutil.copyfile(src_element_path, dst_element_path)
                    # copies src to replica if src has newer modification timestamp
                    # any modification to a replica file should trigger sync code to replace that file with src copy. Using filecmp.cmp to detect changes in files.
                    else: 
                        if (path.getmtime(src_element_path) > path.getmtime(dst_element_path)) or not cmp(src_element_path, dst_element_path, shallow=False):
                            logging.info(f'Copying to: {dst_element_path}')
                            shutil.copyfile(src_element_path, dst_element_path)

                # elif path.isdir(src_element_path):
                elif path.isdir(src_element_path) and not path.islink(src_element_path): # for directories only
                    if not path.exists(dst_element_path):
                        logging.info(f'Copying entire directory to: {dst_element_path}')
                        shutil.copytree(src_element_path, dst_element_path)
                    else:        # if the directory exists we need to traverse it and copy missing elements
                        # for replica_element in listdir(dst_element_path):
                        replica_elements_ls = [f for f in listdir(dst_element_path) if not f.startswith('.')] # we don't care about hidden files on Linux; Windows?
                        for replica_element in replica_elements_ls:
                            if not path.exists(path.join(src, element, replica_element)):
                                replica_element_path = path.join(replica, element, replica_element)
                                if path.isfile(replica_element_path):
                                    logging.info(f'Removing: {replica_element_path}')
                                    remove(replica_element_path) # delete a single file
                                else:
                                    logging.info(f'Removing entire directory: {replica_element_path}')
                                    shutil.rmtree(replica_element_path) # delete dir tree
                        self.sync_dir_changes(src_element_path, dst_element_path) # recursion to propagate the sync down the directory tree

                elif path.islink(src_element_path) and not path.exists(dst_element_path): # for links only
                        logging.info(f'Creating link at: {dst_element_path}')
                        symlink(src_element_path, dst_element_path)
        except  (OSError, IOError) as e:
            logging.error(f"Error synchronising {src} to {replica}: {e}")

    def create_base_sync_changes(self, src:str, replica:str):
        ''' Creates the base directory if needed and synchronises changes from the source directory.'''
        try:
            if not path.exists(replica):
                logging.info(f'Creating replica directory: {replica}')
                mkdir(replica)
            else: # deletes extra dir from the base folder
                # for replica_element in listdir(replica):
                replica_elements_ls = [f for f in listdir(replica) if not f.startswith('.')]
                for replica_element in replica_elements_ls:
                    replica_element_path = path.join(replica, replica_element)
                    src_element_path = path.join(src, replica_element)

                    if not path.exists(src_element_path):
                        # replica_element_path = path.join(replica, replica_element)
                        if path.isfile(replica_element_path):
                            logging.info(f'Removing: {replica_element_path}')
                            remove(replica_element_path) # delete a single file
                        elif path.isdir(replica_element_path):
                            logging.info(f'Removing entire directory: {replica_element_path}')
                            shutil.rmtree(replica_element_path) # delete dir tree
                        elif path.islink(replica_element_path):
                            logging.info(f'Removing link: {replica_element_path}')
                            remove(replica_element_path) # delete link
                   # in case an extensionless file and a dir have same name. 
                    else:
                        if (path.isfile(replica_element_path) and path.isdir(src_element_path)): # isdir also captures symlinks
                            logging.info(f'Removing: {replica_element_path}')
                            remove(replica_element_path)
                        elif (path.isdir(replica_element_path) and path.isfile(src_element_path)):
                            logging.info(f'Removing entire directory: {replica_element_path}')
                            shutil.rmtree(replica_element_path)
            self.sync_dir_changes(src, replica)
        except (OSError, IOError) as e:
            logging.error(f"Error synchronising base directory at {replica}: {e}")

    def start_sync(self):
        """Run the synchronisation loop."""
        spinner = itertools.cycle(['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷'])
        logging.info('Beginning synchronisation.')
        logging.info('Hidden files in Linux will be skipped.')
        sync_cycle = 0
        while sync_cycle < self.sync_attempt_limit:
            t0 = perf_counter()
            self.create_base_sync_changes(self.src_path, self.replica_path)
            
            execution_time = perf_counter() - t0
            sleep_time = max(0, self.sync_interval - execution_time) # sleep_time always >= 0
            elapsed_time = 0
            while elapsed_time < sleep_time:
                sys.stdout.write(next(spinner))
                sys.stdout.flush()
                sleep(0.1)
                elapsed_time += 0.1
                sys.stdout.write('\b')

            sys.stdout.write(' ') # clear spinner
            sys.stdout.write('\b')
            sys.stdout.flush()
            sync_cycle += 1
        logging.info('Stopping synchronisation.')

    def calc_md5_for_directory(self, dir_path:str)-> str:
        """"
        Calculate a single MD5 checksum for the entire directory tree at dir_path.
        This will change if any file's contents, path, or empty directories change.
        """
        ##  May not work if src and replica are on different OSes. 
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
        total_size = 0
        for root, _dirnames, fnames in walk(self.src_path):
            for filename in fnames:
                total_size += path.getsize(path.join(root, filename))
        if total_size <= self.size_threshold:
            if self.calc_md5_for_directory(self.src_path) == self.calc_md5_for_directory(self.replica_path):
                logging.info(f"Integrity between the synchronisation source and replica confirmed with MD5 checksum.")
            else:
                logging.error(f"Integrity between the synchronisation source and replica could NOT be confirmed with MD5 checksum.")
        else:
            logging.info(f"Skipping integrity verification as the source directory exceeds the maximum threshold allowed.")

## ----------------------------------------- Entry point -----------------------------------------
def main():
    ''' Pass the command-line arguments, start the program, and perform integrity check.'''
    
    # if len(sys.argv) != 6:
    #     raise ValueError("Usage: python custom_sync.py src_path replica_path sync_interval sync_attempt_limit log_path")
        ## test environment requires that I do not call exit function. 
        ## logging.error("Usage: python custom_sync.py src_path replica_path sync_interval sync_attempt_limit log_path")
        ## sys.exit(1) 

    # src_path, replica_path, sync_interval, sync_attempt_limit, log_path = sys.argv[1:]

    # sync_object = DirectorySynchroniser(
    #         src_path, replica_path, sync_interval, sync_attempt_limit, log_path
    #     )

    parser = argparse.ArgumentParser()
    parser.add_argument("src_path", type=str, help="Source directory path")
    parser.add_argument("replica_path", type=str, help="Replica directory path")
    parser.add_argument("sync_interval", type=float, help="Synchronisation interval in seconds")
    parser.add_argument("sync_attempt_limit", type=int, help="Number of sync cycles")
    parser.add_argument("log_path", type=str, help="Path to log file")
    
    #TODO: lets see if this causes any problem with test environment
    args = parser.parse_args()

    # try:   
    #     args = parser.parse_args()
    # except SystemExit:
    #     return
    
    sync_object = DirectorySynchroniser(
        args.src_path, args.replica_path, args.sync_interval, args.sync_attempt_limit, args.log_path
    )

    sync_object.start_sync()

    sync_object.verify_integrity()

if __name__ == "__main__":
    main()