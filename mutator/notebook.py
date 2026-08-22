"""Read and write the mutator's notebook. Nothing is ever overwritten in place.

Entries are append-only and the summary is versioned on every rewrite, so the record of what the
mutator believed at each round survives being wrong later.
"""
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
# A lineage keeps its own notebook. Convergence is only evidence if the lineages cannot read
# each other -- a second run that opens the first run's results table is copying, not
# converging, and it would look identical in the output.
NB = os.environ.get("MUTATOR_NB") or os.path.join(HERE, "notebook")
ENTRIES, VERSIONS, CANDIDATES = (os.path.join(NB, d) for d in ("entries", "versions", "candidates"))
SUMMARY = os.path.join(NB, "summary.md")


def _ensure():
    for d in (NB, ENTRIES, VERSIONS, CANDIDATES):
        os.makedirs(d, exist_ok=True)


def _headline(text):
    """First sentence of the CONJECTURE, for the compact listing of older rounds."""
    m = re.search(r"##\s*CONJECTURE\s*\n(.+?)(?:\n\s*\n|\n##)", text, re.S)
    body = " ".join(m.group(1).split()) if m else " ".join(text.split())
    return (body[:150] + "...") if len(body) > 150 else body or "(no conjecture)"


def read():
    """Everything the mutator is shown of its own history. None if it has never run."""
    _ensure()
    paths = sorted(glob.glob(os.path.join(ENTRIES, "iter_*.md")))
    if not paths and not os.path.exists(SUMMARY):
        return None
    entries = []
    for p in paths:
        text = open(p).read()
        entries.append({"n": int(re.search(r"iter_(\d+)", p).group(1)),
                        "headline": _headline(text), "text": text, "path": p})
    summary = open(SUMMARY).read() if os.path.exists(SUMMARY) else ""
    return {"summary": summary, "entries": entries}


def next_iteration():
    _ensure()
    paths = sorted(glob.glob(os.path.join(ENTRIES, "iter_*.md")))
    return int(re.search(r"iter_(\d+)", paths[-1]).group(1)) + 1 if paths else 0


def commit_entry(n, text):
    """Write and close the entry. Called BEFORE the pipeline runs -- that ordering is the point."""
    _ensure()
    path = os.path.join(ENTRIES, f"iter_{n:03d}.md")
    with open(path, "w") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    return path


def append_entry(n, text):
    """Add the machine-computed OUTCOME and the mutator's VERDICT to an already-committed entry."""
    path = os.path.join(ENTRIES, f"iter_{n:03d}.md")
    with open(path, "a") as fh:
        fh.write(text)
    return path


def save_candidate(n, prompt):
    _ensure()
    path = os.path.join(CANDIDATES, f"prompt_{n:03d}.txt")
    with open(path, "w") as fh:
        fh.write(prompt)
        fh.flush()
        os.fsync(fh.fileno())
    return path


def load_candidate(n):
    return open(os.path.join(CANDIDATES, f"prompt_{n:03d}.txt")).read()


def write_summary(text):
    """Version the outgoing summary before replacing it."""
    _ensure()
    if os.path.exists(SUMMARY):
        v = len(glob.glob(os.path.join(VERSIONS, "summary_v*.md"))) + 1
        with open(os.path.join(VERSIONS, f"summary_v{v:03d}.md"), "w") as fh:
            fh.write(open(SUMMARY).read())
    with open(SUMMARY, "w") as fh:
        fh.write(text)
    return SUMMARY


if __name__ == "__main__":
    nb = read()
    if nb is None:
        print(f"notebook empty. next iteration: {next_iteration()}")
    else:
        print(f"summary: {len(nb['summary'].split())} words, {len(nb['entries'])} entries, "
              f"next iteration: {next_iteration()}")
        for e in nb["entries"]:
            print(f"  iter {e['n']:03d}: {e['headline'][:90]}")
