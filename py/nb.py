#!/usr/bin/env python

import os, sys, datetime, hashlib, cPickle, string, copy

class Index:
    def __init__(self):
        self.file_to_mod_timestamp = {}
        self.word_to_mentions = {}

non_word_letters = string.whitespace + "".join([l for l in string.punctuation if not l == '#' and not l == '-'])

def lex(text):
    t_start = 0
    t_end = 0
    while t_end < len(text):
        if text[t_end] in non_word_letters:
            if t_start != t_end:
                yield (text[t_start:t_end].lower(), t_start)
            t_start = t_end + 1
        t_end += 1
    if t_start != t_end:
        yield (text[t_start:t_end].lower(), t_start)

def nb_notes_dir():
    notes_dir = os.getenv("NB_NOTES_DIR")
    if notes_dir:
        return notes_dir
    if sys.platform == "darwin":
        return os.path.expanduser("~/Documents/nbnotes/")
    if os.name == "posix":
        notes_dir = os.getenv("XDG_DATA_HOME")
        if notes_dir:
            return os.path.join(notes_dir, "nbnotes")
        return os.path.expanduser("~/.nbnotes/")
    raise "You are running some unholy operating system. Please desist."

def mk_note(text, index):
    name = datetime.datetime.now().isoformat().replace(":", "-") + "H" + hashlib.sha1(text).hexdigest() + ".txt"
    nd = os.path.join(nb_notes_dir(), "notes")
    if not os.path.exists(nd):
        os.makedirs(nd)
    p = os.path.join(nd, name)
    with open(p, 'w') as f:
        f.write(text)
    add_to_index(text, name, os.path.getmtime(p), index)
    save_index(index)
    
def editor_cmd():
    ed = os.getenv("NB_NOTES_EDITOR")
    if ed:
        return ed
    ed = os.getenv("EDITOR")
    if ed:
        return ed
    return "vi"

def view_cmd():
    v = os.getenv("NB_NOTES_VIEWER")
    if v:
        return v
    return "less -e"

def edit_note(n, index):
    path = os.path.join(nb_notes_dir(), "notes", n)
    if os.path.exists(path):
        remove_from_index(n, index)
        os.system(editor_cmd() + " " + path)
        with open(path, 'r') as f:
            add_to_index(f.read(), n, os.path.getmtime(path), index)
            save_index(index)
            
def view_note(n):
    path = os.path.join(nb_notes_dir(), "notes", n)
    if os.path.exists(path):
        os.system(view_cmd() + " " + path)

def delete_note(n, index):
    remove_from_index(n, index)
    path = os.path.join(nb_notes_dir(), "notes", n)
    if os.path.exists(path):
        os.remove(path)

def search(query, index):
    query = [x.lower() for x in query.split(" ") if len(x) > 0]
    if len(query) == 0:
        return latest_n_entries(index, 30)
    if not query[0] in index.word_to_mentions:
        return set()
    return refine_search(query[1:], index, set([t[1] for t in index.word_to_mentions[query[0]]]))

def latest_n_entries(index, n):
    return sorted(list(set(sum([[t[1] for t in w] for w in index.word_to_mentions.values()], []))))[::-1][:n]

def refine_search(query, index, result):
    if len(query) == 0:
        return result
    if not query[0] in index.word_to_mentions:
        return set()
    return refine_search(query[1:], index, result.intersection([t[1] for t in index.word_to_mentions[query[0]]]))

def load_results(results):
    results = sorted(list(results))[::-1]
    r2 = []
    for n in results:
        path = os.path.join(nb_notes_dir(), "notes", n)
        if os.path.exists(path):
            with open(path, 'r') as f:
                r2.append((n, f.read()))
    return r2
    
def add_to_index(text, f_name, m_time, index):
    index.file_to_mod_timestamp[f_name] = m_time
    for word, offset in lex(text):
        if not word in index.word_to_mentions:
            index.word_to_mentions[word] = []
        index.word_to_mentions[word].append((offset, f_name))

