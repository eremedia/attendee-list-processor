from setuptools import setup, find_packages

setup(
    name = "attendee-list-processor",
    version = "0.2",
    packages = find_packages(),
    description="Process attendee lists; generate QR codes.",
    entry_points = {
        'console_scripts': {
            'process_attendee_list = attendee_list_processor.core:main'
        }
    },
    long_description=open('README.md').read(),
    license = 'BSD',
    install_requires = [
        "phonenumbers==5.8b1",
        "tablib==0.9.11"
    ],
)
