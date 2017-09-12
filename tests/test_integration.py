import os
import pytest
from git_org import git_org


@pytest.fixture(scope="module")
def cloneable_git_url():
    return "ssh://git@github.com/d6e/git-org.git"


def test_dry_run_organize(projects_root, monkeypatch, cloneable_git_url):
    """ Assert that dry run doesn't make fileystem changes. """
    monkeypatch.setattr(git_org, 'prompt_user_approval', lambda: True)
    monkeypatch.setattr(git_org, 'print_fs_changes', lambda x: x)
    pre_org_fs = _get_fs(projects_root)
    with pytest.raises(SystemExit):
        git_org.organize(projects_root, dry_run=True)
    post_org_fs = _get_fs(projects_root)
    assert pre_org_fs == post_org_fs


def test_dry_run_clone(projects_root, monkeypatch, cloneable_git_url):
    """ Assert that dry run doesn't make fileystem changes. """
    fs_path = git_org.url_to_fs_path(projects_root, cloneable_git_url)
    pre_org_fs = _get_fs(projects_root)
    with pytest.raises(SystemExit):
        git_org.clone(cloneable_git_url, fs_path, dry_run=True)
    post_org_fs = _get_fs(projects_root)
    assert pre_org_fs == post_org_fs


def _get_fs(projects_root):
    root_name = os.path.basename(projects_root)
    fs = []
    for path, dirs, files in os.walk(projects_root):
        relative_path = root_name + path.split(root_name)[1]
        fs.append((relative_path, dirs, files))
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
    git_org.organize(projects_root)
    post_org_fs = _get_fs(projects_root)
    assert post_org_fs == expected


def test_clone(projects_root, cloneable_git_url):
    """ A heavier, more fragile integration tests. Ensures that the git
    library works and everything else. """
    fs_path = git_org.url_to_fs_path(projects_root, cloneable_git_url)
    assert not os.path.isdir(fs_path)
    assert not os.path.isdir(os.path.join(fs_path, '.git'))
    git_org._clone(cloneable_git_url, fs_path)
    assert os.path.isdir(fs_path)
    assert os.path.isdir(os.path.join(fs_path, '.git'))
