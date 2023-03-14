###############################################################################
# Copyright (c) 2022, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory
# Written by the Merlin dev team, listed in the CONTRIBUTORS file.
# <merlin@llnl.gov>
#
# LLNL-CODE-797170
# All rights reserved.
# This file is part of Merlin, Version: 1.9.1.
#
# For details, see https://github.com/LLNL/merlin.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
###############################################################################

"""
This module is used to check for differences in the test suites between 2 repos.
If there is a difference, the Python CI will run both the old tests on the branch
that currently exists and the new tests from the new branch that you're merging.
"""
import argparse

from filecmp import dircmp


def setup_argparse():
    parser = argparse.ArgumentParser(description="check_for_updates cli parser")
    parser.add_argument("old_tests", type=str, help="Path to the test folder of the repo we're merging into")
    parser.add_argument("new_tests", type=str, help="Path to the test folder of the repo we're merging")
    return parser


def main():
    """
    Using path's to each repo, check if the test suites have changed.
    If they have, return True. Otherwise, False.
    """
    # # Get the repo paths
    # parser = setup_argparse()
    # args = parser.parse_args()

    # comp = dircmp(args.old_tests, args.new_tests)

    # print(bool(comp.diff_files))
    print("check_for_test_updates called")
    # purposely changing this file


if __name__ == "__main__":
    main()