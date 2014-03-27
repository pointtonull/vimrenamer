#!/usr/bin/env python
#-*- coding: UTF-8 -*-

"""A simple masivefilenames editor that take advantage of the power of VIM"""

from subprocess import Popen, PIPE
import os
import re
import sys
import tempfile
import time

INICIO = time.time()
VIMPATH = "/usr/bin/vim" #FIXME: hardcoded


def debug(*args):
    """
    Write to stderr for debug
    """

    sys.stderr.writelines("".join(
        ["%7.2f" % (time.time() - INICIO),
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

    If dst is "" or None the src file will be deleted.
    If dst dir does not exist it will be created
    """
    
    if dst in ("", None):
        debug("Removing %s" % src)

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

    listdir = os.listdir(path)

    files = []
    dirs = []
    for name in listdir:
        if os.path.isdir(name):
            dirs.append(name + "/")
        else:
            files.append(name)

    return sorted(dirs) + sorted(files)



def main():
    """
    The main function.
    """

    startlist = listdir()
    finallist = listeditor(startlist)

    while len(startlist) != len(finallist):
        print("""No se debe modificar la cantidad de lineas, se abrirá un"""
        """ vimdiff con la lista original a la derecha para referencia.""")
        time.sleep(3)
        finallist = listeditor(finallist, startlist)
    
    changes = [line for line in
         map(lambda x, y: (x, y) if x != y else None, startlist, finallist)
            if line]

    if changes:
        changes = listeditor(changes)

        for args in [eval(line) for line in changes]:
            move(*args)
    else:
        debug("No hay cambios que aplicar.")



if __name__ == "__main__":
    exit(main())
