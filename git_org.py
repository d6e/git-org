import os
import sys
import StringIO
import shutil
import ConfigParser
import argparse
import logging
from urlparse import urlparse

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')

STR_CLONE = 'clone'
STR_ORGANIZE = 'organize'


def is_git_repo(x):
    return os.path.isdir(os.path.join(x, '.git')) and '.git' in os.listdir(x)


def parse_cli():
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
    return parser.parse_args()


def normalize_path(path):
    """ Removes tilda's which would otherwise have to be escaped and
    converts to a more fs friendly path. """
    return path.replace('~', '').replace('/', os.path.sep)


class RepoPaths:
    def __init__(self, path, repo):
        self.name = os.path.basename(repo)  # name of the repo
        self.path = path  # path derived from url
        self.repo = repo  # full path to original location on disk


def organize(args):
    repo_paths = []
    repos = [os.path.join(args.projects_root, x) for x in os.listdir(args.projects_root)]
    git_repos = filter(is_git_repo, repos)
    if len(git_repos) == 0:
        print("No git repos found.")
        sys.exit(0)
    for repo in git_repos:
        git_config_path = os.path.join(repo, '.git', 'config')
        config = ConfigParser.RawConfigParser(allow_no_value=True)
        with open(git_config_path) as f:
            contents = f.read()
            contents = contents.replace('\t', '')
            buf = StringIO.StringIO(contents)
            config.readfp(buf)
        origin_section = 'remote "origin"'
        if origin_section in config.sections():
            origin_url = config.get('remote "origin"', 'url')
            parsed_url = urlparse(origin_url)
            if not parsed_url.scheme:
                if origin_url.startswith('/'):
                    logging.warning("The url '%s' for repo '%s' is a local path. "
                                    "Not going to do anything.", origin_url, repo)
                else:
                    # Assuming it's using scp-like syntax described in
                    # the git-clone manpages.
                    origin_url = 'ssh://' + origin_url
                    parsed_url = urlparse(origin_url)
            origin_hostname = parsed_url.hostname
            origin_path = os.path.dirname(parsed_url.path)
            path = ''.join([origin_hostname, normalize_path(origin_path)])
            repo_paths.append(RepoPaths(path, repo))
    if args.dry_run:
        print('Would create the following directories:')
        paths_dict = {}
        path_list = sorted([os.path.join(rp.path, rp.repo) for rp in repo_paths])
        print('\t' + '\n\t'.join(path_list))
    else:
        for rp in repo_paths:
            full_repo_path = os.path.join(os.path.abspath(args.projects_root), rp.path)
            if not os.path.isdir(full_repo_path):
                os.makedirs(full_repo_path)
            else:
                logging.debug("Repo destination path '%s' already exists, not creating it.", full_repo_path)
            src = os.path.join(args.projects_root, rp.repo)
            dst = os.path.join(full_repo_path, rp.name)
            if not os.path.isdir(dst):
                logging.info("Copying '%s' to '%s'", src, dst)
                shutil.copytree(src, dst, symlinks=True)
                if args.move:
                    # Copy first, then move to cautiously prevent lost data if a move fails.
                    shutil.rmtree(src)
            else:
                logging.info("The path '%s' already exists, not copying to it.", dst)


def clone(args):
    pass


if __name__ == "__main__":
    args = parse_cli()
    subcommand = {
        STR_CLONE: clone,
        STR_ORGANIZE: organize,
    }
    subcommand[args.subparser_name](args)
