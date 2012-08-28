import os, sys, datetime, hashlib, cPickle

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
    with open(os.path.join(nd, name), 'w') as f:
        f.write(text)
    add_to_index(text, name, index)
    save_index(index)

def edit_note(name, index):
    pass

def search(query, index):
    query = query.split(" ")
    if len(query) == 0 or not query[0] in index:
        return set()
    return refine_search(query[1:], index, set([t[1] for t in index[query[0]]]))

def refine_search(query, index, result):
    if len(query) == 0:
        return result
    if not query[0] in index:
        return set()
    return refine_search(query[1:], index, result.intersection([t[1] for t in index[query[0]]]))
    
def add_to_index(text, f_name, index):
    offset = 0
    for word in text.split(" "):
        if not word in index:
            index[word] = []
        index[word].append((offset, f_name))
        offset += len(word) + 1

def remove_from_index(f_name, index):
    for word in index.keys():
        index[word] = [t for t in index[word] if not t[1] == f_name]

def load_index():
    index_f = os.path.join(nb_notes_dir(), "index_py.pickle")
    if not os.path.exists(index_f):
        return {}
    else:
        with open(index_f, 'rb') as f:
            return cPickle.load(f)

def save_index(index):
    nd = nb_notes_dir()
    if not os.path.exists(nd):
        os.makedirs(nd)
    index_f = os.path.join(nd, "index_py.pickle")
    with open(index_f, 'wb') as f:
        cPickle.dump(index, f)

def ui():
    import curses, string
    stdscr = curses.initscr()
    try:
        index = load_index()
        query = ""
        cursor = 0
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(1)
        
        while True:
            old_q = query
            x = stdscr.getch()
            if x > 0 and x < 256 and chr(x) in string.printable:
                query = query[:cursor] + chr(x) + query[cursor:]
                cursor += 1
            elif x == curses.KEY_LEFT:
                cursor = max(0, cursor - 1)
            elif x == curses.KEY_RIGHT:
                cursor = min(len(query), cursor + 1)
            elif (x == curses.KEY_BACKSPACE or x == 127) and cursor > 0:
                query = query[:cursor - 1] + query[cursor:]
                cursor = cursor - 1
            elif x == curses.KEY_EXIT or x == 27:
                return
            else:
                continue
            stdscr.clear()
            stdscr.addstr(0, 0, query)
            
            offset = 1
            for n in sorted(list(search(query, index))):
                path = os.path.join(nb_notes_dir(), "notes", n)
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        stdscr.addstr(offset, 0, f.read())
                    offset += 1
            
            stdscr.move(0, cursor)
            stdscr.refresh()
    finally:
        curses.nocbreak()
        stdscr.keypad(0)
        curses.echo()
        curses.endwin()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:]).encode('utf-8')
        mk_note(text, load_index())
    else:
        ui()