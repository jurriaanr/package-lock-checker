Scan package-lock.json files on all repositories within an organization on a known list of crowdstrike vulnerabilities.
Can be easily adjusted to use any list of libraries in the future.

    usage: main.py [-h] [-f] [--org ORG] [--out OUT] [--include-archived]
    
    options:
      -h, --help          show this help message and exit
      -f, --force         Refetch all package-log.json files
      --org ORG           The name of the organization/user
      --out OUT           The output file for the combined lock files
      --include-archived  By default archived repositories are ignored