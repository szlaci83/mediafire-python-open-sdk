from distutils.core import setup
from pip.req import parse_requirements

requirements = parse_requirements('requirements.txt')
install_requires = [str(r.req) for r in requirements]

setup(
    name='mediafire',
    version='0.1.0',
    author='Roman Yepishev',
    author_email='roman.yepishev@gmail.com',
    packages=['mediafire'],
    url='https://github.com/MediaFire/mediafire-python-open-sdk',
    license='LICENSE.txt',
    description='Python MediaFire client library',
    long_description=open('README.rst').read(),
    install_requires=install_requires,
)
