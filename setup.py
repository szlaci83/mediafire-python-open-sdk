from distutils.core import setup
from pip.req import parse_requirements

requirements = parse_requirements('requirements.txt')
install_requires = [str(r.req) for r in requirements]

setup(
    name='mediafire',
    version='0.2.0',
    author='Roman Yepishev',
    author_email='rye@keypressure.com',
    packages=['mediafire'],
    url='https://github.com/roman-yepishev/mediafire-python-open-sdk',
    license='BSD',
    description='Python MediaFire client library',
    long_description=open('README.rst').read(),
    install_requires=install_requires,
    keywords="mediafire sdk storage api",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'License :: OSI Approved :: BSD License'
    ]
)
