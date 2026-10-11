"""Compile the Claude Code skills TechNext wrote into this site (index.html).

Reads ~/.claude/skills/<name>/SKILL.md for every skill in OWN and publishes it
in full: its text files are embedded for the in-page reader and a zip is
written to install from. Third-party skills are not listed here.

    python tools/build_skills.py

Writes assets/skills/skills.js (window.SKILLS) and assets/skills/<name>.zip,
and stamps skills.js?v=<md5> into index.html. Re-run after every skill
update, then commit and push (repo TechNextSG/technext-claude-skills).
"""
import datetime
import hashlib
import json
import pathlib
import re
import zipfile

from PIL import Image

SITE = pathlib.Path(__file__).resolve().parent.parent
SKILLS = pathlib.Path.home() / ".claude" / "skills"
OUT = SITE / "assets" / "skills"

# Skills TechNext wrote. Add a new one here to publish it.
OWN = ["marketing-team", "nexi-character", "nexi-explains-posters", "nexi-video",
       "technext-presentations", "technext-site-posts", "technext-social-posts"]

# Filter group per skill.
GROUP = {
    "nexi-video": "video", "nexi-character": "video",
    "technext-presentations": "decks",
    "technext-social-posts": "social", "technext-site-posts": "social", "nexi-explains-posters": "social",
    "marketing-team": "team",
}

# How the page names one job of a skill ("10 steps per <unit>") and the heading over its steps.
JOB = {
    "nexi-video": ("video", "How we make one video"),
    "technext-presentations": ("deck change", "How we change a deck"),
    "nexi-character": ("reaction", "How Nexi reacts"),
    "nexi-explains-posters": ("poster", "How we make one poster"),
    "technext-social-posts": ("batch", "How we make a post batch"),
    "technext-site-posts": ("batch", "How we make a site-post batch"),
    "marketing-team": ("run", "Every team run"),
}
ART = {
    "nexi-video": "nexi-present.webp",
    "technext-presentations": "skill-presentations.webp",
    "nexi-character": "nexi-knock.webp",
    "nexi-explains-posters": "nexi-wow.webp",
    "technext-social-posts": "nexi-celebrate.webp",
    "technext-site-posts": "nexi-point-left.webp",
    "marketing-team": "nexi-clap.webp",
}

# One plain line per skill for the cards and the header (SKILL.md openings are written for Claude).
BLURB = {
    "marketing-team": "Runs TechNext's AI marketing team: Pixel designs drips and posts, Razel finds 20 leads a day, Ralph plans one post a day. Every output waits for the owner's OK.",
    "nexi-character": "Who Nexi is: a tiny robot with a cat's attitude. 46 emotions and 30 variants, the rage ladder, and a kit that plays any reaction in one call.",
    "nexi-explains-posters": "One cinematic 3:4 poster per Nexi Explains episode, each built from that episode's own world. Never a template.",
    "nexi-video": "Makes Nexi explainer videos: Odoo walkthroughs, quick tips and solution films with voice, captions, music and a strict release gate.",
    "technext-presentations": "Edits and checks TechNext's interactive HTML decks: company profile, Odoo series, client proposals, PDFs and the launcher.",
    "technext-site-posts": "Original illustrated 3:4 posts, one per technext.asia service, using the website only as a reference.",
    "technext-social-posts": "Cinematic social posts that pair a TechNext service with a real Odoo process: 3:4 images and 9:16 reels, audited before delivery.",
}

# Step titles for skills whose steps are not written as "**Title.** text".
TITLES = {
    "marketing-team": ["Read the brief", "Fix blocked cards", "Link new folders", "Report"],
    "technext-site-posts": ["Set up", "Concepts", "Build", "Render + audit", "Deliver", "Log the batch"],
}

# Folders never published: render caches and big binaries that stay on the PC.
SKIP_DIRS = {"__pycache__", "nexi-cam", "node_modules"}
MAX_ZIP_FILE = 10 * 1024 * 1024
# The reader shows docs and scripts, not the kit's example pages or vendored libraries.
READER_SKIP = ("kit/", "examples/")
MAX_DOC = 200 * 1024

# Internal links that must not be published (the site is public).
REDACT = [(re.compile(r"https://docs\.google\.com/spreadsheets/d/[A-Za-z0-9_-]+[^\s)>\"]*"), "(internal Google Sheet link)")]

# Reading order for published skills; anything else follows alphabetically.
ORDER = ["SKILL.md", "reference/rules.md", "reference/content-rules.md", "reference/workflow.md", "reference/engine.md",
         "reference/build-and-ship.md", "reference/decks.md", "reference/recipes.md", "reference/design.md",
         "reference/qa-checklist.md", "reference/lessons.md", "reference/film-template.js"]
TEXT = {".md", ".js", ".py", ".json", ".txt", ".css", ".html", ".yml", ".yaml"}


def redact(text):
    for rx, sub in REDACT:
        text = rx.sub(sub, text)
    return text


def frontmatter(text):
    """Return (meta dict, body) for a SKILL.md with a --- YAML-ish header."""
    meta, body = {}, text
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?", text, re.S)
    if m:
        body = text[m.end():]
        for line in m.group(1).splitlines():
            k, sep, v = line.partition(":")
            if not sep or line[:1] in " \t#":
                continue
            v = v.strip()
            if len(v) > 1 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            meta[k.strip()] = v
    return meta, body


def plain(text):
    text = re.sub(r"`([^`]*)`", r"\1", text)
    return re.sub(r"\*\*([^*]*)\*\*", r"\1", text)


def summary(body):
    """The first paragraph under the title: written for people, unlike the trigger description."""
    m = re.search(r"^# .*?\n\s*\n(.+?)(?:\n\s*\n|$)", body, re.S | re.M)
    if not m:
        return ""
    return plain(" ".join(m.group(1).split()))


