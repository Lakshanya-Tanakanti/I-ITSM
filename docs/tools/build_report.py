"""Builds docs/FINAL_PROJECT_REPORT.pdf from docs/FINAL_PROJECT_REPORT.md.

    python docs/tools/build_report.py

Needs pandoc, XeLaTeX (with the packages fancyhdr, pdflscape, fvextra, booktabs, longtable, caption,
etoolbox) and Pillow. The Markdown stays the single source of truth. Conventions it relies on:

* `<!-- cover -->` ... `<!-- /cover -->`: title page. `<!-- frontmatter -->` ... : declaration and abstract.
* `<!-- landscape -->` ... `<!-- /landscape -->`: the enclosed figure gets its own landscape page.
* Figure: `![Figure N.M: text](path){width=..%}`; table: a bold line `**Table N.M: text**` before the table.
* Chapter headings are written `# Chapter N: Title`, sections `## N.M Title`. The numbers are removed for
  LaTeX, which numbers everything itself. The script then checks that LaTeX's numbers equal the numbers
  written in the Markdown, so text such as "see Figure 4.2" cannot silently drift.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

DOCS = Path(__file__).resolve().parents[1]
SRC = DOCS / "FINAL_PROJECT_REPORT.md"
OUT = DOCS / "FINAL_PROJECT_REPORT.pdf"
RUNNING_HEAD = "I-ITSM final project report"   # page header, right side
COVER_SUBTITLE = "Project report"               # line under the title on the cover

# Usable text area in cm (A4, 2.5 cm margins). Landscape swaps the roles.
PORTRAIT = (16.0, 21.5)
LANDSCAPE = (25.0, 15.4)

HEADER = r"""
\usepackage{fancyhdr}
\usepackage{pdflscape}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{etoolbox}
\usepackage{caption}
\usepackage{xurl}
\usepackage{fvextra}
\DefineVerbatimEnvironment{Highlighting}{Verbatim}{breaklines,commandchars=\\\{\}}
\captionsetup{font=small,labelfont=bf,labelsep=colon,skip=6pt}
\setlength{\emergencystretch}{3em}
\renewcommand{\arraystretch}{1.18}
\newcommand{\tablesize}{\small}
\AtBeginEnvironment{longtable}{\tablesize}
\setlength{\parskip}{0.55em}
\setlength{\parindent}{0pt}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\thepage}
\fancyhead[L]{\small\nouppercase{\leftmark}}
\fancyhead[R]{\small @@RUNHEAD@@}
\renewcommand{\headrulewidth}{0.3pt}
\fancypagestyle{plain}{\fancyhf{}\fancyfoot[C]{\thepage}\renewcommand{\headrulewidth}{0pt}}
\AtBeginDocument{\hypersetup{hidelinks}}
\setcounter{tocdepth}{2}
\usepackage{tocloft}
\setlength{\cftbeforechapskip}{3pt}
\setlength{\cftbeforesecskip}{0pt}
\renewcommand{\cftchapfont}{\bfseries\small}
\renewcommand{\cftsecfont}{\small}
\renewcommand{\cftsecpagefont}{\small}
\setcounter{secnumdepth}{2}
\renewcommand{\arraystretch}{1.2}
"""

LUA = r"""
local function esc(s)
  s = s:gsub('\\', '\\textbackslash{}')
  s = s:gsub('([{}%%&#$])', '\\%1')
  s = s:gsub('_', '\\_')
  s = s:gsub('%^', '\\textasciicircum{}')
  s = s:gsub('~', '\\textasciitilde{}')
  s = s:gsub('([_%./%-%(,:])', '%1\\allowbreak{}')
  s = s:gsub('(%l)(%u)', '%1\\allowbreak{}%2')
  return s
end
function Code(el)
  if FORMAT:match('latex') then
    return pandoc.RawInline('latex', '\\texttt{' .. esc(el.text) .. '}')
  end
