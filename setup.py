from setuptools import find_packages, setup


setup(
    version="0.0.1",
    name="OdfEdit",
    description="ODF Edition Tool",
    packages=find_packages(),
    include_package_data=True,
    package_data={'': ['*.png', 'OdfEdit_res/*.png']},
    entry_points={
        'console_scripts': ["OdfEdit = src:OdfEdit.main"]
    }
)
