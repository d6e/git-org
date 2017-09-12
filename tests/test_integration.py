import os
from git_org import git_org


def test_clone(projects_root):
    """ A heavier, more fragile integration tests. Ensures that the git
    library works and everything else. """
    url = "ssh://git@github.com/d6e/git-org.git"
    fs_path = git_org.url_to_fs_path(projects_root, url)
    assert not os.path.isdir(fs_path)
    assert not os.path.isdir(os.path.join(fs_path, '.git'))
    git_org._clone(url, fs_path)
    assert os.path.isdir(fs_path)
    assert os.path.isdir(os.path.join(fs_path, '.git'))
