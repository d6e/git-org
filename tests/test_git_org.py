import os
import pytest
import shutil
from git_org import git_org
from typing import List, Tuple

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

ROOT = 'myroot'


@pytest.mark.parametrize(
    "url, expect",
    [
        ('ssh://git@github.com:d6e/git-org.git',
         'myroot/github.com/d6e/git-org'),
        ('http://github.com/rust-lang/rust2.git',
         'myroot/github.com/rust-lang/rust2'),
        ('ssh://git@git.example.com:7999/~user/mything.git',
         'myroot/git.example.com/user/mything'),
        ('http://github.com/rust-lang/rust.git',
         'myroot/github.com/rust-lang/rust'),
        ('https://user@git.example.com/scm/~user/rust.git',
         'myroot/git.example.com/user/rust'),
        ('ftps://host.xz:9999/path/to/repo.git/',
         'myroot/host.xz/path/to/repo'),
        ('ssh_host:chip8.git', 'myroot/ssh_host/chip8'),
        ('user@host.xz:/~user/path/to/repo.git/',
         'myroot/host.xz/user/path/to/repo'),
        ('file:///path/to/repo.git/', 'file:///path/to/repo.git/'),  # ignore
        ('/home/absolute/path/to/myproject',
         '/home/absolute/path/to/myproject'),  # ignore
    ])
def test_url_to_fs_path(url, expect):
    new_path = git_org.url_to_fs_path(ROOT, url)
    assert expect == new_path


@pytest.mark.parametrize("data, expected", [([''], ['']),
                                            (['jfds'], ['jfds']),
                                            (['/myroot/a/long/path', '/myroot/a', '/myroot/a/long/path/longer'], ['/myroot/a']),
                                            (['myroot/notrust', 'myroot/notrust2'], ['myroot/notrust', 'myroot/notrust2']),
                                            (['myroot/notrust2', 'myroot/notrust'], ['myroot/notrust', 'myroot/notrust2'])])
def test_filter_nested_git_repos(data, expected):
    result = git_org.filter_nested_git_repos(data)
    assert result == expected


def _mk_repo(projects_root: str, repo_name: str,
             origin_remote_url: str, config: str=CONFIG) -> str:
    git_config_dir = os.path.join(projects_root, repo_name, '.git')
    os.makedirs(git_config_dir)
    config_path = os.path.join(git_config_dir, 'config')
    with open(config_path, 'w') as f:
        f.write(config.format(url=origin_remote_url))
    return config_path


@pytest.fixture()
def projects_root(request, tmpdir) -> str:
    tmp_root = tmpdir.mkdir(ROOT).strpath
    _mk_repo(tmp_root, 'myrepo', 'github.com:d6e/myrepo.git')
    _mk_repo(tmp_root, 'notrust', 'http://github.com/rust-lang/rust.git')
    _mk_repo(tmp_root, 'notrust2', 'http://github.com/rust-lang/rust2.git')
    _mk_repo(tmp_root, 'no-origin', 'http://github.com/rust-lang/no-origin.git', config=config_no_origin)
    request.addfinalizer(lambda: shutil.rmtree(tmp_root))
    return tmp_root


def _get_fs(projects_root: str) -> List[Tuple[str, List[str], List[str]]]:
    fs = []
    for path, dirs, files in os.walk(projects_root):
        rel_path = ROOT + path.split(ROOT)[1]
        fs.append((rel_path, dirs, files))
    return fs


def test_organize(projects_root, monkeypatch):
    """ An integration test for the organize command. Tests known edge-cases as well. """
    monkeypatch.setattr(git_org, 'prompt_user_approval', lambda: True)
    monkeypatch.setattr(git_org, 'print_fs_changes', lambda x: x)
    expected = [('myroot', ['github.com', 'no-origin'], []),
                ('myroot/github.com', ['d6e', 'rust-lang'], []),
                ('myroot/github.com/d6e', ['myrepo'], []),
                ('myroot/github.com/d6e/myrepo', ['.git'], []),
                ('myroot/github.com/d6e/myrepo/.git', [], ['config']),
                ('myroot/github.com/rust-lang', ['rust', 'rust2'], []),
                ('myroot/github.com/rust-lang/rust', ['.git'], []),
                ('myroot/github.com/rust-lang/rust/.git', [], ['config']),
                ('myroot/github.com/rust-lang/rust2', ['.git'], []),
                ('myroot/github.com/rust-lang/rust2/.git', [], ['config']),
                ('myroot/no-origin', ['.git'], []),
                ('myroot/no-origin/.git', [], ['config'])
                ]
    orgd = git_org.organize(projects_root)
    post_org_fs = _get_fs(projects_root)
    assert post_org_fs == expected


@pytest.mark.parametrize("paths", [("my/same/path/repo1", "my/same/path/repo1"),
                                   ("my/same/path/repo1", "my/same/path1/repo1"),
                                   ("my/same/path/repo1", "my/same/path/repo2")])
def test__ensure_dir_exists(projects_root, paths):
    """ Checks that no exceptions are raised when similar paths are created
    and that the procedure is in fact performing the desired filesystem
    changes. """
    assert not os.path.isdir(os.path.join(projects_root, paths[0]))
    assert not os.path.isdir(os.path.join(projects_root, paths[1]))
    git_org._ensure_dir_exists(os.path.join(projects_root, paths[0]))
    git_org._ensure_dir_exists(os.path.join(projects_root, paths[1]))
    assert os.path.isdir(os.path.join(projects_root, paths[0]))
    assert os.path.isdir(os.path.join(projects_root, paths[1]))


def test_clone_same_parent(projects_root, monkeypatch):
    """ An integration test for the clone command. Checks for bug where it
    fails if the paths they share are the same. """
    monkeypatch.setattr(git_org, '_clone', lambda x, y: None)
    git_org.clone(projects_root, 'git@github.com:my/same/path/repo1.git')
    git_org.clone(projects_root, 'git@github.com:my/same/path/repo2.git')
