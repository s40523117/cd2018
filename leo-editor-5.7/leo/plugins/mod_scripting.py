#@+leo-ver=5-thin
#@+node:ekr.20060328125248: * @file mod_scripting.py
#@+<< docstring >>
#@+node:ekr.20060328125248.1: ** << docstring >>
r""" Creates script buttons and @button, @command, @plugin and @script
nodes.

This plugin puts buttons in the icon area. Depending on settings the plugin will
create the 'Run Script', the 'Script Button' and the 'Debug Script' buttons.

The 'Run Script' button is simply another way of doing the Execute Script
command: it executes the selected text of the presently selected node, or the
entire text if no text is selected.

The 'Script Button' button creates *another* button in the icon area every time
you push it. The name of the button is the headline of the presently selected
node. Hitting this *newly created* button executes the button's script.

For example, to run a script on any part of an outline do the following:

1.  Select the node containing the script.
2.  Press the scriptButton button.  This will create a new button.
3.  Select the node on which you want to run the script.
4.  Push the *new* button.

That's all.

For every @button node, this plugin creates two new minibuffer commands: x and
delete-x-button, where x is the 'cleaned' name of the button. The 'x' command is
equivalent to pushing the script button.

You can specify **global buttons** in leoSettings.leo or myLeoSettings.leo by
putting \@button nodes as children of an @buttons node in an \@settings trees.
Such buttons are included in all open .leo (in a slightly different color).
Actually, you can specify global buttons in any .leo file, but \@buttons nodes
affect all later opened .leo files so usually you would define global buttons in
leoSettings.leo or myLeoSettings.leo.

The cleaned name of an @button node is the headline text of the button with:

- Leading @button or @command removed,
- @key and all following text removed,
- @args and all following text removed,
- @color and all following text removed,
- all non-alphanumeric characters converted to a single '-' characters.

Thus, cleaning headline text converts it to a valid minibuffer command name.

You can delete a script button by right-clicking on it, or by
executing the delete-x-button command.

The 'Debug Script' button runs a script using an external debugger.

This plugin optionally scans for @button nodes, @command, @plugin nodes and
@script nodes whenever a .leo file is opened.

- @button nodes create script buttons.
- @command nodes create minibuffer commands.
- @plugin nodes cause plugins to be loaded.
- @script nodes cause a script to be executed when opening a .leo file.

Such nodes may be security risks. This plugin scans for such nodes only if the
corresponding atButtonNodes, atPluginNodes, and atScriptNodes constants are set
to True in this plugin.

You can specify the following options in leoSettings.leo.  See the node:
@settings-->Plugins-->scripting plugin.  Recommended defaults are shown::

    @bool scripting-at-button-nodes = True
    True: adds a button for every @button node.

    @bool scripting-at-rclick-nodes = False
    True: define a minibuffer command for every @rclick node.

    @bool scripting-at-commands-nodes = True
    True: define a minibuffer command for every @command node.

    @bool scripting-at-plugin-nodes = False
    True: dynamically loads plugins in @plugins nodes when a window is created.

    @bool scripting-at-script-nodes = False
    True: dynamically executes script in @script nodes when a window is created.
    This is dangerous!

    @bool scripting-create-debug-button = False
    True: create Debug Script button.

    @bool scripting-create-run-script-button = False
    True: create Run Script button.
    Note: The plugin creates the press-run-script-button regardless of this setting.

    @bool scripting-create-script-button-button = True
    True: create Script Button button in icon area.
    Note: The plugin creates the press-script-button-button regardless of this setting.

    @int scripting-max-button-size = 18
    The maximum length of button names: longer names are truncated.

You can bind key shortcuts to @button and @command nodes as follows:

@button name @key=shortcut

    Binds the shortcut to the script in the script button. The button's name is
    'name', but you can see the full headline in the status line when you move the
    mouse over the button.

@command name @key=shortcut

    Creates a new minibuffer command and binds shortcut to it. As with @buffer
    nodes, the name of the command is the cleaned name of the headline.

This plugin is based on ideas from e's dynabutton plugin, quite possibly the
most brilliant idea in Leo's history.

You can run the script with sys.argv initialized to string values using @args.
For example:

@button test-args @args = a,b,c

will set sys.argv to [u'a',u'b',u'c']

You can set the background color of buttons created by @button nodes by using @color:

@button name @color=color

For example:

@button my button @key=Ctrl+Alt+1 @color=white @args=a,b,c

This creates a button named 'my-button', with a color of white, a keyboard shortcut
of Ctrl+Alt+1, and sets sys.argv to [u,'a',u'b',u'c'] within the context of the script.

"""
#@-<< docstring >>
#@+<< imports >>
#@+node:ekr.20060328125248.2: ** << imports >>
import leo.core.leoGlobals as g
import leo.core.leoColor as leoColor
import leo.core.leoGui as leoGui
# import os
import string
import sys
from collections import namedtuple
#@-<< imports >>
__version__ = '2.5'
#@+<< version history >>
#@+node:ekr.20060328125248.3: ** << version history >>
#@@nocolor
#@+at
# 
# 2.1 EKR: Support common @button nodes in @settings trees.
# 2.2 EKR: Bug fix: use g.match_word rather than s.startswith to discover names.
# This prevents an 's' button from being created from @buttons nodes.
# 2.3 bobjack:
#     - added 'event' parameter to deleteButtonCallback to support rClick menus
#     - exposed the scripting contoller class as
#          g.app.gui.ScriptingControllerClass
# 2.4 bobjack:
#     - exposed the scripting controller instance as
#         c.theScriptingController
# 2.5 EKR: call c.outerUpdate in callbacks.
#@-<< version history >>
# Fix bug: create new command if button command conflicts with existing command.
# This would fix an unbounded recursion.
#@+others
#@+node:ekr.20060328125248.4: ** init
def init():
    '''Return True if the plugin has loaded successfully.'''
    if g.app.gui is None:
        g.app.createQtGui(__file__)
    # This plugin is now gui-independent.
    ok = g.app.gui and g.app.gui.guiName() in ('qt', 'qttabs', 'nullGui')
    if ok:
        sc = 'ScriptingControllerClass'
        if (not hasattr(g.app.gui, sc) or
            getattr(g.app.gui, sc) is leoGui.NullScriptingControllerClass
        ):
            setattr(g.app.gui, sc, ScriptingController)
        # Note: call onCreate _after_ reading the .leo file.
        # That is, the 'after-create-leo-frame' hook is too early!
        g.registerHandler(('new', 'open2'), onCreate)
        g.plugin_signon(__name__)
    return ok
