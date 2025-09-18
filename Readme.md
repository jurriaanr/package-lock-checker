Scan package-lock.json files on all repositories within an organization on a known list of crowdstrike vulnerabilities.
Can be easily adjusted to use any list of libraries in the future.

Unfortunately the current source is badly formatted, contains spelling errors and missing characters and is not in an
easily accessible location.

This script uses the [Github CLI](https://cli.github.com) to perform the search and retrieve the contents of the files.

    usage: main.py [-h] [-f] [--org ORG] [--out OUT] [--include-archived]
    
    options:
      -h, --help          show this help message and exit
      -f, --force         Refetch all package-log.json files
      --org ORG           The name of the organization/user
      --out OUT           The output file for the combined lock files
      --include-archived  By default archived repositories are ignored