try:
    from setuptools import setup, find_packages
except ImportError:
    import ez_setup

    ez_setup.use_setuptools()
    from setuptools import setup, find_packages


# class BuildCommand(build):
#     def run(self):
#         build.run(self)
#
#
# class InstallCommand(install):
#     def run(self):
#         if not self._called_from_setup(inspect.currentframe()):
#             # Run in backward-compatibility mode to support bdist_* commands.
#             install.run(self)
#         else:
#             install.do_egg_install(self)  # OR: install.do_egg_install(self)

requirements = []
with open('requirements.txt', "r") as requirements_file:
    for line in requirements_file:
        requirements.append(line.strip())

# requirements.append("git+git://github.com/mattpaletta/configparser.git#egg=configparser")

setup(
        name = "bench",
        version = "0.0.1",
        url = 'https://github.com/mattpaletta/bench',
        packages = find_packages(),
        include_package_data = True,
        install_requires = requirements,
        author = "Matthew Paletta",
        author_email = "mattpaletta@gmail.com",
        description = "Benchmarking library.",
        license = "BSD",
        classifiers = [
            'Development Status :: 3 - Alpha',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: BSD License',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Topic :: Communications',
        ],
        entry_points={
            'console_scripts': [
                'bench = bench.bench:main',
            ]
        },
        package_data={'bench': ['resources/argparse.yml']},
)