import setuptools

setuptools.setup(
    name="git-org",
    version="0.1.0",
    packages=['git_org'],
    author="Danielle Jenkins",
    author_email="danielle@d6e.io",
    description="An opinionated approach to filesystem git repo organization.",
    install_requires=["GitPython"],
    url="https://github.com/d6e/git-org",
    entry_points={
            "console_scripts": ["git-org = git_org.git_org:main"]
    }
)