def remove_from_index(f_name, index):
    for word in index.word_to_mentions.keys():
        index.word_to_mentions[word] = [t for t in index.word_to_mentions[word] if not t[1] == f_name]
        if len(index.word_to_mentions[word]) == 0:
            del index.word_to_mentions[word]
    del index.file_to_mod_timestamp[f_name]

def load_index():
    index_f = os.path.join(nb_notes_dir(), "index.txt")
    index = Index()
    if not os.path.exists(index_f):
        return index
    else:
        with open(index_f, 'rb') as f:
            index = Index()
            l = f.readline()
            if l != "nb py 1\n":
                raise "Unknown index format: " + l
            # Read list of files and mod timestamps
            n_list = []
            l = f.readline()
            while l != '\n':
                n = l[:-1]
                m = float(f.readline()[:-1])
                n_list.append(n)
                index.file_to_mod_timestamp[n] = m
                l = f.readline()
            # Read index
            l = f.readline()
            while l != '':
                word = l[:-1]
                mentions = []
                index.word_to_mentions[word] = mentions
                l = f.readline()
                while l != '\n':
                    n = n_list[int(l[:-1])]
                    offset = int(f.readline()[:-1])
                    mentions.append((offset, n))
                    l = f.readline()
                l = f.readline()
            return index

def save_index(index):
    nd = nb_notes_dir()
    if not os.path.exists(nd):
        os.makedirs(nd)
    index_f = os.path.join(nd, "index.txt")
    with open(index_f, 'w') as f:
        # Header
        f.write('nb py 1\n')
        # Files and mod timestamps
        n_m_list = list(index.file_to_mod_timestamp.iteritems())
        n_list = [x[0] for x in n_m_list]
        for n, m in n_m_list:
            f.write(n)
            f.write('\n')
            f.write(str(m))
            f.write('\n')
        f.write('\n') # Separator
        for word, mention_list in index.word_to_mentions.iteritems():
            f.write(word)
            f.write('\n')
            for mention in mention_list:
                f.write(str(n_list.index(mention[1])))
                f.write('\n')
                f.write(str(mention[0]))
                f.write('\n')
            f.write('\n')

def re_index():
    index = Index()
    nd = os.path.join(nb_notes_dir(), "notes")
    if not os.path.exists(nd):
        os.makedirs(nd)
    for f_name in os.listdir(nd):
        if f_name[0] == ".":
            continue
        p = os.path.join(nd, f_name)
        with open(p, 'r') as f:
            add_to_index(f.read(), f_name, os.path.getmtime(p), index)
    return index

def clone_index(index):
    return copy.deepcopy(index)

def re_index_if_modified(index):
    nd = os.path.join(nb_notes_dir(), "notes")
    if not os.path.exists(nd):
        os.makedirs(nd)
    for f_name in os.listdir(nd):
        if f_name[0] == ".":
            continue
        p = os.path.join(nd, f_name)
        if not f_name in index.file_to_mod_timestamp:
            with open(p, 'r') as f:
                add_to_index(f.read(), f_name, os.path.getmtime(p), index)
        else:
            if index.file_to_mod_timestamp[f_name] < os.path.getmtime(p):
                remove_from_index(f_name, index)
                with open(p, 'r') as f:
                    add_to_index(f.read(), f_name, os.path.getmtime(p), index)
    for f_name in index.file_to_mod_timestamp.keys():
        p = os.path.join(nd, f_name)
        if not os.path.exists(p):
            remove_from_index(f_name, index)
    return index
    
def entry_height(t, display_width):
    x = 0
    y = 0
    t_index = 0
    while t_index < len(t):
        if t[t_index] == "\n":
            x = 0
            y += 1
            t_index += 1
            continue
        x += 1
        if x >= display_width:
            x = 0
            y += 1
        t_index += 1
    return y + 1

