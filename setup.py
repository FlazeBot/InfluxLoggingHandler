import ast
import re
import setuptools
from pathlib import Path

with open("requirements.txt") as stream:
    raw = stream.read().splitlines()
    requirements = [x for x in raw if not x.startswith("git+")]

long_description = (Path(__file__).parent / "README.md").read_text(encoding="UTF-8")

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('influx_logging_handler/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(f.read().decode('UTF-8')).group(1)))

setuptools.setup(
    name="InfluxLoggingHandler",
    version=version,
    description="Handler for logging messages to InfluxDB 2 via Python logging -module.",
    long_description=long_description,
    author="Kimmo Huoman",
    author_email="flazebot@gmail.com",
    url="https://github.com/FlazeBot/InfluxLoggingHandler",
    packages=[
        "influx_logging_handler"
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: AsyncIO",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Communications",
        "Topic :: Internet",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    license="MIT License",
    keywords=[
        "influx_logging_handler",
        "influx_logging",
        "influx",
        "python",
        "discord.py"
    ],
    long_description_content_type="text/markdown",
    install_requires=requirements,
    python_requires=">=3.8.0",
    project_urls={
        "Source": "https://github.com/FlazeBot/InfluxLoggingHandler",
        "Issue Tracker": "https://github.com/FlazeBot/InfluxLoggingHandler/issues",
    },
)