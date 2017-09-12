import os
import pytest
from git_org import git_org
from typing import List, Tuple


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
def test_url_to_fs_path(url, expect, root_name):
    new_path = git_org.url_to_fs_path(root_name, url)
    assert expect == new_path


@pytest.mark.parametrize("data, expected", [([''], ['']),
                                            (['jfds'], ['jfds']),
                                            (['/myroot/a/long/path', '/myroot/a', '/myroot/a/long/path/longer'], ['/myroot/a']),
                                            (['src/10.222.28.136/test', 'src/Xastir'], ['src/10.222.28.136/test', 'src/Xastir']),  # Fails to sorting
                                            (['myroot/notrust', 'myroot/notrust2'], ['myroot/notrust', 'myroot/notrust2']),
                                            (['myroot/notrust2', 'myroot/notrust'], ['myroot/notrust', 'myroot/notrust2'])])
def test_filter_nested_git_repos(data, expected):
    result = git_org.filter_nested_git_repos(data)
    assert result == expected


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
    """ A test for the clone command. Checks for bug where it
    fails if the paths they share are the same. Doesn't actually clone. """
    monkeypatch.setattr(git_org, '_clone', lambda x, y: None)
    git_org.clone(projects_root, 'git@github.com:my/same/path/repo1.git')
    git_org.clone(projects_root, 'git@github.com:my/same/path/repo2.git')
