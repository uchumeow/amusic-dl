from setuptools import setup

setup(
    name="amusic-dl",
    version="1.0.0",
    description="Apple Music → YouTube → MP3 downloader",
    author="uchumeow",
    url="https://github.com/uchumeow/amusic-dl",
    py_modules=["amusic_dl"],
    install_requires=[
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "amusic-dl=amusic_dl:main",
        ],
    },
    python_requires=">=3.6",
)
