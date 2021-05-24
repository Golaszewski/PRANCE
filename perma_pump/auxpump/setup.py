from setuptools import setup, find_packages

setup(
    name='auxpump',
    version='1.0',
    packages=find_packages(),
    data_files=[('', ['auxpump/config.json'])],
    license='MIT',
    description='',
    long_description=open('README.md').read(),
    install_requires=[],
    url='https://github.com/dgretton/auxpump.git',
    author='Dana Gretton',
    author_email='dgretton@mit.edu'
)
