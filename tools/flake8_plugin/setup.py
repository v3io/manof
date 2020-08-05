from __future__ import with_statement
import setuptools

requires = [
    'flake8 > 3.0.0',
]

flake8_entry_point = 'flake8.extension'

setuptools.setup(
    name='flake8-igz',
    license='MIT',
    version='0.1.0',
    description='iguazio\'s twisted extension to flake8',
    author='Adam Melnick',
    author_email='adamm@iguazio.com',
    provides=['flake8_igz'],
    py_modules=['flake8_igz'],
    install_requires=requires,
    entry_points={
        flake8_entry_point: [
            'flake8-igz.single_quote_strings = flake8_igz:single_quote_strings',
            'flake8-igz.multiline_string_on_newline ='
            ' flake8_igz:multiline_string_on_newline',
            'flake8-igz.multiline_string_double_quotes ='
            ' flake8_igz:multiline_string_double_quotes',
            'flake8-igz.ctx_log_non_string_first_param ='
            ' flake8_igz:ctx_log_non_string_first_param',
            'flake8-igz.class_name_camel_case = flake8_igz:class_name_camel_case',
            'flake8-igz.logger_forbid_passing_self ='
            ' flake8_igz:logger_forbid_passing_self',
        ],
    },
    classifiers=[],
)
