# Directory Synchroniser

A Python script for one directional synchronisation of a source directory to a replica directory.

## Prerequisites

- Only uses Python standard library.

## Usage 

From command line do:

`python custom_sync.py src_path replica_path sync_interval sync_attempt_limit log_path`

## Arguments

- src_path : Path to the source directory.

- replica_path: Path to the replica directory.

- sync_interval : the interval between sync cycles in seconds. It needs to be a positive real number.

- sync_attempt_limit : the maximum number of sync cycles. It needs to be a positive integer.

- log_path: Path to the log file (valid extensions: .log, .txt, .out, .err, .dat, .csv, .json, .trc).

## Note: 
- Code will delete extra files and directories present in the replica directory.
- It will skip files starting with '.' (hidden directories in Linux).
- It will only copy the link and not traverse it.
- It will perform an integrity test between the source and replica directories using MD5 checksum. The test will be skipped if source directory is too large.