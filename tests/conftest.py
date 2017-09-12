import os
import pytest
import shutil


CONFIG = """
[core]
        repositoryformatversion = 0
        filemode = true
        bare = false
        logallrefupdates = true
        ignorecase = true
        precomposeunicode = true
[remote "origin"]
        url = {url}
        fetch = +refs/heads/*:refs/remotes/origin/*
[branch "master"]
        remote = origin
        merge = refs/heads/master
"""

config_no_origin = """
[core]
    repositoryformatversion = 0
    filemode = true
    bare = false
    logallrefupdates = true
    ignorecase = true
    precomposeunicode = true
"""


def _mk_repo(projects_root: str, repo_name: str,
             origin_remote_url: str, config: str=CONFIG) -> str:
    git_config_dir = os.path.join(projects_root, repo_name, '.git')
    os.makedirs(git_config_dir)
    config_path = os.path.join(git_config_dir, 'config')
    with open(config_path, 'w') as f:
        f.write(config.format(url=origin_remote_url))
    return config_path


@pytest.fixture(scope='module')
def root_name():
    return 'myroot'


@pytest.fixture()
def projects_root(request, tmpdir, root_name) -> str:
    tmp_root = tmpdir.mkdir(root_name).strpath
    _mk_repo(tmp_root, 'myrepo', 'github.com:d6e/myrepo.git')
    _mk_repo(tmp_root, 'notrust', 'http://github.com/rust-lang/rust.git')
    _mk_repo(tmp_root, 'notrust2', 'http://github.com/rust-lang/rust2.git')
    _mk_repo(tmp_root, 'no-origin', 'http://github.com/rust-lang/no-origin.git', config=config_no_origin)
    request.addfinalizer(lambda: shutil.rmtree(tmp_root))
    return tmp_root