end
"""


def fit_image(path: Path, req_w: float | None, req_h_cm: float | None, landscape: bool) -> str:
    """Return a pandoc attribute string that keeps the figure on one page, never stretched."""
    with Image.open(path) as im:
        w, h = im.size
    box_w, box_h = LANDSCAPE if landscape else PORTRAIT
    if "diagrams" not in str(path) and not landscape:
        box_h = 15.5  # screenshots: leave room for text and the caption
    width_cm = box_w * (req_w if req_w else 1.0)
    if req_h_cm:
        width_cm = min(width_cm, req_h_cm * w / h)
    width_cm = min(width_cm, box_h * w / h, box_w)
    return f"{{width={width_cm:.2f}cm}}"


def preprocess(text: str):
    """Returns (latex-ready markdown, expected figure numbers, expected table numbers)."""
    cover = re.search(r"<!-- cover -->\n(.*?)<!-- /cover -->", text, re.S).group(1)
    front = re.search(r"<!-- frontmatter -->\n(.*?)<!-- /frontmatter -->", text, re.S).group(1)
    body = text[text.index("<!-- /frontmatter -->") + len("<!-- /frontmatter -->"):]

    # ---- cover page
    m = re.match(r"# (.*?)\n", cover)
    title = m.group(1)
    cover = cover[m.end():]
    cover = re.sub(r"^\*\*[^*\n]+\*\*\n", "", cover.lstrip("\n"), count=1)
    cover_md = (
        "```{=latex}\n\\begin{titlepage}\n\\thispagestyle{empty}\n\\centering\n\\vspace*{1.5cm}\n"
        "{\\large Object Oriented Programming, Course Project\\par}\n\\vspace{1.2cm}\n"
        f"{{\\Huge\\bfseries {title}\\par}}\n\\vspace{{0.8cm}}\n{{\\Large @@SUBTITLE@@\\par}}\n\\vspace{{1cm}}\n```\n\n"
        + cover.strip() + "\n\n```{=latex}\n\\end{titlepage}\n```\n")

    # ---- front matter: unnumbered chapters in roman numbering
    front = re.sub(r"^## (.*)$", r"# \1 {-}", front, flags=re.M)
    front_md = ("```{=latex}\n\\pagenumbering{roman}\n\\setcounter{page}{1}\n```\n\n" + front.strip() + "\n\n"
                "```{=latex}\n\\tableofcontents\n\\clearpage\n"
                + ("\\listoffigures\n\\clearpage\n\\listoftables\n\\clearpage\n" if os.environ.get("REPORT_LISTS", "1") == "1" else "")
                + "\\pagenumbering{arabic}\n\\setcounter{page}{1}\n```\n")

    # ---- headings: strip the numbers, LaTeX numbers them
    chapter_no, appendix = 0, False
    exp_fig, exp_tab = [], []
    out_lines, lines = [], body.split("\n")
    i, landscape = 0, False
    while i < len(lines):
        ln = lines[i]
        if ln.strip() in ("<!-- landscape -->", "<!-- landscape tiny -->"):
            landscape = True
            size = "\\scriptsize" if "tiny" in ln else "\\footnotesize"
            out_lines += ["```{=latex}", "\\begin{landscape}\\renewcommand{\\tablesize}{" + size + "}", "```"]
            i += 1
            continue
        if ln.strip() == "<!-- /landscape -->":
            landscape = False
            out_lines += ["```{=latex}", "\\renewcommand{\\tablesize}{\\small}\\end{landscape}", "```"]
            i += 1
            continue
        if ln.strip() == "\\newpage":
            out_lines += ["```{=latex}", "\\clearpage", "```"]
            i += 1
            continue
        m = re.match(r"# Chapter (\d+): (.*)", ln)
        if m:
            chapter_no = int(m.group(1))
            out_lines.append(f"# {m.group(2)}")
            i += 1
            continue
        m = re.match(r"# Appendix ([A-Z]): (.*)", ln)
        if m:
            if not appendix:
                appendix = True
                out_lines += ["```{=latex}", "\\appendix", "```"]
            chapter_no = m.group(1)
            out_lines.append(f"# {m.group(2)}")
            i += 1
            continue
        if ln.strip() == "# References":
            out_lines.append("# References {-}")
            chapter_no = "R"
            i += 1
            continue
        m = re.match(r"## (\d+\.\d+) (.*)", ln)
        if m:
            out_lines.append(f"## {m.group(2)}")
            i += 1
            continue
        m = re.match(r"!\[Figure ([A-Z0-9]+\.\d+): (.*?)\]\((.*?)\)(\{.*?\})?\s*$", ln)
        if m:
            exp_fig.append(m.group(1))
            path = DOCS / m.group(3)
            attr = m.group(4) or ""
            req_w = re.search(r"width=(\d+)%", attr)
            req_h = re.search(r"height=([\d.]+)cm", attr)
            fit = fit_image(path, int(req_w.group(1)) / 100 if req_w else None,
                            float(req_h.group(1)) if req_h else None, landscape)
            out_lines.append(f"![{m.group(2)}]({m.group(3)}){fit}")
            i += 1
            continue
        m = re.match(r"\*\*Table ([A-Z0-9]+\.\d+): (.*)\*\*\s*$", ln)
        if m:
            exp_tab.append(m.group(1))
            caption = m.group(2)
            i += 1
            while lines[i].strip() == "":
                i += 1
            tbl = []
            while i < len(lines) and lines[i].startswith("|"):
                tbl.append(lines[i])
                i += 1
            out_lines += tbl + ["", f": {caption}", ""]
            continue
        out_lines.append(ln)
        i += 1
    return cover_md + "\n" + front_md + "\n" + "\n".join(out_lines), exp_fig, exp_tab


def expected_sequence(numbers: list[str]) -> list[str]:
    """What LaTeX will produce: a counter that restarts in every chapter or appendix."""
    seen, result = {}, []
    for n in numbers:
        chap = n.split(".")[0]
        seen[chap] = seen.get(chap, 0) + 1
        result.append(f"{chap}.{seen[chap]}")
    return result


def main() -> int:
    global SRC, OUT, RUNNING_HEAD, COVER_SUBTITLE
    # Optional arguments: source.md output.pdf "running header" "cover subtitle"
    if len(sys.argv) >= 3:
        SRC, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    if len(sys.argv) >= 4:
        RUNNING_HEAD = sys.argv[3]
    if len(sys.argv) >= 5:
        COVER_SUBTITLE = sys.argv[4]
    for tool in ("pandoc", "xelatex"):
        if not shutil.which(tool):
            print(f"{tool} is not installed", file=sys.stderr)
            return 1
    text = SRC.read_text(encoding="utf-8")
    if "\u2014" in text:
        print("The report contains an em dash. Remove it.", file=sys.stderr)
        return 1
    md, figs, tabs = preprocess(text)
    md = md.replace("@@SUBTITLE@@", COVER_SUBTITLE)

    problems = []
    for kind, found in (("Figure", figs), ("Table", tabs)):
        want = expected_sequence(found)
        for written, latex in zip(found, want):
            if written != latex:
                problems.append(f"{kind} written as {written} would be numbered {latex} by LaTeX")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1

    tmp = Path(tempfile.mkdtemp())
    (tmp / "header.tex").write_text(HEADER.replace("@@RUNHEAD@@", RUNNING_HEAD), encoding="utf-8")
    (tmp / "code.lua").write_text(LUA, encoding="utf-8")
    (tmp / "report.md").write_text(md, encoding="utf-8")
    cmd = ["pandoc", str(tmp / "report.md"), "-f", "markdown+pipe_tables+raw_tex+implicit_figures+smart",
           "--pdf-engine=xelatex", "--top-level-division=chapter", "--number-sections",
           "-V", "documentclass=report", "-V", f"classoption={os.environ.get('REPORT_FONT', '11pt')}", "-V", "classoption=a4paper",
           "-V", f"geometry:margin={os.environ.get('REPORT_MARGIN', '2.5cm')}", "-V", f"linestretch={os.environ.get('REPORT_STRETCH', '1.12')}", "-V", "colorlinks=false",
           "-V", "monofontoptions=Scale=0.88",
           "--include-in-header", str(tmp / "header.tex"), "--lua-filter", str(tmp / "code.lua"),
           "--resource-path", str(DOCS), "--highlight-style=tango", "-o", str(OUT)]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=DOCS)
    (tmp / "pandoc.log").write_text(r.stdout + r.stderr)
    if r.returncode != 0:
        print(r.stderr[-3000:], file=sys.stderr)
        return r.returncode
    print(f"Wrote {OUT} ({OUT.stat().st_size // 1024} kB); {len(figs)} figures, {len(tabs)} tables numbered consistently.")
    if r.stderr.strip():
        print(r.stderr[-1500:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
