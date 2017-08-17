import pytest
from git_org import url_to_fs_path


@pytest.mark.parametrize(
    "url, expect",
    [
        ('ssh://git@github.com:d6e/git-org.git', 'myroot/github.com/d6e/git-org'),
        ('ssh://git@git.example.com:7999/~user/mything.git', 'myroot/git.example.com/user/mything'),
        ('http://github.com/rust-lang/rust.git', 'myroot/github.com/rust-lang/rust'),
        ('https://user@git.example.com/scm/~user/rust.git', 'myroot/git.example.com/user/rust'),
        ('ftps://host.xz:9999/path/to/repo.git/', 'myroot/host.xz/path/to/repo'),
        ('ssh_host:chip8.git', 'myroot/ssh_host/chip8'),
        ('user@host.xz:/~user/path/to/repo.git/', 'myroot/host.xz/user/path/to/repo'),
        ('file:///path/to/repo.git/', 'file:///path/to/repo.git/'),  # ignore
        ('/home/absolute/path/to/myproject', '/home/absolute/path/to/myproject'),  # ignore
    ])
def test_url_to_fs_path(url, expect):
    new_path = url_to_fs_path('myroot', url)
    assert expect == new_path
