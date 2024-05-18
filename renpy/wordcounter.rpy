###############################################################################################################
### WORD COUNTER ##############################################################################################
###############################################################################################################

## Preferences ################################################################################################

# Name of the folder your script files are in, if any (for example: "script/")
define script_folder_path = ""

###############################################################################################################
### The Code ##################################################################################################
###############################################################################################################

init -10000 python:

    import collections
    import io
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
        language = None

        all_stmts = list(renpy.game.script.all_stmts)
        all_stmts.sort(key=lambda n : n.filename)

        filestats = collections.defaultdict(Count)

        menu_count = 0
        options_count = 0

        for node in all_stmts:
            if isinstance(node, renpy.ast.Say):
                if hasattr(renpy.ast, 'TranslateSay') and isinstance(node, renpy.ast.TranslateSay):
                    language = node.language

                if language is None:
                    filestats[node.filename].add(node.what)

            elif isinstance(node, renpy.ast.Menu):
                if language is None:
                    menu_count += 1
                    for l, c, b in node.items:
                        options_count += 1

            elif isinstance(node, renpy.ast.Translate):
                language = node.language

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

        with io.open("stats.json", "w", encoding="utf-8") as outfile:
            outfile.write(unicode(json.dumps(report, indent=4, sort_keys=True, ensure_ascii=False)))

    wordcounter()
    renpy.quit()
