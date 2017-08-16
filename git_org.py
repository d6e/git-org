import os
import sys
import shutil
import configparser
import argparse
import logging
from urllib.parse import urlparse, ParseResult
from typing import Optional, Tuple


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
    org_parser.add_argument('-m', '--move', action="store_true", default=False,
                            help='Will move the git repos instead of just copy.')
    org_parser.add_argument('projects_root',
                            type=str, action="store", default='.',
                            help='The root directory where your git repos are stored.')

    if len(sys.argv) <= 1:
        parser.print_help()
        sys.exit(0)
    args = parser.parse_args()
    return str(args.subparser_name), str(args.projects_root), bool(args.move), bool(args.dry_run)


def normalize_path(path: str) -> str:
    """ Removes tilda's which would otherwise have to be escaped and
    converts to a more fs friendly path. """
    return path.replace('~', '').replace('/', os.path.sep)


class RepoPaths:
    def __init__(self, path: str, repo: str) -> None:
        self.name = os.path.basename(repo)  # name of the repo
        self.path = path  # path derived from url
        self.repo = repo  # full path to original location on disk


def _read_git_config(git_repo_path: str) -> configparser.RawConfigParser:
    git_config_path = os.path.join(git_repo_path, '.git', 'config')
    config = configparser.RawConfigParser(allow_no_value=True)
    config.read(git_config_path)
    return config


def _extract_origin_path(config: configparser.RawConfigParser, repo_path: str) -> Optional[ParseResult]:
    origin_section = 'remote "origin"'
    if origin_section in config.sections():
        origin_url = config.get('remote "origin"', 'url')
        parsed_url = urlparse(origin_url)
        if not parsed_url.scheme:
            if origin_url.startswith('/'):
                logging.warning("The url '%s' for repo '%s' is a local path. "
                                "Not going to do anything.", origin_url, repo_path)
            else:
                # Assuming it's using scp-like syntax described in
                # the git-clone manpages.
                origin_url = 'ssh://' + origin_url
                parsed_url = urlparse(origin_url)
        return parsed_url
    else:
        return None


def organize(projects_root: str, move: bool, dry_run: bool) -> None:
    repo_paths = []
    repos = [os.path.join(projects_root, x) for x in os.listdir(projects_root)]
    git_repos = list(filter(is_git_repo, repos))
    if len(git_repos) == 0:
        print("No git repos found.")
        sys.exit(0)
    for repo in git_repos:
        config = _read_git_config(repo)
        parsed_url = _extract_origin_path(config, repo)
        if parsed_url:
            origin_path = os.path.dirname(parsed_url.path)
            origin_hostname = parsed_url.hostname
            path = ''.join([origin_hostname, normalize_path(origin_path)])
            repo_paths.append(RepoPaths(path, repo))
    if dry_run:
        print('Would create the following directories:')
        path_list = sorted([os.path.join(rp.path, rp.repo) for rp in repo_paths])
        print('\t' + '\n\t'.join(path_list))
    else:
        for rp in repo_paths:
            full_repo_path = os.path.join(os.path.abspath(projects_root), rp.path)
            if not os.path.isdir(full_repo_path):
                os.makedirs(full_repo_path)
            else:
                logging.debug("Repo destination path '%s' already exists, not creating it.", full_repo_path)
            src = os.path.join(projects_root, rp.repo)
            dst = os.path.join(full_repo_path, rp.name)
            if not os.path.isdir(dst):
                logging.info("Copying '%s' to '%s'", src, dst)
                shutil.copytree(src, dst, symlinks=True)
                if move:
                    # Copy first, then move to cautiously prevent lost data if a move fails.
                    shutil.rmtree(src)
            else:
                logging.info("The path '%s' already exists, not copying to it.", dst)


def clone(projects_root: str, move: bool, dry_run: bool) -> None:
    pass


def main() -> None:
    subparser_name, projects_root, move, dry_run = parse_cli()
    subcommand = {
        STR_CLONE: clone,
        STR_ORGANIZE: organize,
    }
    subcommand[subparser_name](projects_root, move, dry_run)


if __name__ == "__main__":
    main()
