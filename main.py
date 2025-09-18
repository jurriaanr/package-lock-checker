#!/usr/bin/env python3

import argparse
import json
import os
import re
import subprocess
import sys
from operator import itemgetter
from pathlib import Path
import urllib.request


def get_affected_libraries():
    link = "https://socket.dev/api/blog/feed.atom"
    f = urllib.request.urlopen(link)
    output = f.read()

    affected = re.findall(r'<code>([@a-z/-]+)@([\d\\.]+)</code>', str(output))
    return sorted(affected, key=itemgetter(0))


def run_gh(args, capture_bytes=False):
    try:
        res = subprocess.run(
            ["gh"] + args,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return res.stdout if capture_bytes else res.stdout.decode("utf-8")
    except FileNotFoundError:
        sys.stderr.write("Error: `gh` CLI not found. Install GitHub CLI and login with `gh auth login`.\n")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"gh error: {' '.join(['gh'] + args)}\n{e.stderr.decode('utf-8')}\n")
        raise


def gh_json(args):
    out = run_gh(args)
    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Failed to parse JSON from gh output for: {' '.join(['gh'] + args)}\n")
        raise e


def list_org_repos(org):
    return gh_json([
        "repo", "list", org,
        "--limit", "1000",
        "--json", "nameWithOwner,defaultBranchRef,archivedAt"
    ])


def get_tree(name_with_owner, ref):
    return gh_json([
        "api", f"repos/{name_with_owner}/git/trees/{ref}?recursive=1"
    ])


def get_raw_content(name_with_owner, path, ref):
    return run_gh([
        "api", f"repos/{name_with_owner}/contents/{path}?ref={ref}",
        "-H", "Accept: application/vnd.github.v3.raw"
    ], capture_bytes=True)


def get_package_lock_files(outfile, organization, include_archived):
    # ensure gh is authenticated
    try:
        _ = run_gh(["auth", "status"])
    except SystemExit:
        return
    except Exception:
        pass

    out_path = Path(outfile)
    out_path.write_bytes(b"")  # truncate

    repos = list_org_repos(organization)

    repos_scanned = 0
    archived_repos_skipped = 0
    files_collected = 0
    trees_truncated_skipped = 0

    for r in repos:
        print('Found repository %s' % r['nameWithOwner'])

        if r.get("archivedAt") and not include_archived:
            archived_repos_skipped += 1
            print('Skipped because archived at %s' % r['archivedAt'])
            continue

        repos_scanned += 1

        repo = r["nameWithOwner"]
        ref = r.get("defaultBranchRef")['name'] or "main"

        try:
            tree = get_tree(repo, ref)
        except Exception as e:
            sys.stderr.write(f"Skipping {repo}@{ref}: tree fetch failed: {e}\n")
            continue

        if tree.get("truncated"):
            trees_truncated_skipped += 1
            continue

        entries = tree.get("tree", [])
        targets = [t for t in entries if t.get("type") == "blob" and t.get("path", "").endswith("package-lock.json")]

        if not targets:
            print('Np package-lock.json file found in %s' % r['nameWithOwner'])
            continue

        with out_path.open("ab") as outf:
            for t in targets:
                path = t["path"]
                header = f"// {repo}/{path}@{ref}\n"
                outf.write(header.encode("utf-8"))
                try:
                    data = get_raw_content(repo, path, ref)
                    outf.write(data)
                    if not data.endswith(b"\n"):
                        outf.write(b"\n")
                except Exception as e:
                    err = f"// ERROR fetching {repo}/{path}@{ref}: {e}\n"
                    outf.write(err.encode("utf-8"))
                outf.write(b"\n")
                files_collected += 1

    summary = {
        "org": organization,
        "output": str(out_path.resolve()),
        "repos_scanned": repos_scanned,
        "archived_repos_skipped": archived_repos_skipped,
        "files_collected": files_collected,
        "trees_truncated_skipped": trees_truncated_skipped,
    }

    print('\nSummary of repositories scanned:')
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-f', '--force', help='Refetch all package-log.json files', action='store_true')
    parser.add_argument("--org", default="jurriaanr")
    parser.add_argument("--out", default="all-package-locks.txt")
    parser.add_argument("--include-archived", action="store_true")

    args = parser.parse_args()

    if not os.path.exists(args.out) or args.force:
        get_package_lock_files(args.out, args.org, args.include_archived)

    with open(args.out) as f:
        packages = f.read()

    affected = get_affected_libraries()
    found = []

    print('\nFound %d affected libraries:\n' % len(affected))

    for lib in affected:
        match = '"%s": "%s"' % (lib[0], lib[1])
        print('Checked for %s@%s' % (lib[0], lib[1]))

        for m in re.finditer(match, packages, re.IGNORECASE):
            filePart = packages[0:m.start()]
            file = re.findall(r'(?<=// ).*', filePart)[-1]

            warning = "Package %s@%s found in %s" % (lib[0], lib[1], file)
            found.append(warning)
            print(warning)

    if len(found) == 0:
        print('\nAll good')
    else:
        print('\nAFFECTED PACKAGES FOUND!')
        print(found)


if __name__ == "__main__":
    main()
