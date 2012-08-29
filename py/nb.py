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
    query = [x for x in query.split(" ") if len(x) > 0]
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
        selection = 0
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(1)
        first = True
        
        while True:
            if not first:
                c = stdscr.getch()
                if c > 0 and c < 256 and chr(c) in string.printable:
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
                elif (c == curses.KEY_BACKSPACE or c == 127) and cursor > 0:
                    query = query[:cursor - 1] + query[cursor:]
                    cursor = cursor - 1
                elif c == curses.KEY_EXIT or c == 27:
                    return
                else:
                    continue
                    
            first = False
            height, width = stdscr.getmaxyx()
            stdscr.clear()
            stdscr.addstr(0, 2, query)
            
            element = 0
            if selection == element:
                stdscr.addstr(0, selection, ">", curses.A_REVERSE)
            
            y = 1
            element += 1
            query_bits = query.split(" ")
            for n in sorted(list(search(query, index))):
                path = os.path.join(nb_notes_dir(), "notes", n)
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        t = f.read().split(" ")
                        t_joined = " ".join(t)
                        if selection == element:
                            x = 2
                            t_index = 0
                            stdscr.addstr(y, 0, " ", curses.A_REVERSE)
                            while t_index < len(t):
                                if x > 2 and x + len(t[t_index]) + 1 >= width:
                                    x = 2
                                    y += 1
                                    stdscr.addstr(y, 0, " ", curses.A_REVERSE)
                                if t[t_index] in query_bits:
                                    stdscr.addstr(y, x, t[t_index], curses.A_BOLD)
                                else:
                                    stdscr.addstr(y, x, t[t_index])
                                x += len(t[t_index]) + 1
                                t_index += 1
                        else:
                            # Show excerpt.
                            x = 2
                            t_index = 0
                            # Find first highlighted word.
                            if len(t_joined) > width:
                                while t_index < len(t):
                                    if t[t_index] in query_bits:
                                        break
                                    t_index += 1
                                if t_index == len(t):
                                    t_index = 0
                                else:
                                    # Shift window leftwards for better ctx.
                                    end = len(t[t_index])
                                    while t_index > 0 and end + 1 + len(t[t_index - 1]) < width * 3 / 4:
                                        end += 1 + len(t[t_index - 1])
                                        t_index -= 1
                            start_index = t_index
                            while t_index < len(t) and x + len(t[t_index]) < width:
                                if t[t_index] in query_bits:
                                    stdscr.addstr(y, x, t[t_index], curses.A_BOLD)
                                else:
                                    stdscr.addstr(y, x, t[t_index])
                                x += len(t[t_index]) + 1
                                t_index += 1
                            if t_index < len(t):
                                stdscr.addstr(y, width - 3, "...")
                            if start_index > 0:
                                stdscr.addstr(y, 2, "...")
                        
                    y += 1
                    element += 1
            
            # Help
            if selection == 0:
                if len(query) == 0:
                    stdscr.addstr(height - 2, 0, "Type to search or make new note. Press esc to exit.", curses.A_REVERSE)
                else:
                    stdscr.addstr(height - 2, 0, "Press enter to make new note or up/down arrow keys to select entries.", curses.A_REVERSE)
            else:
                stdscr.addstr(height - 2, 0, "Use arrow keys to select entries. Press enter to edit or esc to exit.", curses.A_REVERSE)
            
            stdscr.move(0, cursor + 2)
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