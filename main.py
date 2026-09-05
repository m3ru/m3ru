from glob import glob
from time import time
import argparse
from hashlib import sha256
from pathlib import Path
from reading import load_build_selection, render_selection
ASSET_ROOT = Path(__file__).resolve().parent
global INCL; INCL = "./inc"
global DEST; DEST = "./site"
global NAME; NAME = "4D47"
global DOMAIN; DOMAIN = "m3ru.org"
global LICENSE; LICENSE = "https://creativecommons.org/licenses/by-nc-sa/4.0/"
global TABLEOFCONTENTS; TABLEOFCONTENTS = "toc"

def lexicon():
    return glob(INCL+"/*.htm")

def init_site_file(lex_f):
    fn = lex_f.split('/')[-1]
    fn = fn.split('.')[0]
    with open(DEST+'/'+fn+'.html', 'w') as f:
        return f, fn

def versioned_asset(path):
    # A new URL for changed content bypasses stale browser and CDN cache entries.
    version = sha256((ASSET_ROOT / path).read_bytes()).hexdigest()[:12]
    return f"../{path}?v={version}"

def write_header(fn):
    stylesheet = versioned_asset("links/main.css")
    theme_script = versioned_asset("links/theme.js")
    with open(DEST+'/'+fn+'.html', 'w') as f:
        f.write("<!DOCTYPE html><html lang='en'><head>")
        f.write(f"<meta charset='utf-8'/><meta name='viewport' content='width=device-width, initial-scale=1'/><meta name='color-scheme' content='light dark'/><script src='{theme_script}'></script><link rel='preload' href='../links/fonts/RLLimoTRIAL-Regular.woff2' as='font' type='font/woff2' crossorigin/><link href='{stylesheet}' type='text/css' rel='stylesheet'/><link href='../media/icon.webp' type='image/webp' rel='shortcut icon'/>")
        f.write(f"<title>{NAME}&mdash;{fn}</title></head>")
        f.write("<body class='page-home'>" if fn == "home" else "<body>")
        f.write("<header></header>")
        # if fn == "home":
        #     f.write("<header><a href='home.html'><img src='../media/main.png' width='160' height='80'></a>&nbsp;&nbsp;&nbsp;&nbsp;</header>")
        # else:
        #     f.write(f"<header><a href='home.html'><img src='../media/main.png' width='160' height='80'></a></header>")
        # can loop over header lines and do specific things based on contents
        #for line in head:
            #f.write(line)
        f.close()
    
def write_nav(fn, cat_dict):
    with open(DEST+'/'+fn+'.html', 'a') as f:
        f.write("<nav aria-label='Site navigation'>\n")
        f.write("<section class='site-nav'>\n")
        # find this filename as a value in the category dict. Return the category.
        match_cat = next((key for key, values in cat_dict.items() if fn in values), None)
        # reorder categories dictionary alphabetically so it is written that way to the nav
        #key_order = sorted(sorted(cat_dict, key=cat_dict.get))
        preferred = ["writing", "meta", "misc"] # hardcoded order; any other categories follow alphabetically
        key_order = [k for k in preferred if k in cat_dict] + sorted(k for k in cat_dict if k not in preferred)
        cat_dict_sorted = {key: cat_dict[key] for key in key_order}
        # make nav bar for each page. note which category the current page belongs AND mark current page in bar
        for cat, pages in cat_dict_sorted.items():
            if cat == 'no-proc': continue
            f.write(f"<section class='nav-{cat}'>\n")
            f.write(f"<h2 class='self'>{cat}&nbsp;</h2>\n") if cat == match_cat else f.write(f"<h2>{cat}&nbsp;</h2>\n")
            f.write("<ul class='nobull capital'>\n")
            for page in sorted(pages): f.write(f"<li><mark><a href='{page}.html' class='self' aria-current='page'>{page}</a></mark></li>\n") \
                if page == fn else f.write(f"<li><a href='{page}.html'>{page}</a></li>\n")
            f.write("</ul>\n")
            f.write("</section>\n")
        f.write("</section>\n")
        f.write("</nav>\n")
        f.write("<!-- Generated file, do not edit -->\n")
    return

def write_toc_body(cat_dict):
    with open(DEST+'/'+TABLEOFCONTENTS+'.html', 'a') as f:
        f.write("<nav></nav>")
        f.write("<main>")
        f.write("<h2>The Garden at a Glance</h2>")
        f.write("<article><p>")
        f.write("<ul class='nobull'>")
        for page in sorted([value for values in cat_dict.values() for value in values]):
            f.write(f"<li><a href='{page}.html'>{page}</a></li>")
        f.write("</ul>")
        f.write("</p></article></main>")
        f.close()

