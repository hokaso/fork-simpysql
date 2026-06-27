import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="simpysqls_hks",
    version="0.0.4",
    author="jeanku, liubin, Hocassian",
    author_email="hokaso@qq.com",
    description="A simple mysql orm base on pymysql",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hokaso/fork-simpysql",
    packages=["simpysql", "simpysql/Util", "simpysql/Eloquent", "simpysql/Connections"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        'pymysql',
        'pandas',
        'configparser',
        'DBUtils',
        'pymongo',
    ],
    entry_points={
        "console_scripts": ['simpysql = DBModel:DBModel']
    },
    keywords='MySQL ORM',
    python_requires='>=3',
)