#@+node:ekr.20060328125248.5: ** onCreate
def onCreate(tag, keys):
    """Handle the onCreate event in the mod_scripting plugin."""
    c = keys.get('c')
    if c:
        # g.trace('mod_scripting',c)
        sc = g.app.gui.ScriptingControllerClass(c)
        c.theScriptingController = sc
        sc.createAllButtons()
#@+node:tbrown.20140819100840.37720: ** type RClick
# representation of an rclick node
# this used to have more elements, but evolved to be simpler
RClick = namedtuple('RClick', 'position,children')
#@+node:tbrown.20140819100840.37719: ** build_rclick_tree (mod_scripting.py)
def build_rclick_tree(command_p, rclicks=None, top_level=False):
    """
    Return a list of top level RClicks for the button at command_p, which can be
    used later to add the rclick menus.

    After building a list of @rclick children and following siblings of the
    @button this method applies itself recursively to each member of that list
    to handle submenus.

    :Parameters:
    - `command_p`: node containing @button. May be None
    - `rclicks`: list of RClicks to add to, created if needed
    - `top_level`: is this the top level?
    """
    # Called from QtIconBarClass.setCommandForButton.
    # g.trace('=====', command_p and command_p.h or 'no command_p')
    if rclicks is None:
        rclicks = list()
    if top_level:
        # command_p will be None for leoSettings.leo and myLeoSettings.leo.
        if command_p:
            if '@others' not in command_p.b:
                rclicks.extend([
                    RClick(position=i.copy(), children=[])
                    # -2 for top level entries, i.e. before "Remove button"
                    for i in command_p.children()
                        if i.h.startswith('@rclick ')
                ])
            for i in command_p.following_siblings():
                if i.h.startswith('@rclick '):
                    rclicks.append(RClick(position=i.copy(), children=[]))
                else:
                    break
        for rc in rclicks:
            build_rclick_tree(rc.position, rc.children, top_level=False)
    else: # recursive mode below top level
        if not command_p:
            return []
        if command_p.b.strip():
            return [] # sub menus can't have body text
        for child in command_p.children():
            # pylint: disable=no-member
            rc = RClick(position=child.copy(), children=[])
            rclicks.append(rc)
            build_rclick_tree(rc.position, rc.children, top_level=False)
    return rclicks
#@+node:ekr.20141031053508.7: ** class AtButtonCallback
class AtButtonCallback(object):
    '''A class whose __call__ method is a callback for @button nodes.'''
    #@+others
    #@+node:ekr.20141031053508.9: *3* __init__ (AtButtonCallback)
    def __init__(self, controller, b, c, buttonText, docstring, gnx, script):
        '''AtButtonCallback.__init__.'''
        self.b = b
            # A QButton.
        self.buttonText = buttonText
            # The text of the button.
        self.c = c
            # A Commander.
        self.controller = controller
            # A ScriptingController instance.
        self.gnx = gnx
            # Set if the script is defined in the local .leo file.
        self.script = script
            # Set if the script is found defined in myLeoSettings.leo or leoSettings.leo
        self.source_c = c
            # For GetArgs.command_source.
        self.__doc__ = docstring
            # The docstring for this callback for g.getDocStringForFunction.
    #@+node:ekr.20141031053508.10: *3* __call__ (AtButtonCallback)
    def __call__(self, event=None):
        '''AtButtonCallbgack.__call__. The callback for @button nodes.'''
        self.execute_script()
    #@+node:ekr.20141031053508.13: *3* __repr__ (AtButtonCallback)
    def __repr__(self):
        '''AtButtonCallback.__repr__.'''
        c = self.c
        return 'AtButtonCallback %s gnx: %s len(script) %s' % (
            c.shortFileName(), self.gnx, len(self.script or ''))
    #@+node:ekr.20150512041758.1: *3* __getattr__ (AtButtonCallback)
    def __getattr__(self, attr):
        '''AtButtonCallback.__getattr__. Implement __name__.'''
        if attr == '__name__':
            return 'AtButtonCallback: %s' % self.gnx
        else:
            return None
    #@+node:ekr.20170203043042.1: *3* AtButtonCallback.execute_script
    def execute_script(self):
        '''Execute the script associated with this button.'''
        trace = False and not g.unitTesting
        c, gnx, script = self.c, self.gnx, self.script
        if trace:
            g.trace('%s len(script): %s' % (
                self.c.shortFileName(),
                len(self.script or ''),
            ))
        if not script:
            # Find the node in c with the given gnx.
            for p in c.all_positions():
                if p.gnx == gnx:
                    script = self.controller.getScript(p)
                    break
            else:
                g.trace('can not find gnx: %s in %s' % (gnx, c.shortFileName()))
        if script:
            self.controller.executeScriptFromButton(
                b=self.b,
                buttonText=self.buttonText,
                p=None,
                script_gnx=gnx,
                script=script,
            )
    #@-others
