# Changelog

## [2.1.0] - 2026-09-22

### Added
- **Multi-selection** - Select multiple sources in the list with Windows Explorer semantics: click selects one, Ctrl toggles, Shift selects a range from the anchor. The primary source is shown bold and drives the parameter panel
- **Parameter broadcast** - Editing a parameter applies the value to every selected source, tuplets included (`Name` is excluded so names stay unique)
- **Selection API** - `SelectedIndices` property, `IsSelected()`, and `SelectSource(index, additive=False, extend=False)`
- **Loop Playlist toggle** - New setting on the Sourcerer Settings page. When on, a Play Next follow action on the last source wraps to the first. Off by default
- **TakeNext / TakePrevious** - Methods for sequential switching relative to the active source, with optional wrap-around (`wrap=True` by default)

### Changed
- Delete and Export Selected now act on the whole selection. Delete always leaves at least one source
- Reordering collapses the selection to the moved row
- The Play Next follow action now uses `TakeNext()`, so the script and follow-action paths behave the same way

### Fixed
- Play Next on the last source no longer calls `Take()` with an out-of-range index
- The Next display property and the early-trigger transition time now respect Loop Playlist
- Embedded copies of `scripts/*.py` in `sourcerer.tox` had drifted behind the files on disk

## [2.0.5] - 2025-01-30

### Fixed
- Fixed export issue. Added .getRaw().

## [2.0.4] - 2025-01-29

### Fixed
- Fixed log clear button inverted display logic

## [2.0.3] - 2025-01-29

### Fixed
- Renamed Trigger to Take in right click context menu
- Flipped order of luma matte lookup on file and top transitions

## [2.0.2] - 2025-01-29

### Fixed
- Fixed issue with luma matte lookup on file and top transitions

## [2.0.1] - 2025-01-28

### Fixed
- onSwitchToSource callback renamed to onTake.
- Changed CopySourceData to return dict rather than DependDict

## [2.0.0] - 2025-01-28

### Added
- **SourcererGrid component** - New touch-friendly grid UI for source selection with pagination and scrollbar overflow modes
- **Temp source support** - Switch to temporary sources without modifying the source list
- **CHOP done validation** - Follow actions only trigger when done-on parameter matches 'chop'
- **Display properties** - `ActiveSource`, `SelectedSource`, `PendingSource` dictionaries with name/index/op
- **Minimized status view** - Compact log display option
- **Source CHOP outputs** - CHOP channels for source state monitoring
- **Context menu** - Right-click menu with Copy, Paste, Delete, Import, Export options
- **Drag-drop reordering** - Reorder sources by dragging in the list

### Changed
- **Transition system overhaul** - Complete rewrite using state machine architecture
- **List system rewrite** - Externalized list component with improved styling and interactions
- **Follow actions** - Improved handling and validation
- **Parameter storage** - Cleaner parameter storing and retrieval

### Fixed
- Blur transition not working correctly
- GLSL transition fade colors
- Pending queue display issues
- Sources with 0 transition time not transitioning
- Play N times logic
- Switching bug in newer TD versions
- Dependency issues with component initialization
- Panels closing on reload

## [1.0.0] - 2019-12-19 - Initial Release

### Added
- Core source management (add, delete, rename, reorder)
- Multiple source types (Movie File, Image File, TOP)
- Transition system with GLSL shader effects (Dissolve, Dip, Slide, Wipe, Blur, File, Top)
- Follow actions (None, Stop, Loop, Next, Previous, Random, First, Last)
- Done conditions (Timer, Play N Times, CHOP)
- Import/Export sources as JSON
- Callbacks for source events