def ui(query=""):
    import curses
    stdscr = curses.initscr()
    try:
        results = []
        index = load_index()
        re_index_if_modified(index) # qqDPS
        cursor = len(query)
        selection = 0
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(1)
        first = True
        edit_mode = False
        autocompletes = []
        ac_tok = None
        speculative_ac = False
        cursor_tok = None
        
        while True:
            if not first:
                c = stdscr.getch()
                if edit_mode:
                    if c == curses.KEY_ENTER or c == 10 or c == 13 or c == ord('e'):
                        curses.nocbreak()
                        stdscr.keypad(0)
                        curses.echo()
                        curses.endwin()
                        edit_note(results[selection - 1][0], index)
                        stdscr = curses.initscr()
                        curses.noecho()
                        curses.cbreak()
                        stdscr.keypad(1)
                    elif c == ord('d'):
                        delete_note(results[selection - 1][0], index)
                    elif c == ord('v'):
                        curses.nocbreak()
                        stdscr.keypad(0)
                        curses.echo()
                        curses.endwin()
                        view_note(results[selection - 1][0])
                        stdscr = curses.initscr()
                        curses.noecho()
                        curses.cbreak()
                        stdscr.keypad(1)
                    edit_mode = False
                else:
                    if c == curses.KEY_ENTER or c == 10 or c == 13:
                        if selection == 0:
                            if len(query) > 0:
                                mk_note(query, index)
                                return
                        else:
                            if selection - 1 < len(results):
                                edit_mode = True
                    elif c == 9:
                        # tab to autocomplete
                        if speculative_ac and len(autocompletes) > 0:
                            query = query[:cursor] + autocompletes[0][len(ac_tok):] + query[cursor:]
                        elif cursor_tok:
                            new_word = autocompletes[(autocompletes.index(cursor_tok[0]) + 1) % len(autocompletes)]
                            query = query[:cursor_tok[1]] + new_word + query[cursor_tok[1] + len(cursor_tok[0]):]
                    elif c > 0 and c < 256 and chr(c) in string.printable:
                        query = query[:cursor] + chr(c) + query[cursor:]
                        cursor += 1
                    elif c == curses.KEY_LEFT:
                        cursor = max(0, cursor - 1)
                    elif c == curses.KEY_RIGHT:
                        cursor = min(len(query), cursor + 1)
                    elif c == curses.KEY_UP:
                        selection = max(0, selection - 1)
                    elif c == curses.KEY_DOWN:
                        selection += 1
                    elif (c == curses.KEY_BACKSPACE or c == 127 or c == 8) and cursor > 0:
                        query = query[:cursor - 1] + query[cursor:]
                        cursor = cursor - 1
                    elif c == curses.KEY_EXIT or c == 27:
                        return
                    else:
                        continue
            
            lexed_query = lex(query)
            autocompletes = []
            ac_tok = None
            speculative_ac = False
            cursor_tok = None
            for tok in lexed_query:
                if cursor > tok[1] and cursor <= tok[1] + len(tok[0]):
                    if cursor == tok[1] + len(tok[0]):
                        speculative_ac = True
                    ac_tok = tok[0][:cursor - tok[1]]
                    cursor_tok = tok
            if ac_tok:
                autocompletes = [w for w in index.word_to_mentions.keys() if len(w) > len(ac_tok) and w[:len(ac_tok)] == ac_tok]
                if not cursor_tok[0] in autocompletes:
                    autocompletes.append(cursor_tok[0])
            
            first = False
            stdscr.clear()
            height, width = stdscr.getmaxyx()
            
            if len(autocompletes) > 0 and speculative_ac:
                stdscr.addstr(0, 2, query[:cursor], curses.A_BOLD)
                y, x = stdscr.getyx()
                stdscr.addstr(y, x, autocompletes[0][len(ac_tok):])
                y, x = stdscr.getyx()
                stdscr.addstr(y, x, query[cursor:], curses.A_BOLD)
            else:
                stdscr.addstr(0, 2, query, curses.A_BOLD)
            
            y = stdscr.getyx()[0] + 1
            
            element = 0
            if selection == element:
                stdscr.addstr(0, selection, ">", curses.A_REVERSE)
            
            element += 1
            query_bits = query.split(" ")
            results = load_results(search(query, index))
            selection = min(len(results), selection)
            full_h = entry_height(results[selection - 1][1], width) if selection > 0 else 1
            results_h = full_h + len(results) - 1
            results_offset = 0;
            if results_h >= height - 4:
                results_offset = max(0, min(selection - 2, results_h - height + 4))
            if results_offset > 0:
                stdscr.addstr(y, 0, "^" * width)
                stdscr.addstr(y, 2, " " + str(results_offset) + " ")
                y += 1
            
            r_index = -1
            for r in results:
                r_index += 1
                if r_index < results_offset:
                    element += 1
                    continue
                if y == height - 3 and r != results[-1]:
                    stdscr.addstr(y, 0, "v" * width)
                    stdscr.addstr(y, 2, " " + str(len(results) - r_index) + " ")
                    break
                start_y = y
                name, t = r
                highlighted = [e for e in lex(t) if e[0] in query_bits]
                t_index = 0
                if selection != element and len(highlighted) > 0 and len(t) > width - 2:
                    t_index = max(0, min(len(t) - (width - 2), highlighted[0][1] - width / 4))
                x = 0
                t_index_start = t_index
                in_highlight = None
                while t_index < len(t):
                    if t[t_index] == "\n" and selection == element:
                        x = 0
                        y += 1
                        t_index += 1
                        continue
                    if y >= height - 3 and r != results[-1]:
                        y = height - 4
                        break
                    if y >= height - 2:
                        y = height - 3
                        break
                    for h in highlighted:
                        if t_index == h[1]:
                            in_highlight = h
                    if in_highlight and t_index >= in_highlight[1] + len(in_highlight[0]):
                        in_highlight = None
                    if in_highlight:
                        stdscr.addch(y, x + 2, ord(t[t_index]), curses.A_BOLD)
                    else:
                        try:
                            stdscr.addch(y, x + 2, ord(t[t_index]))
                        except:
                            stdscr.addstr(0, 0, "y=" + str(y) + " x=" + str(x) + " h=\"" + str(height) + "\"")
                    x += 1
                    if x >= width - 2:
                        if selection == element:
                            x = 0
                            y += 1
                        else:
                            break
                    t_index += 1
                    
                # Highlight selection
                if selection == element:
                    for yy in range(start_y, y + 1):
                        stdscr.addstr(yy, 0, " ", curses.A_REVERSE)
                y += 1
                element += 1
            
            # Help
            if selection == 0:
                if len(query) == 0:
                    stdscr.addstr(height - 2, 0, "Type to search or make new note. Press esc to exit.", curses.A_REVERSE)
                else:
                    stdscr.addstr(height - 2, 0, "Press enter to make new note or up/down arrow keys to select entries.", curses.A_REVERSE)
            else:
                if edit_mode:
                    stdscr.addstr(height - 2, 0, "Press e or enter to edit, v to view, d to delete, and any other key to continue.", curses.A_REVERSE)
                else:
                    stdscr.addstr(height - 2, 0, "Use arrow keys to select entries. Press enter to edit or esc to exit.", curses.A_REVERSE)
            
            stdscr.move(cursor / (width - 2), (cursor + 2) % width)
            stdscr.refresh()
    finally:
        curses.nocbreak()
        stdscr.keypad(0)
        curses.echo()
        curses.endwin()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--reindex":
            save_index(re_index())
        elif sys.argv[1] == "-s" or sys.argv[1] == "--search":
            ui(" ".join(sys.argv[2:]))
        elif sys.argv[1] == "-h" or sys.argv[1] == "--help":
            print (
"""nb is a very simple note-taking program.
'nb <some text>' to make a note.
'nb' to list, search, and edit notes.
'nb -s|--search <query>' to start out with a query.
'nb --reindex' to re-index notes after they've been changed externally.""")
        else:
            mk_note(" ".join(sys.argv[1:]), load_index())
    else:
        ui()