def pipeline(body):
    """Top-level numbered steps under the pipeline (or 'Every run') heading: [{t, d}]."""
    m = re.search(r"^## (?:The pipeline|Pipeline|Every run).*?$(.*?)(?=^## |\Z)", body, re.S | re.M)
    if not m:
        return []
    steps = []
    for s in re.finditer(r"^\d+\.\s+(.*(?:\n(?!\d+\.\s)[ \t]+.*)*)", m.group(1), re.M):
        text = " ".join(s.group(1).split())
        b = re.match(r"\*\*(.+?)\*\*\s*(.*)$", text)
        if b:
            title, rest = re.sub(r"\s*\(.*$", "", b.group(1)).rstrip(".:"), b.group(2)
        else:
            first = plain(text)
            title = re.split(r"[.;:(]|, | - ", first, maxsplit=1)[0].strip()
            if len(title) > 38:
                title = title[:38].rsplit(" ", 1)[0] + "..."
            rest = first
        rest = plain(rest).strip()
        d = re.split(r"(?<=[.!?])\s", rest, maxsplit=1)[0]
        steps.append({"t": plain(title), "d": d})
    return steps


def files_of(folder):
    out = [p for p in folder.rglob("*")
           if p.is_file() and not SKIP_DIRS.intersection(p.relative_to(folder).parts)]
    rel = lambda p: p.relative_to(folder).as_posix()
    rank = {name: i for i, name in enumerate(ORDER)}
    return sorted(out, key=lambda p: (rank.get(rel(p), len(ORDER)), rel(p)))


def write_zip(name, folder, dest):
    """Deterministic zip (fixed timestamps, sorted) so unchanged skills give identical bytes."""
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(files_of(folder), key=lambda p: p.relative_to(folder).as_posix()):
            if p.stat().st_size > MAX_ZIP_FILE:
                continue
            info = zipfile.ZipInfo(f"{name}/{p.relative_to(folder).as_posix()}", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            data = p.read_bytes()
            if p.suffix.lower() in TEXT:
                data = redact(data.decode("utf-8", errors="replace")).replace("\r\n", "\n").encode("utf-8")
            z.writestr(info, data)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    skills = []
    for sid in OWN:
        folder = SKILLS / sid
        raw = (folder / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        meta, body = frontmatter(raw)
        files = files_of(folder)
        newest = max(p.stat().st_mtime for p in files)
        docs = []
        for p in files:
            rel = p.relative_to(folder).as_posix()
            if p.suffix.lower() not in TEXT or rel.startswith(READER_SKIP) or p.stat().st_size > MAX_DOC:
                continue
            text = body.lstrip("\n") if rel == "SKILL.md" else p.read_text(encoding="utf-8", errors="replace")
            docs.append({"path": rel, "kind": "md" if p.suffix.lower() == ".md" else "code",
                         "text": redact(text.replace("\r\n", "\n"))})
        lessons = folder / "reference" / "lessons.md"
        unit, pipe = JOB.get(sid, ("job", "How we do one job"))
        s = {
            "id": sid,
            "name": meta.get("name") or sid,
            "desc": redact(meta.get("description", "")),
            "group": GROUP.get(sid, "team"),
            "invoke": "manual" if meta.get("disable-model-invocation", "").lower() == "true" else "auto",
            "nfiles": len(files),
            "date": datetime.date.fromtimestamp(newest).isoformat(),
            "docs": docs,
            "summary": BLURB.get(sid) or redact(summary(body)),
            "steps": [dict(st, t=TITLES[sid][i]) if sid in TITLES and i < len(TITLES[sid]) else st
                      for i, st in enumerate(pipeline(body))],
            "lessons": len(re.findall(r"^## ", lessons.read_text(encoding="utf-8"), re.M)) if lessons.exists() else 0,
            "unit": unit, "pipe": pipe,
            "zip": f"assets/skills/{sid}.zip",
        }
        if sid in ART:
            w, h = Image.open(SITE / "assets" / "img" / ART[sid]).size
            s["art"] = {"src": "assets/img/" + ART[sid], "w": w, "h": h}
        write_zip(sid, folder, OUT / f"{sid}.zip")
        size = (OUT / f"{sid}.zip").stat().st_size
        s["zipsize"] = f"{size / 1048576:.1f} MB" if size >= 1048576 else f"{max(1, round(size / 1024))} KB"
        skills.append(s)

    data = {"built": datetime.date.today().isoformat(), "skills": skills}
    js = ("/* Generated by tools/build_skills.py from ~/.claude/skills. Do not edit by hand. */\n"
          "window.SKILLS=" + json.dumps(data, ensure_ascii=True, separators=(",", ":")) + ";\n")
    (OUT / "skills.js").write_text(js, encoding="utf-8", newline="\n")
    # Cache-bust: GitHub Pages caches for 10 min, so stamp the data hash into the page.
    page = SITE / "index.html"
    html = page.read_text(encoding="utf-8")
    ver = hashlib.md5(js.encode()).hexdigest()[:8]
    stamped = re.sub(r"assets/skills/skills\.js\?v=[0-9a-z]*", "assets/skills/skills.js?v=" + ver, html)
    if stamped != html:
        page.write_text(stamped, encoding="utf-8", newline="\n")
    for s in skills:
        print(f"{s['id']:24} {len(s['steps']):2} steps {len(s['docs']):3} docs  zip {s['zipsize']}")
    print(f"{len(skills)} skills -> {OUT.relative_to(SITE)} ({len(js) // 1024} KB skills.js)")


if __name__ == "__main__":
    main()