def parse_body(lex_f, fn, cat_dict, proc=True, reading_html=""):
    with open(lex_f) as inc:
        # SLICE out and process header lines
        inc_lines = inc.readlines()
        ind_head = [i for i, x in enumerate(inc_lines) if x == '---\n']
        if len(ind_head) == 2:
            # we have a header
            head = inc_lines[ind_head[0] + 1:ind_head[1]]
            body_lines = inc_lines[ind_head[1] + 1:]
        else:
            # no or erroneous head
            head = []
            body_lines = inc_lines
        inc.close()
    with open(DEST+'/'+fn+'.html', 'a') as f:
        if proc:
            write_header(fn)
            write_nav(fn, cat_dict)
        body = ''.join(body_lines)
        if fn == "home":
            body = body.replace("  <!-- CURRENTLY_READING -->\n",
                                f"  {reading_html}\n" if reading_html else "")
        # Pages pasted straight from a markdown converter have no <main> wrapper;
        # without it the content floats around the nav instead of forming the content column.
        if proc and '<main' not in body:
            body = "<main>\n" + body + "</main>\n"
        f.write(body)

        f.close()

def write_footer(fn, proc=True):
    if not proc:
        return
    with open(DEST+'/'+fn+'.html', 'a') as f:
        f.write("<footer><hr />")
        f.write("<div class='footer-meta'><span><b>Meru Gopalan</b> © 2026</span>")
        f.write("<button class='theme-toggle' type='button' aria-label='Switch to dark mode' title='Switch to dark mode' hidden>")
        f.write("<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'>")
        f.write("<path class='theme-moon' d='M20.5 13.1A8.5 8.5 0 1 1 10.9 3.5a6.5 6.5 0 0 0 9.6 9.6Z'/>")
        f.write("<g class='theme-sun'><circle cx='12' cy='12' r='4'/><path d='M12 2v2m0 16v2M2 12h2m16 0h2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42'/></g>")
        f.write("</svg></button></div>")
        f.write("</footer>")
        f.write("</body>")
        f.write("</html>")

def preparse_header(lex_f, fn, categories):
    with open(lex_f) as inc:
        # SLICE out and process header lines
        inc_lines = inc.readlines()
        ind_head = [i for i, x in enumerate(inc_lines) if x == '---\n']
        if len(ind_head) == 2:
            # we have a header
            head = inc_lines[ind_head[0] + 1:ind_head[1]]
            try:
                cat = [i for i, x in enumerate(head) if x.split(':')[0] == 'category']
                this_cat = head[cat[0]].split(':')[-1].strip()
                categories.setdefault(this_cat, [])
                categories[head[cat[0]].split(':')[-1].strip()].append(fn)
            except IndexError:
                print(f"** {fn} - Incorrect header format.\nSetting category to 'no-proc'.\n")
                categories.setdefault('no-proc', [])
                categories['no-proc'].append(fn)    
        else:
            # no or erroneous head
            head = []
        inc.close()
    return categories

def write_table_of_contents(cat_dict):
    write_header(TABLEOFCONTENTS)
    write_toc_body(cat_dict)
    write_footer(TABLEOFCONTENTS)
    return
    
def finalize(f, fn):
    try:
        f.close()
    except:
        print(f"Error processing file {fn}")

def engine(offline=False):
    # Refresh and validate before opening generated files; offline builds use the snapshot.
    reading_html = render_selection(load_build_selection(offline=offline))
    lex = lexicon()
    i=1
    # preprocess loop to get table of contents (which files belong to which categories)
    categories = {}
    tock = time()
    files_not_to_process = ["./inc/atavata.htm"]
    for lex_f in lex:
        f, fn = init_site_file(lex_f)
        preparse_header(lex_f, fn, categories)
    # make table of contents
    write_table_of_contents(categories)
    # main processing loop
    for lex_f in lex:
        f, fn = init_site_file(lex_f)
        proc = False if lex_f in files_not_to_process else True
            
        parse_body(lex_f, fn, categories, proc, reading_html)
        write_footer(fn, proc)
        finalize(f, fn)
        print(f"{str(i).zfill(2)}/{len(lex)} :: {fn}"); i += 1
    tick = time()
    print(f"Processed {len(lex)} files in {1000*(tick-tock):.5} miliseconds.")
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the site from inc/.")
    parser.add_argument("--offline", action="store_true", help="use saved reading links without contacting Histre")
    engine(offline=parser.parse_args().offline)
