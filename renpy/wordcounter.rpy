###############################################################################################################
### WORD COUNTER ##############################################################################################
###############################################################################################################

## Preferences ################################################################################################

# Name of the folder your script files are in, if any (for example: "script/")
define script_folder_path = ""

###############################################################################################################
### The Code ##################################################################################################
###############################################################################################################

init python:

    import collections
    import json

    class Count(object):
        def __init__(self):
            self.blocks = 0
            self.words = 0
            self.characters = 0

        def add(self, s):
            self.blocks += 1
            self.words += len(s.split())
            self.characters += len(s)

    # The main function
    def wordcounter():

        all_stmts = list(renpy.game.script.all_stmts)
        all_stmts.sort(key=lambda n : n.filename)

        filestats = collections.defaultdict(Count)

        menu_count = 0
        options_count = 0

        for node in all_stmts:
            if isinstance(node, renpy.ast.Say):
                filestats[node.filename].add(node.what)

            elif isinstance(node, renpy.ast.Menu):
                menu_count += 1
                for l, c, b in node.items:
                    options_count += 1

        report_stats(filestats, menu_count, options_count)

    def report_stats(filestats, menu_count, options_count):

        count_to_char = collections.defaultdict(list)
        blocks = 0
        words = 0

        for file in filestats:
            blocks += filestats[file].blocks
            words += filestats[file].words

        report = {
            "blocks": blocks,
            "menus": menu_count,
            "options": options_count,
            "words": words
        }

        f = open("stats.json", "w", encoding="utf-8")
        f.write(unicode(json.dumps(report, indent=4, sort_keys=True, ensure_ascii=False))
        f.close()

    wordcounter()
    renpy.quit()
