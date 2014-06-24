#!/usr/bin/env python
#-*- coding: UTF-8 -*-

"""A simple masivefilenames editor that take advantage of the power of VIM"""

import argparse
import os
import re
import sys
import tempfile
import time

from subprocess import Popen, PIPE, check_output

START_TIME = time.time()
VIMPATH = "/usr/bin/vim" #FIXME: hardcoded

parser = argparse.ArgumentParser(
    description="""vimrenamer allows to edit tons of files a dirs names in """
        """the best text editor ever. If you master vim you can master """
        """file system xD .""")
parser.add_argument("-v", '--verbose', action="append_const", dest="verbose",
    const=1, default=[2], help='Increase the verbosity of the output.')
parser.add_argument("-q", '--quiet', action="append_const", dest="verbose",
    const=-1, help='Decrease the verbosity of the output.')
parser.add_argument("-r", '--recursive', default=False, action="store_true",
    help="Go through all dirs present in the root dir.")
parser.add_argument("-l", '--loop', default=False, action="store_true",
    help="Repeat until no changes are made.")

VERBOSE = 2

def vprint(message, verbose=2):
    if VERBOSE >= verbose:
        try:
            print(message)
        except UnicodeEncodeError:
            print(message.encode("utf8"))

error = lambda m: vprint("E: %s" % m, 0)
warning = lambda m: vprint("W: %s" % m, 1)
info = lambda m: vprint(m, 2)
moreinfo = lambda m: vprint("+I: %s" % m, 3)
debug = lambda m: vprint("D: %s" % m, 4)


def debug(*args):
    """
    Write to stderr for debug
    """

    sys.stderr.writelines("".join(
        ["%7.2f" % (time.time() - START_TIME),
        " ",
        " ".join([str(e) for e in args]) + "\n",
        ]))


def dump(filename, lines):
    """
    Writes lines to the file (filename can be a fd int).
    """
    if type(filename) is int:
        fobj = os.fdopen(filename, "w")
    else:
        fobj = open(filename, "w")

    fobj.writelines([str(s) + "\n" for s in lines])
    fobj.close()


def load(filename):
    """
    Load a file and return their striped content.
    """
    return [s.rstrip("\n") for s in open(filename).readlines()]


def list2file(lines):
    tmp_fd, tmp_name = tempfile.mkstemp(".vimrenamer")
    dump(tmp_fd, lines)
    return tmp_name


def move(src, dst):
    """
    The best "move" implementation ever, just a unix mv wrapper.
    Maybe shutil.move will be a cross plataform option on its next version.


    If *dst* is "" or None:
        If *src* is a dir:
            Deletes dir *src* and all it's empty parents.
        Else:
            Deletes file *src*.
    Else:
        If *dst* has path.sep:
            Create *dst* dir and it's parents.
        Executes "mv *src* *dst*".
    """

    if dst in ("", None):
        if src.endswith("/"):
            debug("Removing directory: %s" % src)
            os.removedirs(src)
        else:
            debug("Removing file: %s" % src)
            os.remove(src)
        error = 0

    else:
        if os.path.sep in dst:
            dst_dir = os.path.dirname(dst)
            if not os.path.exists(dst_dir):
                debug("Creating dest dir %s" % dst_dir)
                os.makedirs(dst_dir)
        debug("Moving %s to %s" % (src, dst))

        process = Popen(["", "--", src, dst], 0, "/bin/mv", stderr=PIPE,
            stdout=PIPE, env={"LANG":"C", "LC_ALL":"C"})

        error = process.wait()

        if error == 1:
            stderr = "\n".join(process.stderr.readlines())
            errors = {
                2: r""": cannot create regular file `.*': """
                    """Permission denied\n""",
                3: r""": cannot move `.*' to `.*': """
                    """No such file or directory\n""",
                4: r""": cannot move `.*' to `.*': Permission denied\n""",
                5: r""": cannot stat `.*': No such file or directory\n""",
                }

            while error == 1 and len(errors) > 0:
                e, r = errors.popitem()

                if re.match(r, stderr):
                    error = e

    return error


def listeditor(llines, rlines=None):
    """
    Simple wrapper to the vim editor. If rlines use vimdiff but return only
    llines.
    """

    lname = list2file(llines)

    if rlines:
        rname = list2file(rlines)
        assert Popen(["", "-d", lname, rname], 0, VIMPATH).wait() == 0
        os.remove(rname)
    else:
        assert Popen(["", lname], 0, VIMPATH).wait() == 0

    llines = load(lname)
    os.remove(lname)
    return llines 


def listdir(path="./", recursive=False):
    """
    Return a ordened list of dirs and files of the path.
    """

    command = "find" if recursive else "ls"
    listdir = check_output(command)
    listdir = listdir.splitlines()

    files = set()
    dirs = set()
    for name in listdir:
        if recursive:
            toadd = name[2:]
        else:
            toadd = name
        toremove = os.path.join(*os.path.split(toadd)[:-1])

        if os.path.isdir(name):
            dirs.add(toadd + "/")
            try:
                dirs.remove(toremove + "/")
            except:
                pass
        else:
            files.add(toadd)
            try:
                dirs.remove(toremove + "/")
            except:
                pass
            try:
                files.remove(toremove)
            except:
                pass

    return sorted(dirs) + sorted(files)



def main():
    """
    The main function.
    """

    OPTIONS = vars(parser.parse_args())
    VERBOSE = sum(OPTIONS["verbose"])

    recursive = OPTIONS['recursive']
    loop = OPTIONS['loop']

    keep = True
    while keep:
        startlist = listdir(recursive=recursive)
        finallist = listeditor(startlist)

        while len(startlist) != len(finallist):
            print("""No se debe modificar la cantidad de lineas, se """
                """abrirá un vimdiff con la lista original a la derecha """
                """para referencia.""")
            time.sleep(1)
            finallist = listeditor(finallist, startlist)

        changes = [line for line in
             map(lambda x, y: (x, y) if x != y else None, startlist,
                 finallist) if line]

        if changes:
            changes = listeditor(changes)

            for args in [eval(line) for line in changes]:
                move(*args)
        else:
            changes = False
            debug("No hay cambios que aplicar.")

        keep = changes and loop



if __name__ == "__main__":
    exit(main())
