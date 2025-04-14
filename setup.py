from setuptools import setup, find_packages

setup(
    name="ai_multi_comms_engine",
    version="0.1.0",
    packages=find_packages(where="src_dev"),
    package_dir={"": "src_dev"},
) 