#!/usr/bin/env python
"""Run acid test against latest packages on PyPi."""

import os
import subprocess
import sys

import acid


TMP_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                       'pypi_tmp')


def latest_packages(last_hours):
    """Return names of latest released packages on PyPi."""
    process = subprocess.Popen(
        ['yolk', '--latest-releases={hours}'.format(hours=last_hours)],
        stdout=subprocess.PIPE)

    for line in process.communicate()[0].decode('utf-8').split('\n'):
        if line:
            yield line.split()[0]


def download_package(name, output_directory):
    """Download package to output_directory.

    Raise CalledProcessError on failure.

    """
    subprocess.check_call(['yolk', '--fetch-package={name}'.format(name=name)],
                          cwd=output_directory)


def extract_package(path, output_directory):
    """Extract package at path."""
    if path.lower().endswith('.tar.gz'):
        import tarfile
        try:
            tar = tarfile.open(path)
            tar.extractall(path=output_directory)
            tar.close()
            return True
        except (tarfile.ReadError, IOError):
            return False
    elif path.lower().endswith('.zip'):
        import zipfile
        try:
            archive = zipfile.ZipFile(path)
            archive.extractall(path=output_directory)
            archive.close()
        except (zipfile.BadZipfile, IOError):
            return False
        return True

    return False


def main():
    """Run main."""
    try:
        os.mkdir(TMP_DIR)
    except OSError:
        pass

    opts, args = acid.process_args()
    if args:
        # Copy
        names = list(args)
    else:
        names = None

    import time
    start_time = time.time()

    checked_packages = []
    skipped_packages = []
    last_hours = 1
    while True:
        if opts.timeout > 0 and time.time() - start_time > opts.timeout:
            break

        if args:
            if not names:
                break
        else:
            while not names:
                # Continually populate if user did not specify a package
                # explicitly.
                names = [p for p in latest_packages(last_hours)
                         if p not in checked_packages and
                         p not in skipped_packages]

                if not names:
                    last_hours *= 2

        package_name = names.pop(0)
        print(package_name)

        package_tmp_dir = os.path.join(TMP_DIR, package_name)
        try:
            os.mkdir(package_tmp_dir)
        except OSError:
            print('Skipping already checked package')
            skipped_packages.append(package_name)
            continue

        try:
            download_package(package_name, output_directory=package_tmp_dir)
        except subprocess.CalledProcessError:
            print('ERROR: yolk fetch failed')
            continue

        for download_name in os.listdir(package_tmp_dir):
            try:
                if not extract_package(
                        os.path.join(package_tmp_dir, download_name),
                        output_directory=package_tmp_dir):
                    print('ERROR: Could not extract package')
                    continue
            except UnicodeDecodeError:
                print('ERROR: Could not extract package')
                continue

            if acid.check(opts, [package_tmp_dir]):
                checked_packages.append(package_name)
            else:
                return 1

    if checked_packages:
        print('\nTested packages:\n    ' + '\n    '.join(checked_packages))

if __name__ == '__main__':
    sys.exit(main())
