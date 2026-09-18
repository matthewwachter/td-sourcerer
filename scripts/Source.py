"""
Source - Media source playback component for Sourcerer.

Handles playback of file-based and TOP-based sources with follow actions,
display properties, and transition timing calculations.

Author: Matthew Wachter
License: MIT
"""

import traceback

from CallbacksExt import CallbacksExt
from TDStoreTools import StorageManager
import TDFunctions as TDF


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


class Source(CallbacksExt):
    """
    Source playback component extension.

    Manages playback state, display properties (timecode, progress, etc.),
    follow actions, and done conditions for individual media sources.
    """

    def __init__(self, ownerComp):
        self.ownerComp = ownerComp

        # Initialize callbacks
        self.callbackDat = self.ownerComp.par.Callbackdat.eval()
        try:
            CallbacksExt.__init__(self, ownerComp)
        except:
            self.ownerComp.addScriptError(
                traceback.format_exc() + "Error in CallbacksExt __init__. See textport."
            )
            print()
            print("Error initializing callbacks - " + self.ownerComp.path)
            print(traceback.format_exc())

        try:
            self.DoCallback('onInit', {'ownerComp': self.ownerComp})
        except:
            self.ownerComp.addScriptError(
                traceback.format_exc() + "Error in custom onInit callback. See textport."
            )
            print(traceback.format_exc())

        # Storage setup
        self.dataComp = ownerComp.op('data')
        storedItems = [
            {'name': 'Data', 'default': None, 'readOnly': False,
             'property': True, 'dependable': True},
        ]
        self.stored = StorageManager(self, self.dataComp, storedItems)

        # Operator references
        self.movieFileIn = self.ownerComp.op('moviefilein')
        self.doneTimer = self.ownerComp.op('doneTimer')

        # State flags
        self._isUpdating = False
        self._doneTriggered = False

        # File playback state
        self._currentFrame = 0
        self._totalFrames = 0
        self._sampleRate = 30.0
        self._lastFrameState = 0
        self._loopCount = 0
        self._loopsRemaining = 0

        # Timer state
        self._timerProgress = 0.0
        self._timerLengthSeconds = 0.0
        self._timerTimeRemaining = 0.0

        # Display properties (dependable for reactive UI)
        TDF.createProperty(self, 'Timecode', value='N/A', dependable=True, readOnly=False)
        TDF.createProperty(self, 'TimeRemaining', value='N/A', dependable=True, readOnly=False)
        TDF.createProperty(self, 'LoopCount', value='N/A', dependable=True, readOnly=False)
        TDF.createProperty(self, 'LoopsRemaining', value='N/A', dependable=True, readOnly=False)
        TDF.createProperty(self, 'Progress', value='N/A', dependable=True, readOnly=False)
        TDF.createProperty(self, 'Next', value='N/A', dependable=True, readOnly=False)

    def _formatTimecode(self, frames, fps):
        """Format frame count as timecode string HH:MM:SS:FF"""
        if fps <= 0:
            return '00:00:00:00'
        total_seconds = frames / fps
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        frame = int(frames % fps)
        return f'{hours:02d}:{minutes:02d}:{seconds:02d}:{frame:02d}'

    def _getTransitionTimeForFollowAction(self):
        """Get the transition time (in seconds) for the follow action target."""
        follow_action = str(self.ownerComp.par.Followactionfile)
        if follow_action == FollowAction.NONE:
            return 0.0

        target_source = None
        current_index = int(self.ownerComp.par.Index)

        if follow_action == FollowAction.PLAY_NEXT:
            next_index = current_index + 1
            if next_index < len(ext.SOURCERER.Sources):
                target_source = ext.SOURCERER.Sources[next_index]
        elif follow_action == FollowAction.GOTO_INDEX:
            goto_index = int(self.ownerComp.par.Gotoindexfile)
            if 0 <= goto_index < len(ext.SOURCERER.Sources):
                target_source = ext.SOURCERER.Sources[goto_index]
        elif follow_action == FollowAction.GOTO_NAME:
            goto_name = str(self.ownerComp.par.Gotonamefile)
            source_data, idx, name = ext.SOURCERER._getSource(goto_name)
            target_source = source_data

        if target_source is None:
            return 0.0

        settings = target_source.get('Settings', {})
        if settings.get('Useglobaltransitiontime', False):
            return float(parent.SOURCERER.par.Globaltransitiontime)
        return float(settings.get('Transitiontime', 0.0))

    def _getNextSourceDisplay(self):
        """Get display name for the next source based on follow action."""
        source_type = str(self.ownerComp.par.Sourcetype)

        if source_type == SourceType.FILE:
            follow_action = str(self.ownerComp.par.Followactionfile)
        elif source_type == SourceType.TOP:
            follow_action = str(self.ownerComp.par.Followactiontop)
        else:
            return 'N/A'

        if follow_action == FollowAction.NONE:
            return 'N/A'

        current_index = int(self.ownerComp.par.Index)
        target_index = None
        target_name = None

        if follow_action == FollowAction.PLAY_NEXT:
            next_index = current_index + 1
            if next_index < len(ext.SOURCERER.Sources):
                target_index = next_index
                target_source = ext.SOURCERER.Sources[next_index]
                target_name = target_source.get('Settings', {}).get('Name', '')
        elif follow_action == FollowAction.GOTO_INDEX:
            if source_type == SourceType.FILE:
                goto_index = int(self.ownerComp.par.Gotoindexfile)
            else:
                goto_index = int(self.ownerComp.par.Gotoindextop)
            if 0 <= goto_index < len(ext.SOURCERER.Sources):
                target_index = goto_index
                target_source = ext.SOURCERER.Sources[goto_index]
                target_name = target_source.get('Settings', {}).get('Name', '')
        elif follow_action == FollowAction.GOTO_NAME:
            if source_type == SourceType.FILE:
                goto_name = str(self.ownerComp.par.Gotonamefile)
            else:
                goto_name = str(self.ownerComp.par.Gotonametop)
            source_data, idx, name = ext.SOURCERER._getSource(goto_name)
            if source_data is not None:
                target_index = idx
                target_name = name

        if target_index is None:
            return 'N/A'
        return f'{target_name}'

    def _formatSeconds(self, seconds):
        """Format seconds as timecode string HH:MM:SS:FF (assuming 30fps for frame display)."""
        if seconds <= 0:
            return '00:00:00:00'
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        # Use fractional seconds for frame portion (display at 30fps equivalent)
        frame = int((seconds % 1) * 30)
        return f'{hours:02d}:{minutes:02d}:{secs:02d}:{frame:02d}'

    def _updateDisplayState(self):
        """Update display properties based on source type and done condition."""
        if not parent.SOURCERER.par.Updatedisplay:
            return

        source_type = str(self.ownerComp.par.Sourcetype)
        if source_type == SourceType.FILE:
            self._updateFileDisplay(str(self.ownerComp.par.Doneonfile))
        elif source_type == SourceType.TOP:
            self._updateTopDisplay(str(self.ownerComp.par.Doneontop))
        else:
            self._setAllDisplayNA()

    def _updateFileDisplay(self, done_on):
        """Update display properties for file source type."""
        self.Timecode = self._formatTimecode(self._currentFrame, self._sampleRate)
        self.LoopCount = self._loopCount
        self.Next = self._getNextSourceDisplay()

        if done_on == DoneOn.PLAY_N_TIMES:
            play_n_times = int(self.ownerComp.par.Playntimes)
            total_frames_all_loops = self._totalFrames * play_n_times
            frames_completed = (self._loopCount * self._totalFrames) + self._currentFrame

            if total_frames_all_loops > 1:
                progress_pct = (frames_completed / (total_frames_all_loops - 1)) * 100
            else:
                progress_pct = 100.0 if total_frames_all_loops == 1 else 0.0
            self.Progress = round(progress_pct, 2)

            frames_remaining_current = max(0, self._totalFrames - 1 - self._currentFrame)
            frames_remaining_future = self._loopsRemaining * self._totalFrames
            total_frames_remaining = frames_remaining_current + frames_remaining_future
            self.TimeRemaining = self._formatTimecode(total_frames_remaining, self._sampleRate)
            self.LoopsRemaining = self._loopsRemaining

        elif done_on == DoneOn.TIMER:
            self.Progress = round(self._timerProgress * 100, 2)
            self.TimeRemaining = self._formatSeconds(self._timerTimeRemaining)
            self.LoopsRemaining = 'N/A'

        else:  # 'none' or manual
            if self._totalFrames > 1:
                progress_pct = (self._currentFrame / (self._totalFrames - 1)) * 100
            else:
                progress_pct = 100.0 if self._totalFrames == 1 else 0.0
            self.Progress = round(progress_pct, 2)

            frames_remaining = max(0, self._totalFrames - 1 - self._currentFrame)
            self.TimeRemaining = self._formatTimecode(frames_remaining, self._sampleRate)
            self.LoopsRemaining = 'N/A'

    def _updateTopDisplay(self, done_on):
        """Update display properties for TOP source type."""
        self.LoopCount = 'N/A'
        self.LoopsRemaining = 'N/A'
        self.Next = self._getNextSourceDisplay()

        if done_on == DoneOn.TIMER:
            self.Progress = round(self._timerProgress * 100, 2)
            self.TimeRemaining = self._formatSeconds(self._timerTimeRemaining)
            self.Timecode = self._formatSeconds(self._timerLengthSeconds * self._timerProgress)
        else:  # 'none' or manual
            self.Progress = 'N/A'
            self.TimeRemaining = 'N/A'
            self.Timecode = 'N/A'

    def _setAllDisplayNA(self):
        """Set all display properties to N/A."""
        self.Timecode = 'N/A'
        self.TimeRemaining = 'N/A'
        self.Progress = 'N/A'
        self.LoopCount = 'N/A'
        self.LoopsRemaining = 'N/A'
        self.Next = 'N/A'

    def whileDoneTimerActive(self, fraction):
        """Timer callback - updates progress and display."""
        self._timerProgress = float(fraction)
        self._timerTimeRemaining = self._timerLengthSeconds * (1.0 - self._timerProgress)
        self._updateDisplayState()

    def UpdateFromData(self, source_data, active=False, store_changes=False, index=None):
        """Update component from a source data dictionary.

        Args:
            source_data: Dictionary of {page_name: {par_name: value}}
            active: Whether this source is actively playing
            store_changes: Whether to store parameter changes back to Sourcerer
            index: The source index this component represents
        """
        self._isUpdating = True

        for page_name, page_data in source_data.items():
            for par_name, value in page_data.items():
                ext.SOURCERER._setParVal(par_name, value, self.ownerComp)

        self.ownerComp.par.Storechanges = store_changes
        self.ownerComp.par.Active = active
        if index is not None:
            self.ownerComp.par.Index = index

        self._isUpdating = False

        run(self.UpdateFileInfo, delayFrames=1)

        if active:
            if self.ownerComp.par.Enablecommand:
                try:
                    run(str(self.ownerComp.par.Command))
                except Exception as e:
                    ext.SOURCERER._log('CommandError', {'error': str(e), 'command': str(self.ownerComp.par.Command)}, level='ERROR')
            if self.ownerComp.par.Enablecuetop:
                try:
                    op(self.ownerComp.par.Cuetop).par.cue.pulse()
                except Exception as e:
                    ext.SOURCERER._log('CueTOPError', {'error': str(e), 'top': str(self.ownerComp.par.Cuetop)}, level='ERROR')

    def UpdateFileInfo(self):
        """Update file length and rate from the movieFileIn operator."""
        source_type = str(self.ownerComp.par.Sourcetype)
        if source_type != 'file':
            return

        num_frames = int(self.movieFileIn.numImages)
        if num_frames > 0:
            self.ownerComp.par.Filelengthframes = num_frames
            self._totalFrames = num_frames
            sample_rate = float(self.movieFileIn.rate) if self.movieFileIn.rate > 0 else 30.0
            self.ownerComp.par.Filesamplerate = sample_rate
            self._sampleRate = sample_rate

    def Start(self):
        """Reset playback state and start the source."""
        self._doneTriggered = False
        self._lastFrameState = 0
        self._currentFrame = 0
        self._timerProgress = 0.0
        self._timerTimeRemaining = self._timerLengthSeconds
        self._loopCount = 0
        self._loopsRemaining = max(0, int(self.ownerComp.par.Playntimes) - 1)

        self._updateDisplayState()

        source_type = str(self.ownerComp.par.Sourcetype)
        if source_type == SourceType.FILE:
            self.movieFileIn.par.reload.pulse()
            done_on = self.ownerComp.par.Doneonfile.eval()
            if done_on == DoneOn.TIMER and self.doneTimer is not None:
                self._timerLengthSeconds = float(self.ownerComp.par.Timertimefile)
                self._timerTimeRemaining = self._timerLengthSeconds
                self.doneTimer.par.initialize.pulse()
                run(self.doneTimer.par.start.pulse, delayFrames=1)
        elif source_type == SourceType.TOP:
            done_on = self.ownerComp.par.Doneontop.eval()
            if done_on == DoneOn.TIMER and self.doneTimer is not None:
                self._timerLengthSeconds = float(self.ownerComp.par.Timertimetop)
                self._timerTimeRemaining = self._timerLengthSeconds
                self.doneTimer.par.initialize.pulse()
                run(self.doneTimer.par.start.pulse, delayFrames=1)

            if self.ownerComp.par.Enablecuetop.eval():
                vid = self.ownerComp.par.Cuetop.eval()
                op(vid).par.cuepulse.pulse()

    def _handleFollowAction(self):
        """Handle follow action when source is done playing."""
        source_type = str(self.ownerComp.par.Sourcetype)
        if source_type == SourceType.FILE:
            follow_action = self.ownerComp.par.Followactionfile
        elif source_type == SourceType.TOP:
            follow_action = self.ownerComp.par.Followactiontop
        else:
            return

        if not self.ownerComp.par.Active:
            return
        if self.ownerComp.name not in ['source0', 'source1']:
            return
        if self.ownerComp.digits != ext.SOURCERER.State:
            return

        ext.SOURCERER.OnSourceDone()

        if follow_action == FollowAction.PLAY_NEXT:
            # Defers to TakeNext so the end of the list is handled in one place:
            # with Loop Playlist off it stops here, with it on it wraps to the
            # first source.
            ext.SOURCERER.TakeNext(wrap=ext.SOURCERER.isLoopingPlaylist)
        elif follow_action == FollowAction.GOTO_INDEX:
            if source_type == SourceType.FILE:
                goto_index = self.ownerComp.par.Gotoindexfile
            else:
                goto_index = self.ownerComp.par.Gotoindextop
            ext.SOURCERER.Take(int(goto_index))
        elif follow_action == FollowAction.GOTO_NAME:
            if source_type == SourceType.FILE:
                goto_name = self.ownerComp.par.Gotonamefile
            else:
                goto_name = self.ownerComp.par.Gotonametop
            ext.SOURCERER.Take(str(goto_name))

    def onValueChange(self, par, prev):
        """Callback for parameter value changes."""
        if self._isUpdating:
            return

        if par.name == 'File' and par.val != prev:
            run(self.UpdateFileInfo, delayFrames=1)

        if not self.ownerComp.par.Storechanges:
            return
        ext.SOURCERER.StoreParToSelected(par)

    def onFileValueChange(self, channel, val):
        """Callback for file info CHOP channel changes."""
        chan_name = channel.name

        # File ready - update info
        if chan_name in ('open', 'preloading'):
            if val == 1.0:
                num_frames = int(self.movieFileIn.numImages)
                self.ownerComp.par.Filelengthframes = num_frames
                self._totalFrames = num_frames
                sample_rate = float(self.movieFileIn.rate) if self.movieFileIn.rate > 0 else 30.0
                self.ownerComp.par.Filesamplerate = sample_rate
                self._sampleRate = sample_rate
            return

        # Log file open failures
        if chan_name == 'open_failed':
            if val == 1.0:
                ext.SOURCERER._log(
                    'FileOpenFailed',
                    {
                        'index': int(self.ownerComp.par.Index),
                        'name': str(self.ownerComp.par.Name),
                        'file': str(self.ownerComp.par.File)
                    },
                    level='ERROR'
                )
            return

        # Playback updates only for active source
        is_active_playback = (
            self.ownerComp.par.Active and
            self.ownerComp.name in ['source0', 'source1'] and
            self.ownerComp.digits == ext.SOURCERER.State
        )
        if not is_active_playback:
            return

        if chan_name == 'index':
            self._currentFrame = int(val)
        elif chan_name == 'length':
            self._totalFrames = int(val)
        elif chan_name == 'sample_rate':
            self._sampleRate = float(val) if val > 0 else 30.0
        elif chan_name == 'last_frame':
            # Rising edge detection for loop counting
            if val == 1.0 and self._lastFrameState == 0:
                done_on = str(self.ownerComp.par.Doneonfile)
                play_n_times = int(self.ownerComp.par.Playntimes)

                self._loopCount += 1
                self._loopsRemaining = max(0, play_n_times - self._loopCount)

                if done_on == DoneOn.PLAY_N_TIMES and not self._doneTriggered:
                    if self._loopCount >= play_n_times:
                        self._doneTriggered = True
                        self._handleFollowAction()

            self._lastFrameState = val

        self._updateDisplayState()

        # Early transition trigger (only on index changes in play_n_times mode)
        if chan_name != 'index':
            return

        done_on = str(self.ownerComp.par.Doneonfile)
        if done_on != 'play_n_times' or self._doneTriggered:
            return

        play_n_times = int(self.ownerComp.par.Playntimes)
        transition_time = self._getTransitionTimeForFollowAction()
        if transition_time <= 0:
            return

        transition_frames = transition_time * self._sampleRate
        frames_remaining = max(0, self._totalFrames - 1 - self._currentFrame)
        is_final_loop = (self._loopCount >= play_n_times - 1)

        if is_final_loop and frames_remaining > 0 and frames_remaining <= transition_frames:
            self._doneTriggered = True
            self._handleFollowAction()
    
    def onDoneTimerDone(self):
        """Callback for timer completion."""
        self._handleFollowAction()

    def onDoneCHOPFile(self):
        """Callback for done CHOP completion for file source."""
        if str(self.ownerComp.par.Doneonfile) == DoneOn.CHOP:
            self._handleFollowAction()

    def onDoneCHOPTop(self):
        """Callback for done CHOP completion for TOP source."""
        if str(self.ownerComp.par.Doneontop) == DoneOn.CHOP:
            self._handleFollowAction()

    # -------------------------------------------------------------------------
    # Pulse Parameter Handlers
    # -------------------------------------------------------------------------

    def pulse_Cuepulse(self):
        """Cue the movie file in."""
        self.ownerComp.op('moviefilein').par.cuepulse.pulse()

    def pulse_Commandpulse(self):
        """Execute the command script."""
        run(str(self.ownerComp.par.Command), fromOP=parent.SOURCERER)

    def pulse_Donepulsefile(self):
        """Trigger done for file source."""
        self._handleFollowAction()

    def pulse_Commandpulsetop(self):
        """Trigger done for TOP source."""
        self._handleFollowAction()

    def pulse_Editextension(self):
        """Open extension for editing."""
        self.ownerComp.op('Source').par.edit.pulse()
