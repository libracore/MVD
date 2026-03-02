# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from pathlib import Path

def get_git_commit():
    git_head = Path(__file__).parent.parent / ".git/HEAD"

    if git_head.exists():
        ref = git_head.read_text().strip()
        if ref.startswith("ref:"):
            ref_path = Path(__file__).parent.parent / ".git" / ref.split(" ")[1]
            return ref_path.read_text().strip()[:7]
    return "---"

__version__ = '17.0.0 ({0})'.format(get_git_commit())


