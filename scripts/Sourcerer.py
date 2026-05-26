"""
Sourcerer - Media source management for TouchDesigner.

A streamlined component for managing, switching, and transitioning between
file-based media and TOP-based generative content.

Author: Matthew Wachter
License: MIT
"""

import copy
import json
import os
from TDStoreTools import StorageManager, DependList
import TDFunctions as TDF
from CallbacksExt import CallbacksExt


class TransitionState:
    """State machine states for source transitions."""
    IDLE = 'idle'
    TRANSITIONING = 'transitioning'


class SourceType:
    FILE = 'file'
    TOP = 'top'


class DoneOn:
    NONE = 'none'
    PLAY_N_TIMES = 'play_n_times'
    TIMER = 'timer'
    CHOP = 'chop'


class FollowAction:
    NONE = 'none'
    PLAY_NEXT = 'play_next'
    GOTO_INDEX = 'goto_index'
    GOTO_NAME = 'goto_name'


class Sourcerer(CallbacksExt):
    """
    Main Sourcerer extension for managing media sources and transitions.

    Provides centralized source management with a list-based interface,
    built-in transitions, follow actions, and real-time display properties.

    Architecture:
        Source Components:
        - defaultSource: Clone master, stores default parameter template
        - selectedSource: User-facing editor, Storechanges=True
        - source0, source1: Playback pair for A/B transitions, Active=True when live

        State Machine:
        - State (0 or 1): Which source comp is currently live
        - Transitions ping-pong between source0 and source1
        - During transition, outgoing source continues while incoming starts
    """

    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        
        self.callbackDat = self.ownerComp.par.Callbackdat.eval()

        try:
            super().__init__(ownerComp)
        except Exception:
            error_msg = traceback.format_exc()
            self.ownerComp.addScriptError(
                f"{error_msg} Error in CallbacksExt __init__. See textport."
            )
            print(f"Error initializing callbacks - {self.ownerComp.path}")
            print(error_msg)

        try:
            self.DoCallback('onInit', {'ownerComp': self.ownerComp})
        except Exception:
            error_msg = traceback.format_exc()
            self.ownerComp.addScriptError(
                f"{error_msg} Error in custom onInit callback. See textport."
            )
            print(error_msg)
        
        self.DataComp = ownerComp.op('data')
        self.transitionComp = ownerComp.op('transitions')
        self.switcherState = ownerComp.op('state')
        self.selectedSourceComp = ownerComp.op('selectedSource')

        storedItems = [
            {'name': 'Sources', 'default': [], 'dependable': True},
            {
                'name': 'SelectedSource',
                'default': {'index': 0, 'name': ''},
                'dependable': True
            },
            {
                'name': 'ActiveSource',
                'default': {'index': -1, 'name': ''},
                'dependable': True
            },
            {'name': 'State', 'default': 0, 'dependable': True},
            {'name': 'Safety', 'default': False, 'dependable': True},
            {'name': 'Log', 'default': [], 'dependable': True},
            {'name': 'LogFormatted', 'default': [], 'dependable': True},
            {'name': 'PendingQueue', 'default': [], 'dependable': True},
            {'name': 'SourceNames', 'default': [], 'dependable': True},
        ]

        self.stored = StorageManager(self, self.DataComp, storedItems)

        # State machine for transitions
        self.transitionState = TransitionState.IDLE

        # update source list initially
        self._updateSourceList()

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def ActiveSourceComp(self):
        """The currently active source component (source0 or source1)."""
        return self.ownerComp.op('source' + str(self.stored['State']))

    @property
    def isTransitioning(self):
        """Whether a transition is currently in progress."""
        return self.transitionState == TransitionState.TRANSITIONING

    @property
    def isQueueEnabled(self):
        """Whether the pending queue is enabled."""
        return self.ownerComp.par.Enablependingqueue.eval()

    @property
    def isEditingActive(self):
        """Whether the selected source is the active source (for UI warnings)."""
        return self.stored['SelectedSource']['index'] == self.stored['ActiveSource']['index']

    # -------------------------------------------------------------------------
    # Safety Mode
    # -------------------------------------------------------------------------

    def ToggleSafety(self):
        """Toggle safety mode on or off."""
        self.stored['Safety'] = not self.stored['Safety']

    def _confirmSafetyAction(self, action_name, force=False):
        """
        Prompt user to confirm a destructive action.

        Args:
            action_name: Name of the action for the dialog
            force: If True, always prompt regardless of safety mode

        Returns True if action should proceed, False if cancelled.
        """
        if not force and not self.stored['Safety']:
            return True
        result = ui.messageBox(f'Confirm {action_name}',
                               f'Are you sure you want to {action_name.lower()}?',
                               buttons=['OK', 'Cancel'])
        return result == 0  # 0 = OK, 1 = Cancel

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------

    # Log colors (RGB 0-255) based on list color palette
    LOG_COLORS = {
        'time': (178, 178, 178),        # label_font gray
        'Take': (51, 127, 204),                 # blue
        'TransitionComplete': (140, 220, 180),  # green
        'SourceDone': (255, 200, 50),           # yellow
        'StoreDefault': (200, 150, 255),        # purple
        'AddSource': (100, 200, 100),           # green
        'DeleteSource': (255, 100, 100),        # red
        'RenameSource': (100, 200, 200),        # cyan
        'MoveSource': (100, 150, 255),          # light blue
        'Init': (200, 200, 200),                # gray
        'FileOpenFailed': (255, 80, 80),        # bright red for errors
        'data': (255, 255, 255),                # white
    }

    def _log(self, event, data, level='INFO'):
        """Add an entry to the log with timestamp. Newest first, max 10 entries.

        Args:
            event: Event name (e.g., 'Take', 'AddSource')
            data: Dict of event data
            level: Log level for external logger ('INFO', 'WARNING', 'ERROR')
        """
        import datetime

        # Format time with 2 decimal places on seconds
        now = datetime.datetime.now()
        time_str = now.strftime('%Y-%m-%d %H:%M:%S') + f'.{now.microsecond // 10000:02d}'

        entry = {
            'time': time_str,
            'event': event,
            'data': data
        }
        self.stored['Log'].insert(0, entry)

        # Build formatted string with colors
        tc = self.LOG_COLORS['time']
        ec = self.LOG_COLORS.get(event, (255, 255, 255))
        dc = self.LOG_COLORS['data']

        # Format data as "key: value" pairs
        data_str = ', '.join(f'{k}: {v}' for k, v in data.items())

        # Pad event name to 18 chars (length of "TransitionComplete")
        event_padded = f"{event:<18}"

        formatted = (
            f"{{#color({tc[0]}, {tc[1]}, {tc[2]});}}{time_str}  "
            f"{{#color({ec[0]}, {ec[1]}, {ec[2]});}}{event_padded}  "
            f"{{#color({dc[0]}, {dc[1]}, {dc[2]});}}{data_str}"
        )
        self.stored['LogFormatted'].insert(0, formatted)

        # Keep only the first 10 entries (newest)
        if len(self.stored['Log']) > 10:
            self.stored['Log'] = self.stored['Log'][:10]
        if len(self.stored['LogFormatted']) > 10:
            self.stored['LogFormatted'] = self.stored['LogFormatted'][:10]

        # Write to external Logger if enabled
        if self.ownerComp.par.Enablelogging.eval():
            logger = self.ownerComp.par.Logger.eval()
            if logger is not None:
                log_msg = f"{time_str} | {event} | {data_str}"
                match level:
                    case 'INFO':
                        logger.Info(log_msg)
                    case 'WARNING':
                        logger.Warning(log_msg)
                    case 'ERROR':
                        logger.Error(log_msg)
                    case _:
                        logger.Info(log_msg)

        # Fire onLog callback
        self.DoCallback('onLog', {
            'time': time_str,
            'event': event,
            'data': data,
            'level': level
        })

    def ClearLog(self):
        """Clear all log entries."""
        self.stored['Log'].clear()
        self.stored['LogFormatted'].clear()

    # -------------------------------------------------------------------------
    # Source Management
    # -------------------------------------------------------------------------

    def InitData(self, force_confirm=False):
        """Reset to clean state - delete all sources and create one new default source."""
        if not self._confirmSafetyAction(
            'Initialize (this will clear all sources and log)',
            force=force_confirm
        ):
            return

        # Clear all sources
        self.stored['Sources'] = []

        # Clear pending queue and reset transition state
        self.stored['PendingQueue'].clear()
        self.transitionState = TransitionState.IDLE

        # Create one default source
        source = self._getSourceTemplate('defaultSource')
        source['Settings']['Name'] = 'new_source'
        self.stored['Sources'].append(source)

        # Reset selection and active source
        self.stored['SelectedSource']['index'] = 0
        self.stored['SelectedSource']['name'] = 'new_source'
        self.stored['ActiveSource']['index'] = -1
        self.stored['ActiveSource']['name'] = ''
        self.stored['State'] = 0

        # Update the source list and UI
        self._updateSourceList()
        self.UpdateSelectedSourceComp()

        # Reset playback comps to default (stops any playing media)
        default_data = self._getSourceTemplate('defaultSource')
        self.ownerComp.op('source0').UpdateFromData(default_data, active=False, store_changes=False, index=-1)
        self.ownerComp.op('source1').UpdateFromData(default_data, active=False, store_changes=False, index=-1)

        # Clear and log
        self.ClearLog()
        self._log('Sourcerer v' + self.ownerComp.par.Version.eval(), {})

    def _updateSourceList(self):
        """Update the SourceNames dependable property from stored Sources."""
        self.stored['SourceNames'] = [str(s['Settings']['Name']) for s in self.stored['Sources']]

    def _getSource(self, source):
        """
        Look up a source by index, name, or return dict directly.

        Args:
            source: Source index (int), name (str), or source_data dict.

        Returns:
            Tuple of (source_data, index, name) or (None, None, None) if not found.
            For dict inputs: index is -1 (temp source).
        """
        source_data = None
        name = None
        index = None

        if isinstance(source, dict):
            # Direct source data (temp source)
            source_data = source
            name = source.get('Settings', {}).get('Name', 'Temp')
            index = -1

        elif isinstance(source, str):
            sources = self.stored['Sources']
            source_names = [s['Settings']['Name'] for s in sources]
            if source in source_names:
                s = source_names.index(source)
                source_data = self.stored['Sources'][s]
                name = source
                index = s
            else:
                debug('no source', source, 'in', source_names)

        elif isinstance(source, int):
            s = source
            index = source
            if source <= len(self.stored['Sources']) - 1:
                source_data = self.stored['Sources'][s]
                name = source_data['Settings']['Name']
            else:
                debug('source index', s, 'is out of range')

        else:
            debug('wrong source type', source)

        return source_data, index, name

    def Take(self, source, force=False):
        """Take (switch to) a source.

        Args:
            source: Source index (int), name (str), or source_data dict.
                    Dict sources are temp sources (not in source list, ActiveIndex = -1).
            force: If True, clears pending queue and switches immediately.
        """
        if force:
            self.stored['PendingQueue'].clear()
            self._beginTransition(source)
            return

        # Check if pending queue is enabled
        queue_enabled = self.ownerComp.par.Enablependingqueue.eval()

        # If already transitioning, decide whether to queue or switch immediately
        if self.transitionState == TransitionState.TRANSITIONING:
            if queue_enabled:
                # Avoid duplicate consecutive entries
                if not self.stored['PendingQueue'] or self.stored['PendingQueue'][-1] != source:
                    self.stored['PendingQueue'].append(source)
            else:
                # Queue disabled - begin transition immediately (will interrupt current)
                self._beginTransition(source)
            return

        self._beginTransition(source)

    def _beginTransition(self, source):
        """Start the actual transition to a source.

        Args:
            source: Source index (int), name (str), or source_data dict.
        """
        self.transitionState = TransitionState.TRANSITIONING

        source_data, index, name = self._getSource(source)
        if source_data is None:
            self.transitionState = TransitionState.IDLE
            return

        next_state = self._prepareNextSourceComp(source_data, index)
        self._configureTransition(source_data)
        self._updateActiveState(next_state, index, name)
        self._fireTransitionCallbacks(index, name, source_data)

    def _prepareNextSourceComp(self, source_data, index):
        """Prepare the next source component for playback.

        Returns:
            next_state: The state index (0 or 1) of the prepared source comp.
        """
        state = self.stored['State']
        next_state = 1 - state
        source_comp = self.ownerComp.op('source' + str(next_state))

        if index == -1:
            source_comp.UpdateFromData(source_data, active=True, store_changes=False, index=-1)
        else:
            self.UpdateSourceComp(source_comp, index)

        source_comp.Start()
        return next_state

    def _configureTransition(self, source_data):
        """Configure transition parameters from source settings."""
        settings = source_data['Settings']
        tcomp_par = self.transitionComp.par
        trans_type = settings['Transitiontype']
        tcomp_par.Transitiontype = trans_type

        if trans_type == 'dip':
            self._setParVal('Dipcolor', settings['Dipcolor'], self.transitionComp)
        elif trans_type in ('slide', 'wipe'):
            tcomp_par.Transitiondirection = settings['Transitiondirection']
        elif trans_type == 'file':
            tcomp_par.Transitionfile = settings['Transitionfile']
        elif trans_type == 'top':
            tcomp_par.Transitiontop = settings['Transitiontop']
        elif trans_type == 'blur':
            tcomp_par.Bluramount = settings.get('Bluramount', 8.0)

        if settings['Useglobaltransitiontime']:
            trans_time = self.ownerComp.par.Globaltransitiontime.eval()
        else:
            trans_time = settings['Transitiontime']
        tcomp_par.Transitiontime = trans_time

        trans_shape = settings['Transitionshape']
        tcomp_par.Transitionshape = trans_shape
        if trans_shape == 'custom':
            tcomp_par.Customtransitionshape = settings['Customtransitionshape']

    def _updateActiveState(self, next_state, index, name):
        """Update state machine and active source tracking."""
        self.stored['State'] = next_state
        self.stored['ActiveSource']['index'] = index
        self.stored['ActiveSource']['name'] = name

    def _fireTransitionCallbacks(self, index, name, source_data):
        """Fire callbacks and log the transition."""
        self.DoCallback('onTake', {
            'index': index,
            'name': name,
            'source_data': source_data
        })
        self._log('Take', {'index': index, 'name': name})

    def OnTransitionComplete(self):
        """Called when the transition animation finishes.
        Hook this up to be called when the transition timer/animation ends."""
        self.transitionState = TransitionState.IDLE

        self.DoCallback('onTransitionComplete', {
            'index': self.stored['ActiveSource']['index'],
            'name': self.stored['ActiveSource']['name']
        })

        self._log('TransitionComplete', {'index': self.stored['ActiveSource']['index'], 'name': self.stored['ActiveSource']['name']})

        # Process next item in queue if any
        if self.stored['PendingQueue']:
            next_source = self.stored['PendingQueue'].pop(0)
            self.Take(next_source)

    def OnSourceDone(self):
        """Called when the current source finishes (timer ends, video ends, etc.).
        Hook this up to source timer/video completion events."""
        self.DoCallback('onSourceDone', {
            'index': self.stored['ActiveSource']['index'],
            'name': self.stored['ActiveSource']['name']
        })

        self._log('SourceDone', {'index': self.stored['ActiveSource']['index'], 'name': self.stored['ActiveSource']['name']})

    def ClearPendingQueue(self):
        """Clear all pending source switches."""
        self.stored['PendingQueue'].clear()

    def SkipToLastPending(self):
        """Clear queue but keep last item - jump to final destination."""
        if len(self.stored['PendingQueue']) > 1:
            last = self.stored['PendingQueue'][-1]
            self.stored['PendingQueue'].clear()
            self.stored['PendingQueue'].append(last)

    def TakeSelected(self):
        """Take the currently selected source."""
        self.Take(self.stored['SelectedSource']['index'])

    def TakeNext(self, wrap=True):
        """Take the source after the currently active source.

        Args:
            wrap: If True, wraps from last source back to first.
        """
        sources = self.stored['Sources']
        if not sources:
            return
        active = self.stored['ActiveSource']['index']
        if active == -1:
            self.Take(0)
        elif wrap:
            self.Take((active + 1) % len(sources))
        elif active + 1 < len(sources):
            self.Take(active + 1)

    def TakePrevious(self, wrap=True):
        """Take the source before the currently active source.

        Args:
            wrap: If True, wraps from first source back to last.
        """
        sources = self.stored['Sources']
        if not sources:
            return
        active = self.stored['ActiveSource']['index']
        if active == -1:
            self.Take(len(sources) - 1)
        elif wrap:
            self.Take((active - 1) % len(sources))
        elif active - 1 >= 0:
            self.Take(active - 1)

    def DelayTake(self, source, delay=0):
        """Take a source after a delay in frames."""
        run(self.Take, source, delayFrames=delay)

    def RunCommand(self, command):
        """Execute a Python command string."""
        run(command, fromOP=self.ownerComp)

    # -------------------------------------------------------------------------
    # Import/Export
    # -------------------------------------------------------------------------

    def Import(self):
        """Import sources from a JSON file with location selection dialog."""
        f = ui.chooseFile(load=True, fileTypes=['json'], title='Import Sources')
        if f is None:
            return

        with open(f, 'r') as json_file:
            imported_sources = json.load(json_file)

        if not imported_sources:
            return

        location = ui.messageBox(
            'Sourcerer Import Location',
            'Select a location:',
            buttons=['Prepend', 'Insert (above selected)', 'Append']
        )
        sources = list(self.stored['Sources'])

        if location == 0:  # Prepend
            new_sources = imported_sources.copy()
            new_sources.extend(sources)
            self.stored['Sources'] = new_sources
            for i in range(len(imported_sources)):
                self._checkUniqueName(self.stored['Sources'][i], exclude_index=i)

        elif location == 1:  # Insert
            s = self.stored['SelectedSource']['index']
            new_sources = sources[:s] + imported_sources + sources[s:]
            self.stored['Sources'] = new_sources
            for i in range(s, s + len(imported_sources)):
                self._checkUniqueName(self.stored['Sources'][i], exclude_index=i)

        elif location == 2:  # Append
            new_sources = sources + imported_sources
            self.stored['Sources'] = new_sources
            for i in range(len(sources), len(new_sources)):
                self._checkUniqueName(self.stored['Sources'][i], exclude_index=i)

        self._updateSourceList()

    def ExportAll(self):
        """Export all sources to a JSON file."""
        f = ui.chooseFile(load=False, fileTypes=['json'], title='Export Sources')
        if f is None:
            return

        with open(f, 'w') as json_file:
            json.dump(self.stored['Sources'].getRaw(), json_file)

    def ExportSelected(self):
        """Export the selected source to a JSON file."""
        f = ui.chooseFile(load=False, fileTypes=['json'], title='Export Sources')
        if f is None:
            return

        selected = self.stored['SelectedSource']['index']
        with open(f, 'w') as json_file:
            json.dump([self.stored['Sources'][selected].getRaw()], json_file)

    def ExportRange(self, range_start=None, range_end=None):
        """Export a range of sources to a JSON file."""
        f = ui.chooseFile(load=False, fileTypes=['json'], title='Export Sources')
        if f is None:
            return

        if range_start is None:
            range_start = self.ownerComp.par.Exportrangeval1
        if range_end is None:
            range_end = self.ownerComp.par.Exportrangeval2

        sources = self.stored['Sources'].getRaw()[range_start:range_end + 1]
        with open(f, 'w') as json_file:
            json.dump(sources, json_file)

    def _getSourceTemplate(self, template):
        """Get a source template as a simple value dictionary from a template component."""
        template_op = self.ownerComp.op(template)
        return self._extractValues(template_op)

    def StoreDefaultFromSelected(self):
        """Store the selected source's settings as the default template."""
        # Get the selected source data
        idx = self.stored['SelectedSource']['index']
        name = self.stored['SelectedSource']['name']
        source_data = self.stored['Sources'][idx]

        # Get the default template component
        default_comp = self.ownerComp.op('defaultSource')

        # Write all parameter values to the default template
        for page_name, page_data in source_data.items():
            for par_name, value in page_data.items():
                self._setParVal(par_name, value, default_comp)

        self._log('StoreDefault', {'index': idx, 'name': name})

    # Suffix patterns for multi-value parameters that don't have a base accessor
    PAR_SUFFIXES = {
        'r': ['r', 'g', 'b'],      # Color parameters
        'x': ['x', 'y'],           # Translate, Scale, etc.
    }

    def _setParVal(self, par_name, value, target_comp):
        """Set a parameter value on a component, handling multi-value parameters."""
        if hasattr(target_comp.par, par_name):
            par = getattr(target_comp.par, par_name)
            if isinstance(value, (list, tuple)):
                for i, p in enumerate(par.tuplet):
                    if i < len(value):
                        p.val = value[i]
            else:
                par.val = value
        else:
            # Handle suffix-based parameters (color, xy, etc.)
            for first_suffix, suffixes in self.PAR_SUFFIXES.items():
                if hasattr(target_comp.par, par_name + first_suffix):
                    for i, suffix in enumerate(suffixes):
                        if i < len(value):
                            getattr(target_comp.par, par_name + suffix).val = value[i]
                    break

    # Parameters that are derived/read-only and should not be stored
    EXCLUDE_FROM_STORAGE = {'Filelengthframes', 'Filesamplerate'}
    # Parameter pages to exclude entirely from storage
    EXCLUDE_PAGES_FROM_STORAGE = {'Callbacks', 'Private'}

    def _extractValues(self, comp):
        """Extract parameter values from a component as a nested dictionary.

        Uses par.val instead of par.eval() for OP-type parameters to store
        string paths rather than operator objects (which can't be pickled).
        """
        source_dict = {}
        for page in comp.customPages:
            if page.name in self.EXCLUDE_PAGES_FROM_STORAGE:
                continue
            page_dict = {}
            for par in page.pars:
                if par.name in self.EXCLUDE_FROM_STORAGE:
                    continue
                if len(par.tuplet) > 1 and par == par.tuplet[0]:
                    if par.tupletName in self.EXCLUDE_FROM_STORAGE:
                        continue
                    # Use par.val for OP parameters to get string path, not operator object
                    page_dict[par.tupletName] = [p.val if p.isOP else p.eval() for p in par.tuplet]
                elif len(par.tuplet) == 1:
                    # Use par.val for OP parameters to get string path, not operator object
                    page_dict[par.name] = par.val if par.isOP else par.eval()
            source_dict[page.name] = page_dict
        return source_dict

    def UpdateSelectedSourceComp(self):
        """Update the selected source component from storage."""
        s = self.stored['SelectedSource']['index']
        self.UpdateSourceComp(self.selectedSourceComp, s, active=False, store_changes=True)

    def UpdateSourceComp(self, source_comp, source_index, active=True, store_changes=False):
        """Update a source component with data from storage."""
        source_data = self.stored['Sources'][source_index]
        source_comp.UpdateFromData(source_data, active=active, store_changes=store_changes, index=source_index)

    def StoreSourceToSelected(self, source_comp, update_selected_comp=False):
        """Store all source component parameters to the selected source in storage."""
        source = self.stored['SelectedSource']['index']
        self.StoreSource(source_comp, source)

        if update_selected_comp:
            self.UpdateSelectedSourceComp()

        # Update active source in real-time if editing it
        if source == self.stored['ActiveSource']['index']:
            active_comp = self.ownerComp.op('source' + str(self.stored['State']))
            self.UpdateSourceComp(active_comp, source, active=True, store_changes=False)

        self._updateSourceList()

    def StoreParToSelected(self, par):
        """Store a single parameter value to the selected source in storage."""
        index = self.stored['SelectedSource']['index']
        page_name = par.page.name

        # Skip excluded pages and parameters
        if page_name in self.EXCLUDE_PAGES_FROM_STORAGE:
            return
        if par.name in self.EXCLUDE_FROM_STORAGE:
            return

        # Handle tuplet parameters (colors, transforms, etc.)
        if len(par.tuplet) > 1 and par == par.tuplet[0]:
            self.stored['Sources'][index][page_name][par.tupletName] = [p.eval() for p in par.tuplet]
        elif len(par.tuplet) == 1:
            self.stored['Sources'][index][page_name][par.name] = par.eval()

        # Only update source list if name changed
        if par.name == 'Name':
            self._updateSourceList()

        # Update active source in real-time if editing it
        if index == self.stored['ActiveSource']['index']:
            active_comp = self.ownerComp.op('source' + str(self.stored['State']))
            self.UpdateSourceComp(active_comp, index, active=True, store_changes=False)

    def StoreSource(self, source_comp, source):
        """Store source component parameters to storage at given index."""
        self.stored['Sources'][source] = self._extractValues(source_comp)
        self._updateSourceList()

    def InitSource(self):
        """Reset the selected source to default template values."""
        source_dict = self._getSourceTemplate('defaultSource')
        s = self.stored['SelectedSource']['index']
        self.stored['Sources'][s] = source_dict
        self._updateSourceList()

    def _getUniqueName(self, name, exclude_index=None):
        """Get a unique name, optionally excluding an index (for renames)."""
        names = [s['Settings']['Name'] for i, s in enumerate(self.stored['Sources'])
                 if i != exclude_index]

        if name not in names:
            return name

        # Find next available number suffix
        base = name.rstrip('0123456789 ')
        i = 1
        while f"{base} {i}" in names:
            i += 1
        return f"{base} {i}"

    def _checkUniqueName(self, source, exclude_index=None):
        """Ensure source has a unique name. Returns the modified source."""
        name = str(source['Settings']['Name'])
        source['Settings']['Name'] = self._getUniqueName(name, exclude_index)
        self._updateSourceList()
        return source

    def GetDefaultSource(self):
        """Get a source template for customization.

        Returns a new dict that can be modified and passed to AddSource().

        Example:
            source = op('Sourcerer').GetDefaultSource()
            source['Settings']['Name'] = 'My Source'
            source['Settings']['Transitiontype'] = 'blur'
            source['File']['File'] = '/path/to/video.mp4'
            op('Sourcerer').AddSource(source_data=source)
        """
        return self._getSourceTemplate('defaultSource')

    def _addSource(self, source_data=None, source_type=None, source_path=None, source_name=None):
        """Internal add source without safety check."""
        # get the selected source index
        s = self.stored['SelectedSource']['index']

        # use provided source or default template
        if source_data is None:
            source_data = self._getSourceTemplate('defaultSource')

            # set the source type and path if provided
            if source_type == SourceType.FILE:
                source_data['Settings']['Sourcetype'] = SourceType.FILE
                if source_path is not None:
                    source_data['File']['File'] = source_path

            elif source_type == SourceType.TOP:
                source_data['Settings']['Sourcetype'] = SourceType.TOP
                if source_path is not None:
                    source_data['TOP']['Top'] = source_path

            # source_type=None leaves Sourcetype at its default value (likely 'none')

            # set the name - use provided name or default to "Source"
            source_data['Settings']['Name'] = source_name if source_name is not None else 'new_source'

        source_data = self._checkUniqueName(source_data)

        # insert the template into the sources list
        # handle empty list case - insert at 0 instead of s+1
        insert_index = s + 1 if self.stored['Sources'] else 0
        self.stored['Sources'].insert(insert_index, source_data)

        self.SelectSource(insert_index)

        # update the source comp parameters
        self.UpdateSourceComp(self.selectedSourceComp, insert_index, store_changes=True)
        self._updateSourceList()

        self._log('AddSource', {'index': insert_index, 'name': source_data['Settings']['Name']})

    def AddSource(self, source_data=None, source_type=None, source_path=None, source_name=None):
        """Add a new source.

        Args:
            source_data: Optional complete source dict (from GetDefaultSource()).
                         When provided, other arguments are ignored.
            source_type: 'file' or 'top' (ignored if source_data is provided)
            source_path: Path to file or TOP (ignored if source_data is provided)
            source_name: Display name (ignored if source_data is provided)
        """
        # Confirm if safety is on
        if not self._confirmSafetyAction('Add Source'):
            return
        self._addSource(source_data, source_type, source_path, source_name)
        return

    def DropSource(self, args):
        """Handle dropped files or TOPs, creating sources for valid items."""
        for dropped in args:
            if isinstance(dropped, str):
                if os.path.isfile(dropped):
                    base = os.path.basename(dropped)
                    source_name = os.path.splitext(base)[0]
                    file_ext = os.path.splitext(base)[1][1:]

                    if file_ext in tdu.fileTypes['movie'] or file_ext in tdu.fileTypes['image']:
                        self.AddSource(source_type='file', source_path=dropped, source_name=source_name)

            elif hasattr(dropped, 'family') and dropped.family == 'TOP':
                self.AddSource(source_type='top', source_path=dropped.path, source_name=dropped.name)

    def CopySource(self):
        """Duplicate the selected source."""
        s = self.stored['SelectedSource']['index']
        source = copy.deepcopy(self.stored['Sources'][s])
        source = self._checkUniqueName(source)
        self.stored['Sources'].insert(s, source)
        self.SelectSource(s)
        self._updateSourceList()

    def DeleteSource(self):
        """Delete the selected source."""
        if not self._confirmSafetyAction('Delete Source'):
            return

        s = self.stored['SelectedSource']['index']
        sources = self.stored['Sources']

        if len(sources) <= 1:
            self._updateSourceList()
            return

        deleted_name = sources[s]['Settings']['Name']
        is_active = (self.stored['ActiveSource']['index'] == s)

        sources.pop(s)

        if is_active:
            self.stored['ActiveSource']['index'] = -1
            self.stored['ActiveSource']['name'] = ''
        elif self.stored['ActiveSource']['index'] > s:
            self.stored['ActiveSource']['index'] -= 1

        if s >= len(sources):
            self.SelectSource(len(sources) - 1)
        else:
            self.SelectSource(s)

        self._log('DeleteSource', {'index': s, 'name': deleted_name})
        self._updateSourceList()

    def RenameSource(self, index, new_name):
        """Rename a source at the given index."""
        if not self._confirmSafetyAction('Rename Source'):
            return

        if not (0 <= index < len(self.stored['Sources'])):
            return

        old_name = self.stored['Sources'][index]['Settings']['Name']
        name = self._getUniqueName(str(new_name), exclude_index=index)
        self.stored['Sources'][index]['Settings']['Name'] = name

        if self.stored['SelectedSource']['index'] == index:
            self.stored['SelectedSource']['name'] = name

        if self.stored['ActiveSource']['index'] == index:
            self.stored['ActiveSource']['name'] = name

        self._updateSourceList()
        self.UpdateSelectedSourceComp()
        self._log('RenameSource', {'index': index, 'from': old_name, 'to': name})

    def MoveSource(self, from_index, to_index):
        """Move a source from one position to another."""
        if not self._confirmSafetyAction('Move Source'):
            return

        sources = self.stored['Sources']
        if from_index < 0 or from_index >= len(sources):
            return

        to_index = max(0, min(to_index, len(sources)))

        active_index = self.stored['ActiveSource']['index']
        moving_active = (from_index == active_index)

        source = sources.pop(from_index)
        moved_name = source['Settings']['Name']

        if from_index < to_index:
            to_index -= 1

        sources.insert(to_index, source)

        # Update ActiveSource index based on the move
        if moving_active:
            self.stored['ActiveSource']['index'] = to_index
        elif active_index >= 0:
            if from_index < active_index <= to_index:
                self.stored['ActiveSource']['index'] -= 1
            elif to_index <= active_index < from_index:
                self.stored['ActiveSource']['index'] += 1

        self.stored['SelectedSource']['index'] = to_index
        self.stored['SelectedSource']['name'] = moved_name

        self._updateSourceList()
        self.UpdateSelectedSourceComp()
        self._log('MoveSource', {'name': moved_name, 'from': from_index, 'to': to_index})

    def CopySourceData(self, source):
        """Copy source data by index or name.

        Args:
            source: Source index (int) or name (str).

        Returns:
            Deep copy of the source data dict, or None if not found.
        """
        source_data, _, _ = self._getSource(source)
        if source_data is not None:
            return copy.deepcopy(source_data).getRaw()
        return None

    def PasteSourceData(self, index, data):
        """Paste source data after the given index."""
        if not self._confirmSafetyAction('Paste Source'):
            return

        if data is None:
            return

        new_source = copy.deepcopy(data)
        new_source = self._checkUniqueName(new_source)
        self.stored['Sources'].insert(index + 1, new_source)
        self.SelectSource(index + 1)
        self._updateSourceList()

    def SelectSource(self, index):
        """Select a source by index for editing."""
        if index > len(self.stored['Sources']) - 1:
            index = index - 1

        self.stored['SelectedSource']['index'] = index

        if 0 <= index < len(self.stored['Sources']):
            self.stored['SelectedSource']['name'] = self.stored['Sources'][index]['Settings']['Name']
        else:
            self.stored['SelectedSource']['name'] = ''

        self.UpdateSelectedSourceComp()

    def SelectSourceUp(self):
        """Select the previous source in the list."""
        s = self.stored['SelectedSource']['index']
        if s > 0:
            self.SelectSource(s - 1)

    def SelectSourceDown(self):
        """Select the next source in the list."""
        s = self.stored['SelectedSource']['index']
        if s < len(self.stored['Sources']) - 1:
            self.SelectSource(s + 1)

    def MoveSourceUp(self):
        """Move the selected source up one position."""
        if not self._confirmSafetyAction('Move Source Up'):
            return

        s = self.stored['SelectedSource']['index']
        if s > 0:
            source = self.stored['Sources'].pop(s)
            self.stored['Sources'].insert(s - 1, source)
            self.SelectSourceUp()
        self._updateSourceList()

    def MoveSourceDown(self):
        """Move the selected source down one position."""
        if not self._confirmSafetyAction('Move Source Down'):
            return

        s = self.stored['SelectedSource']['index']
        sources = self.stored['Sources']
        if s < len(sources) - 1:
            source = sources.pop(s)
            sources.insert(s + 1, source)
            self.SelectSourceDown()
        self._updateSourceList()

    # -------------------------------------------------------------------------
    # Pulse Parameter Handlers
    # -------------------------------------------------------------------------

    def pulse_Editextension(self):
        """Open the extension script for editing."""
        self.ownerComp.op('Sourcerer').par.edit.pulse()

    def pulse_Import(self):
        """Handle Import pulse parameter."""
        self.Import()

    def pulse_Exportall(self):
        """Handle Export All pulse parameter."""
        self.ExportAll()

    def pulse_Exportselected(self):
        """Handle Export Selected pulse parameter."""
        self.ExportSelected()

    def pulse_Exportrange(self):
        """Handle Export Range pulse parameter."""
        self.ExportRange()

    def pulse_Initdata(self):
        """Handle Init Sources pulse parameter."""
        self.InitData(force_confirm=True)

    def pulse_Clearpendingqueue(self):
        """Handle Clear Pending Queue pulse parameter."""
        self.ClearPendingQueue()