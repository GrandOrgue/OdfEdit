from setuptools import find_packages, setup

setup(
    version="2.1.0",
    name="OdfEdit",
    description="ODF Edition Tool",
    packages=find_packages(),
    include_package_data=True,
    package_data={'': ['*.png', 'src/*.png', '*.txt', 'src/*.txt', '*.wav']},
    entry_points={
        'console_scripts': ["OdfEdit = src:OdfEdit.main"]
    }
)
