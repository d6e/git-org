import os
import sys
import time
import shutil
import configparser
import argparse
import tempfile
import logging
import re
from typing import Optional, Tuple, List


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')

STR_CLONE = 'clone'
STR_ORGANIZE = 'organize'


def is_git_repo(x: str) -> bool:
    return os.path.isdir(os.path.join(x, '.git')) and '.git' in os.listdir(x)


def parse_cli() -> Tuple[str, str, bool, bool]:
    organize_help = """Looks through the 1st-level of directories in the
                  'projects root' for any git repos and relocates them
                  to a new directory tree based on their git repo's
                  origin url.
                  """
    description = "A tool for organizing git repos on your local filesystem."
    parser = argparse.ArgumentParser(description=description)

    subparsers = parser.add_subparsers(dest="subparser_name")  # this line changed
    clone_parser = subparsers.add_parser(STR_CLONE, help='Will clone a repo according to the organization.')
    clone_parser.add_argument('url', help='The git remote origin url.')
    org_parser = subparsers.add_parser(STR_ORGANIZE, help=organize_help)
    org_parser.add_argument('-d', '--dry-run', action="store_true", default=False,
                            help='Will print what actions would be taken.')
    org_parser.add_argument('projects_root',
                            type=str, action="store", default='.',
                            help='The root directory where your git repos are stored.')

    if len(sys.argv) <= 1:
        parser.print_help()
        sys.exit(0)
    args = parser.parse_args()
    return str(args.subparser_name), str(args.projects_root), bool(args.dry_run)


def _read_git_config(git_repo_path: str) -> configparser.RawConfigParser:
    git_config_path = os.path.join(git_repo_path, '.git', 'config')
    config = configparser.RawConfigParser(allow_no_value=True)
    config.read(git_config_path)
    return config


def _extract_origin_url(config: configparser.RawConfigParser, repo_path: str) -> Optional[str]:
    origin_section = 'remote "origin"'
    if origin_section in config.sections():
        return config.get('remote "origin"', 'url')
    else:
        logging.warning("No origin found for '%s'", repo_path)
        return None


def _is_sublist(lst1: List[str], lst2: List[str]) -> bool:
    def get_all_in(one, another):
        for element in one:
            if element in another:
                yield element

    for x1, x2 in zip(get_all_in(lst1, lst2), get_all_in(lst2, lst1)):
        if x1 != x2:
            return False


def filter_nested_git_repos(git_repos: List[str]) -> List[str]:
    git_parents = []  # type: List[str]
    git_repos.sort()
    for repo in git_repos:
        append = True
        for parent in git_parents:
            split_parent = parent.split('/')
            split_repo = repo.split('/')
            # if 'rust' in parent:
            # import pdb;pdb.set_trace()
            # for i in range(len(split_parent)):
            #     if split_repo[i] != split_parent[i]:

            if _is_sublist(split_repo, split_parent):
                append = False
        if append:
            git_parents.append(repo)
    return git_parents


def find_git_repos(root: str) -> List[str]:
    """
    Returns a list of git repo directories.
    """
    git_repos = []
    for path, dirs, files in os.walk(root):
        if '.git' in dirs:
            git_repos.append(path)
    return git_repos


def url_to_fs_path(root: str, url: str) -> str:
    """ Transforms the url for use as a filesystem path. """
    # If the url is a local filesystem url, then we ignore.
    if url.startswith('/') or url.startswith('file://'):
        return url
    # Trim scheme: it is not relevant to us.
    if '://' in url:
        url = url.split('://')[1]
    # Trim user: it is not relevant to us.
    if '@' in url:
        url = url.split('@')[1]
    # Trim .git part of url repo ending
    if url.endswith('.git') or url.endswith('.git/'):
        url = url.split('.git')[0]
    # Replace the port number
    url = re.sub(r":[0-9]{1,4}/", "/", url)
    # Handle the edge case where no port is specified.
    url = url.replace(':/', '/')
    # Replace any colons used with users
    url = url.replace(':', '/')
    # Replace remove tildes
    url = url.replace('~', '')
    # Remove junk from system configuration TODO: this should go in a config or something
    url = url.replace('scm/', '')
    # Ensure slashes use the system-native separator
    url = url.replace('/', os.path.sep).replace('\\', os.path.sep)
    return os.path.join(root, url)


def print_fs_changes(fs_changes: List[Tuple[str, str]]) -> None:
    print('\n'.join([' -> '.join(rp) for rp in fs_changes]))


def determine_fs_changes(projects_root: str, git_repos: List[str]) -> List[Tuple[str, str]]:
    fs_changes = []
    for repo in git_repos:
        config = _read_git_config(repo)
        origin_url = _extract_origin_url(config, repo)
        if origin_url is not None:
            new_fs_path = url_to_fs_path(projects_root, origin_url)
            fs_changes.append((repo, new_fs_path))
    return fs_changes


def prompt_user_approval() -> bool:
    """ Asks the user if it's acceptable. """
    return input("\nAccept? [y/N]").lower() in ['y', 'yes']


def organize(projects_root: str, dry_run: bool=False) -> None:
    """ The 'organize' command does the following:
    1. Finds all git repos under the provided root (not including nested git repos).
    2. Reads and parses the git config of each git repo to determine the destination path.
    3. Proposes the file system changes to the user and prompts for approval.
    4. Finally, it copies each old git repo path to the new git repo path and deletes the old repo
    if the 'move' cli flag is specified. """
    logging.info("Using projects_root: %s", projects_root)
    git_repos = find_git_repos(projects_root)
    git_repos = filter_nested_git_repos(git_repos)
    logging.info("Found the following non-nested repos: %s", git_repos)
    if len(git_repos) == 0:
        print("No git repos found. Maybe change your 'projects_root'? (projects_root='{}')".format(projects_root))
        sys.exit(0)
    # Read each git repo and determine the destination path by parsing the git remote origin
    fs_changes = determine_fs_changes(projects_root, git_repos)

    # Filter any non-changes
    fs_changes = list(filter(lambda x: x[0] != x[1], fs_changes))

    print("The proposed filesystem changes:\n")
    print_fs_changes(fs_changes)
    if dry_run:
        answer = False
    else:
        answer = prompt_user_approval()
    if answer:
        for fs_change in fs_changes:
            src, dst = fs_change
            parent_dir = os.path.dirname(dst)

            if not os.path.isdir(parent_dir):
                os.makedirs(parent_dir)
            else:
                logging.info("Repo destination path '%s' already exists, not creating it.", dst)
            if is_git_repo(dst):
                logging.warning("Git repo '%s' already exists, not moving...", dst)
            else:
                logging.info("Moving '%s' to '%s'", src, dst)
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp_src = os.path.join(tmp_dir, os.path.basename(src))
                    shutil.move(src, tmp_src)
                    shutil.move(tmp_src, dst)
                # shutil.copytree(src, dst, symlinks=True)
                # if move:
                #     # Copy first, then move to cautiously prevent lost data if a move fails.
                #     shutil.rmtree(src)


def clone(projects_root: str, dry_run: bool) -> None:
    pass


def main() -> None:
    subparser_name, projects_root, dry_run = parse_cli()
    subcommand = {
        STR_CLONE: clone,
        STR_ORGANIZE: organize,
    }
    subcommand[subparser_name](projects_root, dry_run)


if __name__ == "__main__":
    main()
