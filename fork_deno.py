# This is a script which takes a tag (e.g. 'v1.13.2') of deno and creates and
# pushes a fork of it such that the deno-cli crate is marked as a library.
# See https://github.com/denoland/deno/issues/9728
# Assumes you have push access to the repository in REMOTE.

import os
import subprocess
import sys
import tempfile
import textwrap

# The repository (git remote formatted) that the fork should be pushed to.
REMOTE = 'git@github.com:aplite-lang/deno'

def usage():
    print("Usage: {} v1.13.2".format(sys.argv[0]))
    sys.exit(1)


def main():
    # Check python version, fail if <3.5
    assert sys.version_info >= (3, 5)

    # Fetch the version of deno to fork.
    # Fail if the command line argument is not found, or the version doesn't
    # start with a 'v'.
    if len(sys.argv) != 2:
        usage()

    version = sys.argv[1]

    if version[0] != 'v':
        usage()

    # Create a temporary directory.
    tempdir = tempfile.TemporaryDirectory()

    # Move to the directory, and clone deno.
    os.chdir(tempdir.name)
    subprocess.run(["git", "clone", "https://github.com/denoland/deno", "--branch", version], check=True)

    # Move into the deno directory for our modifications.
    os.chdir('deno')

    # Add our forked remote.
    subprocess.run(["git", "remote", "add", "fork", REMOTE], check=True)

    # Our overarching goal here is to make deno-cli a library crate rather than
    # an application crate. As such we need to add a [lib] section to
    # `cli/Cargo.toml`, and to make it useful, we need to make all the modules
    # in `cli/main.rs` reexported.

    # We add a [lib] section before the [[bin]] section in cli/Cargo.toml.
    with open('cli/Cargo.toml', 'r') as cargo_toml_file:
        cargo_toml = cargo_toml_file.readlines()
        
        index_of_bin = cargo_toml.index('[[bin]]\n')

        lib_section = ["[lib]\n", 'name="deno"\n', 'path="main.rs"\n', '\n']

        new_cargo_toml = cargo_toml[1:index_of_bin] + lib_section + cargo_toml[index_of_bin:]

    with open('cli/Cargo.toml', 'w') as cargo_toml_file:
        cargo_toml_file.writelines(new_cargo_toml)

    # We replace all occurences of `mod X;` with `pub mod X;` in cli/main.rs.
    with open('cli/main.rs', 'r') as main_rs_file:
        main_rs = main_rs_file.readlines()
        
        new_main_rs = []

        for line in main_rs:
            if line.startswith('mod ') and line.endswith(';\n'):
                new_main_rs.append('pub ' + line)
            else:
                new_main_rs.append(line)

    with open('cli/main.rs', 'w') as main_rs_file:
        main_rs_file.writelines(new_main_rs)

    # Now we git commit, tag, and try to push.
    subprocess.run(['git', 'commit', '-am', 'Fork of {}'.format(version)], check=True)

    subprocess.run(['git', 'tag', '{}-fork'.format(version)], check=True)

    subprocess.run(['git', 'push', '-u', 'fork', '{}-fork'.format(version)], check=True)


if __name__ == '__main__':
    main()