#@+node:ekr.20060328125248.6: ** class ScriptingController
class ScriptingController(object):
    '''A class defining scripting commands.'''
    #@+others
    #@+node:ekr.20060328125248.7: *3*  sc.ctor
    def __init__(self, c, iconBar=None):
        self.c = c
        self.gui = c.frame.gui
        getBool = c.config.getBool
        self.scanned = False
        kind = c.config.getString('debugger_kind') or 'idle'
        self.buttonsDict = {} # Keys are buttons, values are button names (strings).
        self.debuggerKind = kind.lower()
        self.atButtonNodes = getBool('scripting-at-button-nodes')
            # True: adds a button for every @button node.
        self.atCommandsNodes = getBool('scripting-at-commands-nodes')
            # True: define a minibuffer command for every @command node.
        self.atRclickNodes = getBool('scripting-at-rclick-nodes')
            # True: define a minibuffer command for every @rclick node.
        self.atPluginNodes = getBool('scripting-at-plugin-nodes')
            # True: dynamically loads plugins in @plugins nodes when a window is created.
        self.atScriptNodes = getBool('scripting-at-script-nodes')
            # True: dynamically executes script in @script nodes when a window is created.
            # DANGEROUS!
        # Do not allow this setting to be changed in local (non-settings) .leo files.
        if self.atScriptNodes and c.config.isLocalSetting('scripting-at-script-nodes', 'bool'):
            g.es('Security warning! Ignoring...', color='red')
            g.es('@bool scripting-at-script-nodes = True', color='red')
            g.es('This setting can be True only in')
            g.es('leoSettings.leo or myLeoSettings.leo')
            # Restore the value in myLeoSettings.leo
            val = g.app.config.valueInMyLeoSettings('scripting-at-script-nodes')
            if val is None: val = False
            g.es('Restoring value to', val, color='red')
            self.atScriptNodes = val
        self.createDebugButton = getBool('scripting-create-debug-button')
            # True: create Debug Script button.
        self.createRunScriptButton = getBool('scripting-create-run-script-button')
            # True: create Run Script button.
        self.createScriptButtonButton = getBool('scripting-create-script-button-button')
            # True: create Script Button button.
        self.maxButtonSize = c.config.getInt('scripting-max-button-size') or 18
            # Maximum length of button names.
        if not iconBar:
            self.iconBar = c.frame.getIconBarObject()
        else:
            self.iconBar = iconBar
        self.seen = set()
            # Fix bug 74: problems with @button if defined in myLeoSettings.leo
            # Set of gnx's (not vnodes!) that created buttons or commands.
    #@+node:ekr.20150401113822.1: *3* sc.Callbacks
    #@+node:ekr.20060328125248.23: *4* sc.addScriptButtonCommand
    def addScriptButtonCommand(self, event=None):
        '''Called when the user presses the 'script-button' button or executes the script-button command.'''
        c = self.c; p = c.p; h = p.h
        buttonText = self.getButtonText(h)
        shortcut = self.getShortcut(h)
        statusLine = "Run Script: %s" % buttonText
        if shortcut:
            statusLine = statusLine + " @key=" + shortcut
        self.createLocalAtButtonHelper(p, h, statusLine, kind='script-button', verbose=True)
        c.bodyWantsFocus()
    #@+node:ekr.20060522105937.1: *4* sc.runDebugScriptCommand
    def runDebugScriptCommand(self, event=None):
        '''Called when user presses the 'debug-script' button or executes the debug-script command.'''
        c = self.c; p = c.p
        script = g.getScript(c, p, useSelectedText=True, useSentinels=False)
        if script:
            #@+<< set debugging if debugger is active >>
            #@+node:ekr.20060523084441: *5* << set debugging if debugger is active >>
            g.trace(self.debuggerKind)
            if self.debuggerKind == 'winpdb':
                try:
                    import rpdb2
                    debugging = rpdb2.g_debugger is not None
                except ImportError:
                    debugging = False
            elif self.debuggerKind == 'idle':
                # import idlelib.Debugger.py as Debugger
                # debugging = Debugger.interacting
                debugging = True
            else:
                debugging = False
            #@-<< set debugging if debugger is active >>
            if debugging:
                #@+<< create leoScriptModule >>
                #@+node:ekr.20060524073716: *5* << create leoScriptModule >> (mod_scripting.py)
                target = g.os_path_join(g.app.loadDir, 'leoScriptModule.py')
                f = None
                try:
                    f = open(target, 'w')
                    f.write('# A module holding the script to be debugged.\n')
                    if self.debuggerKind == 'idle':
                        # This works, but uses the lame pdb debugger.
                        f.write('import pdb\n')
                        f.write('pdb.set_trace() # Hard breakpoint.\n')
                    elif self.debuggerKind == 'winpdb':
                        f.write('import rpdb2\n')
                        f.write('if rpdb2.g_debugger is not None: # don\'t hang if the debugger isn\'t running.\n')
                        f.write('  rpdb2.start_embedded_debugger(pwd="",fAllowUnencrypted=True) # Hard breakpoint.\n')
                    # f.write('# Remove all previous variables.\n')
                    f.write('# Predefine c, g and p.\n')
                    f.write('import leo.core.leoGlobals as g\n')
                    f.write('c = g.app.scriptDict.get("c")\n')
                    f.write('script_gnx = g.app.scriptDict.get("script_gnx")\n')
                    f.write('p = c.p\n')
                    f.write('# Actual script starts here.\n')
                    f.write(script + '\n')
                finally:
                    if f: f.close()
                #@-<< create leoScriptModule >>
                # pylint: disable=no-name-in-module
                g.app.scriptDict['c'] = c
                g.app.scriptDict = {'script_gnx': p.gnx}
                if 'leoScriptModule' in sys.modules.keys():
                    del sys.modules['leoScriptModule'] # Essential.
                import leo.core.leoScriptModule as leoScriptModule
                assert leoScriptModule # for pyflakes.
            else:
                g.error('No debugger active')
        c.bodyWantsFocus()
    #@+node:ekr.20060328125248.21: *4* sc.runScriptCommand
    def runScriptCommand(self, event=None):
        '''Called when user presses the 'run-script' button or executes the run-script command.'''
        c, p = self.c, self.c.p
        args = self.getArgs(p)
        g.app.scriptDict = {'script_gnx': p.gnx}
        c.executeScript(args=args, p=p, useSelectedText=True, silent=True)
        if 0:
            # Do not assume the script will want to remain in this commander.
            c.bodyWantsFocus()
    #@+node:ekr.20060328125248.8: *3* sc.createAllButtons
    def createAllButtons(self):
        '''Scan for @button, @rclick, @command, @plugin and @script nodes.'''
        c = self.c
        if self.scanned:
            return # Defensive.
        self.scanned = True
        # First, create standard buttons.
        if self.createRunScriptButton:
            self.createRunScriptIconButton()
        if self.createScriptButtonButton:
            self.createScriptButtonIconButton()
        if self.createDebugButton:
            self.createDebugIconButton()
        # Next, create common buttons and commands.
        self.createCommonButtons()
        self.createCommonCommands()
        # Last, scan for user-defined nodes.
        table = (
            ('@button', self.handleAtButtonNode),
            ('@command', self.handleAtCommandNode),
            ('@plugin', self.handleAtPluginNode),
            ('@rclick', self.handleAtRclickNode), # Jake Peck.
            ('@script', self.handleAtScriptNode),
        )
        p = c.rootPosition()
        while p:
            gnx = p.v.gnx
            if p.isAtIgnoreNode():
                p.moveToNodeAfterTree()
            elif gnx in self.seen:
                # tag:#657
                if g.match_word(p.h, 0, '@rclick'):
                    self.handleAtRclickNode(p)
                p.moveToThreadNext()
            else:
                self.seen.add(gnx)
                for kind, func in table:
                    if g.match_word(p.h, 0, kind):
                        func(p)
                        break
                p.moveToThreadNext()
    #@+node:ekr.20060328125248.24: *3* sc.createLocalAtButtonHelper
    def createLocalAtButtonHelper(self, p, h, statusLine,
        kind='at-button',
        verbose=True,
    ):
        '''Create a button for a local @button node.'''
        c = self.c
        buttonText = self.cleanButtonText(h, minimal=True)
        args = self.getArgs(p)
        # We must define the callback *after* defining b,
        # so set both command and shortcut to None here.
        bg = self.getColor(h)
        b = self.createIconButton(
            args=args,
            text=h,
            command=None,
            statusLine=statusLine,
            kind=kind,
            bg=bg,
        )
        if not b:
            return None
        # Now that b is defined we can define the callback.
        # Yes, executeScriptFromButton *does* use b (to delete b if requested by the script).
        docstring = g.getDocString(p.b).strip()
        cb = AtButtonCallback(
            controller=self,
            b=b,
            c=c,
            buttonText=buttonText,
            docstring=docstring,
            gnx=p.v.gnx,
            script=None,
        )
        self.iconBar.setCommandForButton(
            button=b,
            command=cb, # This encapsulates the script.
            command_p=p and p.copy(), # This does exist.
            controller=self,
            gnx=p and p.gnx,
            script=None,
        )
        # At last we can define the command and use the shortcut.
        # registerAllCommands recomputes the shortcut.
        self.registerAllCommands(
            args=self.getArgs(p),
            func=cb,
            h=h,
            pane='button',
            source_c=p.v.context,
            tag='local @button')
        return b
    #@+node:ekr.20060328125248.17: *3* sc.createIconButton (creates all buttons)
    def createIconButton(self, args, text, command, statusLine, bg=None, kind=None):
        '''
        Create one icon button.
        This method creates all scripting icon buttons.

        - Creates the actual button and its balloon.
        - Adds the button to buttonsDict.
        - Registers command with the shortcut.
        - Creates x amd delete-x-button commands, where x is the cleaned button name.
        - Binds a right-click in the button to a callback that deletes the button.
        '''
        c = self.c
        # Create the button and add it to the buttons dict.
        commandName = self.cleanButtonText(text)
        # Truncate only the text of the button, not the command name.
        truncatedText = self.truncateButtonText(commandName)
        if not truncatedText.strip():
            g.error('%s ignored: no cleaned text' % (text.strip() or ''))
            return None
        # Command may be None.
        b = self.iconBar.add(text=truncatedText, command=command, kind=kind)
        if not b:
            return None
        self.setButtonColor(b, bg)
        self.buttonsDict[b] = truncatedText
        if statusLine:
            self.createBalloon(b, statusLine)
        if command:
            self.registerAllCommands(
                args=args,
                func=command,
                h=text,
                pane='button',
                source_c=c,
                tag='icon button')

        def deleteButtonCallback(event=None, self=self, b=b):
            self.deleteButton(b, event=event)
        # Register the delete-x-button command.

        deleteCommandName = 'delete-%s-button' % commandName
        c.k.registerCommand(
            # allowBinding=True,
            commandName=deleteCommandName,
            func=deleteButtonCallback,
            pane='button',
            shortcut=None,
        )
            # Reporting this command is way too annoying.
        return b
    #@+node:ekr.20060328125248.28: *3* sc.executeScriptFromButton
    def executeScriptFromButton(self, b, buttonText, p, script, script_gnx=None):
        '''Execute an @button script in p.b or script.'''
        c = self.c
        if c.disableCommandsMessage:
            g.blue(c.disableCommandsMessage)
            return None
        if not p and not script:
            g.trace('can not happen: no p and no script')
            return
        g.app.scriptDict = {'script_gnx': script_gnx}
        args = self.getArgs(p)
        if not script:
            script = self.getScript(p)
        c.executeScript(args=args, p=p, script=script, silent=True)
        # Remove the button if the script asks to be removed.
        if g.app.scriptDict.get('removeMe'):
            g.es("Removing '%s' button at its request" % buttonText)
            self.deleteButton(b)
        # Do *not* set focus here: the script may have changed the focus.
            # c.bodyWantsFocus()
    #@+node:ekr.20130912061655.11294: *3* sc.open_gnx
    def open_gnx(self, c, gnx):
        '''
        Find the node with the given gnx in c, myLeoSettings.leo and leoSettings.leo.
        If found, open the tab/outline and select the specified node.
        Return c,p of the found node.
        '''
        trace = False and not g.unitTesting
        if not gnx: g.trace('can not happen: no gnx')
        # First, look in commander c.
        for p2 in c.all_positions():
            if p2.gnx == gnx:
                if trace: g.trace('Found', c.shortFileName(), p2.h)
                return c, p2
        # Fix bug 74: problems with @button if defined in myLeoSettings.leo.
        for f in (c.openMyLeoSettings, c.openLeoSettings):
            c2 = f() # Open the settings file.
            if c2:
                for p2 in c2.all_positions():
                    if p2.gnx == gnx:
                        if trace: g.trace('Found', c2.shortFileName(), p2.h)
                        return c2, p2
                c2.close()
        # Fix bug 92: restore the previously selected tab.
        if trace: g.trace('Not found', gnx)
        if g.app.qt_use_tabs:
            c.frame.top.leo_master.select(c)
                # c.frame.top.leo_master is a LeoTabbedTopLevel.
        return None, None # 2017/02/02.
    #@+node:ekr.20150401130207.1: *3* sc.Scripts, common
    #@+node:ekr.20080312071248.1: *4* sc.createCommonButtons
    def createCommonButtons(self):
        '''Handle all global @button nodes.'''
        c = self.c
        buttons = c.config.getButtons() or []
        for z in buttons:
            p, script = z
            gnx = p.v.gnx
            if gnx not in self.seen:
                self.seen.add(gnx)
                script = self.getScript(p)
                self.createCommonButton(p, script, rclicks=p.rclicks)
    #@+node:ekr.20070926084600: *4* sc.createCommonButton (common @button)
    def createCommonButton(self, p, script, rclicks=None):
        '''
        Create a button in the icon area for a common @button node in an @setting
        tree. Binds button presses to a callback that executes the script.
        '''
        c = self.c
        # g.trace('global @button', c.shortFileName(), p.gnx, p.h)
        gnx = p.gnx
        args = self.getArgs(p)
        # Fix bug #74: problems with @button if defined in myLeoSettings.leo
        docstring = g.getDocString(p.b).strip()
        statusLine = docstring or 'Global script button'
        shortcut = self.getShortcut(p.h)
            # Get the shortcut from the @key field in the headline.
        if shortcut:
            statusLine = '%s = %s' % (statusLine.rstrip(), shortcut)
        # We must define the callback *after* defining b,
        # so set both command and shortcut to None here.
        b = self.createIconButton(
            args=args,
            text=p.h,
            command=None,
            statusLine=statusLine,
            kind='at-button',
        )
        if not b:
            return
        # Now that b is defined we can define the callback.
        # Yes, the callback *does* use b (to delete b if requested by the script).
        buttonText = self.cleanButtonText(p.h)
        cb = AtButtonCallback(
            controller=self,
            b=b,
            c=c,
            buttonText=buttonText,
            docstring=docstring,
            gnx=gnx, # tag:#367: the gnx is needed for the Goto Script command.
            script=script,
        )
        # Now patch the button.
        self.iconBar.setCommandForButton(
            button=b,
            command=cb, # This encapsulates the script.
            command_p=p and p.copy(), # tag:#567
            controller=self,
            gnx=gnx, # For the find-button function.
            script=script,
        )
        self.handleRclicks(rclicks)
        # At last we can define the command.
        self.registerAllCommands(
            args=args,
            func=cb,
            h=p.h,
            pane='button',
            source_c=p.v.context,
            tag='@button')
    #@+node:ekr.20080312071248.2: *4* sc.createCommonCommands
    def createCommonCommands(self):
        '''Handle all global @command nodes.'''
        c = self.c
        aList = c.config.getCommands() or []
        for z in aList:
            p, script = z
            gnx = p.v.gnx
            if gnx not in self.seen:
                self.seen.add(gnx)
                script = self.getScript(p)
                self.createCommonCommand(p, script)
    #@+node:ekr.20150401130818.1: *4* sc.createCommonCommand (common @command)
    def createCommonCommand(self, p, script):
        '''Handle a single @command node.'''
        c = self.c
        args = self.getArgs(p)

        def commonCommandCallback(event=None, script=script):
            c.executeScript(args=args, script=script, silent=True)

        commonCommandCallback.__doc__ = g.getDocString(script).strip()
            # Bug fix: 2015/03/28.
        self.registerAllCommands(
            args=args,
            func=commonCommandCallback,
            h=p.h,
            pane='button', # Fix bug 416: use 'button', NOT 'command', and NOT 'all'
            source_c=p.v.context,
            tag='global @command')
    #@+node:ekr.20150401130313.1: *3* sc.Scripts, individual
    #@+node:ekr.20060328125248.12: *4* sc.handleAtButtonNode @button
    def handleAtButtonNode(self, p):
        '''
        Create a button in the icon area for an @button node.

        An optional @key=shortcut defines a shortcut that is bound to the button's script.
        The @key=shortcut does not appear in the button's name, but
        it *does* appear in the statutus line shown when the mouse moves over the button.

        An optional @color=colorname defines a color for the button's background.  It does
        not appear in the status line nor the button name.
        '''
        trace = False and not g.app.unitTesting and not g.app.batchMode
        h = p.h
        shortcut = self.getShortcut(h)
        docstring = g.getDocString(p.b).strip()
        statusLine = docstring if docstring else 'Local script button'
        if shortcut:
            statusLine = '%s = %s' % (statusLine, shortcut)
        g.app.config.atLocalButtonsList.append(p.copy())
        # g.trace(c.config,p.h)
        # This helper is also called by the script-button callback.
        if trace: g.trace('local @button', h)
        self.createLocalAtButtonHelper(p, h, statusLine, verbose=False)
    #@+node:ekr.20060328125248.10: *4* sc.handleAtCommandNode @command
    def handleAtCommandNode(self, p):
        '''Handle @command name [@key[=]shortcut].'''
        c = self.c
        if not p.h.strip(): return
        args = self.getArgs(p)

        def atCommandCallback(event=None, args=args, c=c, p=p.copy()):
            # pylint: disable=dangerous-default-value
            c.executeScript(args=args, p=p, silent=True)

        # Fix bug 1251252: https://bugs.launchpad.net/leo-editor/+bug/1251252
        # Minibuffer commands created by mod_scripting.py have no docstrings

        atCommandCallback.__doc__ = g.getDocString(p.b).strip()
        self.registerAllCommands(
            args=args,
            func=atCommandCallback,
            h=p.h,
            pane='button', # Fix # 416.
            source_c=p.v.context,
            tag='local @command')
        g.app.config.atLocalCommandsList.append(p.copy())
    #@+node:ekr.20060328125248.13: *4* sc.handleAtPluginNode @plugin
    def handleAtPluginNode(self, p):
        '''Handle @plugin nodes.'''
        tag = "@plugin"
        h = p.h
        assert(g.match(h, 0, tag))
        # Get the name of the module.
        theFile = h[len(tag):].strip()
        # The following two lines break g.loadOnePlugin
        #if theFile[-3:] == ".py":
        #    theFile = theFile[:-3]
        # in fact, I believe the opposite behavior is intended: add .py if it doesn't exist
        if theFile[-3:] != ".py":
            theFile = theFile + ".py"
        theFile = g.toUnicode(theFile)
        if not self.atPluginNodes:
            g.warning("disabled @plugin: %s" % (theFile))
        # elif theFile in g.app.loadedPlugins:
        elif g.pluginIsLoaded(theFile):
            g.warning("plugin already loaded: %s" % (theFile))
        else:
            g.loadOnePlugin(theFile)
    #@+node:peckj.20131113130420.6851: *4* sc.handleAtRclickNode @rclick
    def handleAtRclickNode(self, p):
        '''Handle @rclick name [@key[=]shortcut].'''
        c = self.c
        if not p.h.strip():
            return
        args = self.getArgs(p)

        def atCommandCallback(event=None, args=args, c=c, p=p.copy()):
            # pylint: disable=dangerous-default-value
            c.executeScript(args=args, p=p, silent=True)
        if p.b.strip():
            self.registerAllCommands(
                args=args,
                func=atCommandCallback,
                h=p.h,
                pane='all',
                source_c=p.v.context,
                tag='local @rclick')
        g.app.config.atLocalCommandsList.append(p.copy())
    #@+node:vitalije.20180224113123.1: *4* sc.handleRclicks
    def handleRclicks(self, rclicks):
        def handlerc(rc):
            if rc.children:
                for i in rc.children:
                    handlerc(i)
            else:
                self.handleAtRclickNode(rc.position)
        for rc in rclicks:
            handlerc(rc)
        
    #@+node:ekr.20060328125248.14: *4* sc.handleAtScriptNode @script
    def handleAtScriptNode(self, p):
        '''Handle @script nodes.'''
        c = self.c
        tag = "@script"
        assert(g.match(p.h, 0, tag))
        name = p.h[len(tag):].strip()
        args = self.getArgs(p)
        if self.atScriptNodes:
            g.blue("executing script %s" % (name))
            c.executeScript(args=args, p=p, useSelectedText=False, silent=True)
        else:
            g.warning("disabled @script: %s" % (name))
        if 0:
            # Do not assume the script will want to remain in this commander.
            c.bodyWantsFocus()
    #@+node:ekr.20150401125747.1: *3* sc.Standard buttons
    #@+node:ekr.20060522105937: *4* sc.createDebugIconButton 'debug-script'
    def createDebugIconButton(self):
        '''Create the 'debug-script' button and the debug-script command.'''
        self.createIconButton(
            args=None,
            text='debug-script',
            command=self.runDebugScriptCommand,
            statusLine='Debug script in selected node',
            kind='debug-script')
    #@+node:ekr.20060328125248.20: *4* sc.createRunScriptIconButton 'run-script'
    def createRunScriptIconButton(self):
        '''Create the 'run-script' button and the run-script command.'''
        self.createIconButton(
            args=None,
            text='run-script',
            command=self.runScriptCommand,
            statusLine='Run script in selected node',
            kind='run-script',
        )
    #@+node:ekr.20060328125248.22: *4* sc.createScriptButtonIconButton 'script-button'
    def createScriptButtonIconButton(self):
        '''Create the 'script-button' button and the script-button command.'''
        self.createIconButton(
            args=None,
            text='script-button',
            command=self.addScriptButtonCommand,
            statusLine='Make script button from selected node',
            kind="script-button-button")
    #@+node:ekr.20061014075212: *3* sc.Utils
    #@+node:ekr.20060929135558: *4* sc.cleanButtonText
    def cleanButtonText(self, s, minimal=False):
        '''Clean the text following @button or @command so that it is a valid name of a minibuffer command.'''
        # 2011/10/16: Delete {tag}
        s = s.strip()
        i, j = s.find('{'), s.find('}')
        if -1 < i < j:
            s = s[: i] + s[j + 1:]
            s = s.strip()
        if minimal:
            return s.lower()
        for tag in ('@key', '@args', '@color',):
            i = s.find(tag)
            if i > -1:
                j = s.find('@', i + 1)
                if i < j:
                    s = s[: i] + s[j:]
                else:
                    s = s[: i]
                s = s.strip()
        if 1: # Not great, but spaces, etc. interfere with tab completion.
            # 2011/10/16 *do* allow '@' sign.
            chars = g.toUnicode(string.ascii_letters + string.digits + '@' + '-')
            aList = [ch if ch in chars else '-' for ch in g.toUnicode(s)]
            s = ''.join(aList)
            s = s.replace('--', '-')
        return s.strip('-').lower()
    #@+node:ekr.20060522104419.1: *4* sc.createBalloon (gui-dependent)
    def createBalloon(self, w, label):
        'Create a balloon for a widget.'
        if g.app.gui.guiName().startswith('qt'):
            # w is a leoIconBarButton.
            if hasattr(w, 'button'):
                w.button.setToolTip(label)
    #@+node:ekr.20060328125248.26: *4* sc.deleteButton
    def deleteButton(self, button, **kw):
        """Delete the given button.
        This is called from callbacks, it is not a callback."""
        w = button
        if button and self.buttonsDict.get(w):
            del self.buttonsDict[w]
            self.iconBar.deleteButton(w)
            self.c.bodyWantsFocus()
    #@+node:ekr.20080813064908.4: *4* sc.getArgs
    def getArgs(self, p):
        '''Return the list of @args field of p.h.'''
        args = []
        if not p:
            return args
        h, tag = p.h, '@args'
        i = h.find(tag)
        if i > -1:
            j = g.skip_ws(h, i + len(tag))
            # 2011/10/16: Make '=' sign optional.
            if g.match(h, j, '='): j += 1
            if 0:
                s = h[j + 1:].strip()
            else: # new logic 1/3/2014 Jake Peck
                k = h.find('@', j + 1)
                if k == -1: k = len(h)
                s = h[j: k].strip()
            args = s.split(',')
            args = [z.strip() for z in args]
        # if args: g.trace(args)
        return args
    #@+node:ekr.20060328125248.15: *4* sc.getButtonText
    def getButtonText(self, h):
        '''Returns the button text found in the given headline string'''
        tag = "@button"
        if g.match_word(h, 0, tag):
            h = h[len(tag):].strip()
        for tag in ('@key', '@args', '@color',):
            i = h.find(tag)
            if i > -1:
                j = h.find('@', i + 1)
                if i < j:
                    h = h[: i] + h[j + 1:]
                else:
                    h = h[: i]
                h = h.strip()
        buttonText = h
        # fullButtonText = buttonText
        return buttonText
    #@+node:peckj.20140103101946.10404: *4* sc.getColor
    def getColor(self, h):
        '''Returns the background color from the given headline string'''
        color = None
        tag = '@color'
        i = h.find(tag)
        if i > -1:
            j = g.skip_ws(h, i + len(tag))
            if g.match(h, j, '='): j += 1
            k = h.find('@', j + 1)
            if k == -1: k = len(h)
            color = h[j: k].strip()
        return color
    #@+node:ekr.20060328125248.16: *4* sc.getShortcut
    def getShortcut(self, h):
        '''Return the keyboard shortcut from the given headline string'''
        shortcut = None
        i = h.find('@key')
        if i > -1:
            j = g.skip_ws(h, i + len('@key'))
            if g.match(h, j, '='): j += 1
            if 0:
                shortcut = h[j:].strip()
            else: # new logic 1/3/2014 Jake Peck
                k = h.find('@', j + 1)
                if k == -1: k = len(h)
                shortcut = h[j: k].strip()
        return shortcut
    #@+node:ekr.20150402042350.1: *4* sc.getScript
    def getScript(self, p):
        '''Return the script composed from p and its descendants.'''
        return (
            g.getScript(self.c, p,
                useSelectedText=False,
                forcePythonSentinels=True,
                useSentinels=True,
            ))
    #@+node:ekr.20120301114648.9932: *4* sc.registerAllCommands
    def registerAllCommands(self, args, func, h, pane, source_c=None, tag=None):
        '''Register @button <name> and @rclick <name> and <name>'''
        trace = False and not g.unitTesting
        trace_name = False
        c, k = self.c, self.c.k
        shortcut = self.getShortcut(h) or ''
        if trace: g.trace('pane', pane, 'shortcut', shortcut, h)
        commandName = self.cleanButtonText(h)
        if trace and trace_name:
            if hasattr(func, '__name__'):
                g.trace(func.__name__, func.__doc__)
            else:
                g.trace(func)
        # Register the original function.
        k.registerCommand(
            allowBinding=True,
            commandName=commandName,
            func=func,
            pane=pane,
            shortcut=shortcut,
        )

        # 2013/11/13 Jake Peck:
        # include '@rclick-' in list of tags
        for prefix in ('@button-', '@command-', '@rclick-'):
            if commandName.startswith(prefix):
                commandName2 = commandName[len(prefix):].strip()
                # Create a *second* func, to avoid collision in c.commandsDict.

                def registerAllCommandsCallback(event=None, func=func):
                    func()
        
                # Fix bug 1251252: https://bugs.launchpad.net/leo-editor/+bug/1251252
                # Minibuffer commands created by mod_scripting.py have no docstrings.
                registerAllCommandsCallback.__doc__ = func.__doc__
                # Make sure we never redefine an existing commandName.
                if commandName2 in c.commandsDict:
                    # A warning here would probably be annoying.
                    pass
                else:
                    k.registerCommand(
                        commandName=commandName2,
                        func=registerAllCommandsCallback,
                        pane=pane,
                        shortcut=None
                    )
    #@+node:ekr.20150402021505.1: *4* sc.setButtonColor
    def setButtonColor(self, b, bg):
        '''Set the background color of Qt button b to bg.'''
        if not bg:
            return
        if not bg.startswith('#'):
            bg0 = bg
            d = leoColor.leo_color_database
            bg = d.get(bg.lower())
            if not bg:
                g.trace('bad color? %s' % bg0)
                return
        try:
            b.button.setStyleSheet("QPushButton{background-color: %s}" % (bg))
        except Exception:
            # g.es_exception()
            pass # Might not be a valid color.
    #@+node:ekr.20061015125212: *4* sc.truncateButtonText
    def truncateButtonText(self, s):
        # 2011/10/16: Remove @button here only.
        i = 0
        while g.match(s, i, '@'):
            i += 1
        if g.match_word(s, i, 'button'):
            i += 6
        s = s[i:]
        if self.maxButtonSize > 10:
            s = s[: self.maxButtonSize]
            if s.endswith('-'):
                s = s[: -1]
        s = s.strip('-')
        return s.strip()
    #@-others

scriptingController = ScriptingController
#@-others
#@-leo
