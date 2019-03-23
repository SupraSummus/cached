from setuptools import setup


setup(
    name='cached',
    version='0.0.0',
    description='Cache process output',
    license='MIT',
    url='https://github.com/SupraSummus/cached',
    classifiers=[
        'Operating System :: POSIX',
        'Topic :: System',
        'Topic :: Utilities',
    ],
    keywords='unix pipe cache command',
    py_modules=['cached'],
    scripts=[
        'bin/cached',
    ],
)
