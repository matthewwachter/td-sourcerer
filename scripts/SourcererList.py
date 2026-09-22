"""
SourcererList - List UI component for Sourcerer.

Provides the source list interface with drag-drop reordering,
double-click renaming, and right-click context menu.

Author: Matthew Wachter
License: MIT
"""


class SourcererList:
    """List UI for displaying and managing sources."""

    # Color scheme
    COLORS = {
        'label_bg': (0.125, 0.125, 0.125, 1),
        'label_font': (0.7, 0.7, 0.7, 1),
        'cell_bg': (0.2, 0.2, 0.2, 1),
        'cell_bg_hover': (0.25, 0.25, 0.25, 1),
        'cell_bg_active': (0.3, 0.4, 0.5, 1),
        'cell_bg_active_hover': (0.35, 0.45, 0.55, 1),
        'cell_bg_live': (0.2, 0.35, 0.2, 1),
        'cell_bg_live_hover': (0.25, 0.4, 0.25, 1),
        'cell_bg_live_active': (0.3, 0.5, 0.4, 1),
        'cell_bg_live_active_hover': (0.35, 0.55, 0.45, 1),
        'cell_font': (0.7, 0.7, 0.7, 1),
        'cell_font_hover': (0.85, 0.85, 0.85, 1),
        'cell_font_active': (1.0, 1.0, 1.0, 1),
        'cell_font_active_hover': (1.0, 1.0, 1.0, 1),
        'border_right': (0.1, 0.1, 0.1, 1),
        'border_left': (0.1, 0.1, 0.1, 1),
        'border_top': (0.1, 0.1, 0.1, 1),
        'border_bottom': (0.1, 0.1, 0.1, 1),
        'drag_highlight': (0.2, 0.5, 0.8, 1),
    }

    # Sizes
    CELL_HEIGHT = 24
    CELL_FONT_SIZE = 12
    LABEL_HEIGHT = 24
    LABEL_FONT_SIZE = 12

    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        self.list = ownerComp.op('list')
        self.showIndex = True

        # Drag state
        self.dragRow = False
        self.dropType = None
        self.endRow = None

        # Clipboard
        self.clipboard = None

        # Context menu labels, rebuilt per open (they carry selection counts)
        self.menuLabels = {}

    # -------------------------------------------------------------------------
    # Data Accessors
    # -------------------------------------------------------------------------

    def sourcerer(self):
        """Get Sourcerer operator."""
        return op(self.ownerComp.par.Sourcerer)
    
    def getSourceNames(self):
        """Get list of source names."""
        return op(self.ownerComp.par.Sourcerer).SourceNames

    def getSelection(self):
        """Get the set of selected source indices and the primary index.

        Returns:
            Tuple of (set of selected indices, primary index).
        """
        sourcerer = self.sourcerer()
        return set(sourcerer.SelectedIndices), sourcerer.SelectedSource['index']

    def getSourceName(self, index):
        """Get name of source at index."""
        names = self.getSourceNames()
        if 0 <= index < len(names):
            return names[index]
        return None

    # def getSelectedIndex(self):
    #     """Get selected source index."""
    #     return op(self.ownerComp.par.Sourcerer).SelectedIndex

    # def getActiveName(self):
    #     """Get active source name."""
    #     return op(self.ownerComp.par.Sourcerer).ActiveName

    # def getActiveIndex(self):
    #     """Get active source index."""
    #     return op(self.ownerComp.par.Sourcerer).ActiveIndex

    # -------------------------------------------------------------------------
    # Public Methods
    # -------------------------------------------------------------------------

    def InitData(self):
        """Rebuild list data and refresh display."""
        self.list.par.reset.pulse()

    def Refresh(self):
        """Refresh the list display."""
        self.list.par.reset.pulse()

    # -------------------------------------------------------------------------
    # List Callbacks
    # -------------------------------------------------------------------------

    def onInitCell(self, comp, row, col, attribs):
        """Initialize cell content and appearance."""
        names = self.getSourceNames()
        if not names:
            return

        if col == 0:  # Index column
            attribs.textOffsetX = 0
            attribs.textJustify = JustifyType.CENTER
            attribs.text = '#' if row == 0 else str(row - 1)
        elif col == 1:  # Name column
            attribs.textOffsetX = 6
            attribs.textJustify = JustifyType.CENTERLEFT
            if row == 0:
                attribs.text = 'Sources'
            else:
                attribs.text = names[row - 1]
                attribs.editable = 2
                attribs.help = ('Click to select, ctrl+click to add/remove, shift+click to '
                                'select a range, drag to reorder, double-click to rename')

        attribs.rightBorderOutColor = self.COLORS['border_right']
        attribs.leftBorderOutColor = self.COLORS['border_left']

    def onInitRow(self, comp, row, attribs):
        """Initialize row appearance."""
        if row == 0:
            attribs.bgColor = self.COLORS['label_bg']
            attribs.textColor = self.COLORS['label_font']
            attribs.fontBold = True
            attribs.rowHeight = self.LABEL_HEIGHT
            attribs.fontSizeX = self.LABEL_FONT_SIZE
        else:
            attribs.rowHeight = self.CELL_HEIGHT
            attribs.fontSizeX = self.CELL_FONT_SIZE
            self._resetRowVisuals(comp, row)

    def onInitCol(self, comp, col, attribs):
        """Initialize column widths."""
        if not self.showIndex:
            colWidth = [100]
            stretch = [1]
        else:
            colWidth = [self.CELL_HEIGHT, 100]
            stretch = [0, 1]
        attribs.colWidth = colWidth[col]
        attribs.colStretch = stretch[col]

    def onInitTable(self, comp, attribs):
        """Initialize table settings."""
        attribs.bottomBorderOutColor = self.COLORS['border_bottom']

    def onRollover(self, comp, row, col, coords, prevRow, prevCol, prevCoords):
        """Handle mouse hover effects."""
        names = self.getSourceNames()
        if not names:
            return

        selected, _ = self.getSelection()
        active_index = self.sourcerer().ActiveSource['index']

        # Apply hover to current row
        if row is not None and row > 0 and row != prevRow:
            source_index = row - 1
            is_selected = (source_index in selected)
            is_active = (source_index == active_index)
            rowAttribs = comp.rowAttribs[row]

            if is_selected:
                rowAttribs.bgColor = self.COLORS['cell_bg_live_active_hover'] if is_active else self.COLORS['cell_bg_active_hover']
                rowAttribs.textColor = self.COLORS['cell_font_active_hover']
            else:
                rowAttribs.bgColor = self.COLORS['cell_bg_live_hover'] if is_active else self.COLORS['cell_bg_hover']
                rowAttribs.textColor = self.COLORS['cell_font_hover']

        # Reset previous row
        if prevRow is not None and prevRow > 0 and row != prevRow:
            source_index = prevRow - 1
            is_selected = (source_index in selected)
            is_active = (source_index == active_index)
            prevRowAttribs = comp.rowAttribs[prevRow]

            if is_selected:
                prevRowAttribs.bgColor = self.COLORS['cell_bg_live_active'] if is_active else self.COLORS['cell_bg_active']
                prevRowAttribs.textColor = self.COLORS['cell_font_active']
            else:
                prevRowAttribs.bgColor = self.COLORS['cell_bg_live'] if is_active else self.COLORS['cell_bg']
                prevRowAttribs.textColor = self.COLORS['cell_font']

    def onSelect(self, comp, startRow, startCol, startCoords, endRow, endCol, endCoords, start, end):
        """Handle selection, drag-drop reordering, and right-click menu."""
        if startRow is None or startRow <= 0:
            return

        source_index = startRow - 1
        names = self.getSourceNames()
        if not names:
            return

        # Left click - select and begin drag
        if start and comp.panel.lselect:
            ctrl = bool(comp.panel.ctrl)
            shift = bool(comp.panel.shift)

            op(self.ownerComp.par.Sourcerer).SelectSource(
                source_index, additive=ctrl, extend=shift
            )

            # Drag-to-reorder moves a single row, so it only arms on a plain
            # click. Dragging during a ctrl/shift click would fight the
            # selection the user is building.
            if not ctrl and not shift:
                self.dragRow = True
                self.endRow = startRow

        # Right click - context menu
        elif start and comp.panel.rselect:
            # Right-clicking inside an existing multi-selection keeps it, so
            # the menu can act on the whole set (Explorer behaviour).
            selected, _ = self.getSelection()
            if source_index not in selected:
                op(self.ownerComp.par.Sourcerer).SelectSource(source_index)
            self._openContextMenu(source_index)

        # Drag end - complete move
        elif end and self.dragRow:
            self.dragRow = False
            did_move = False

            if startRow != endRow and endRow is not None:
                from_index = startRow - 1
                num_sources = len(names)

                if endRow == 0:
                    op(self.ownerComp.par.Sourcerer).MoveSource(from_index, 0)
                    did_move = True
                elif endRow == -1:
                    op(self.ownerComp.par.Sourcerer).MoveSource(from_index, num_sources)
                    did_move = True
                elif endRow > 0:
                    to_index = endRow - 1
                    if self.dropType == 'above':
                        op(self.ownerComp.par.Sourcerer).MoveSource(from_index, to_index)
                        did_move = True
                    elif self.dropType == 'below':
                        op(self.ownerComp.par.Sourcerer).MoveSource(from_index, to_index + 1)
                        did_move = True

            # Reset visuals
            if self.endRow is not None:
                if self.endRow == 0:
                    comp.rowAttribs[0].bottomBorderOutColor = self.COLORS['border_bottom']
                elif self.endRow == -1:
                    lastRow = len(names)
                    if lastRow > 0:
                        self._resetRowVisuals(comp, lastRow)
                elif self.endRow > 0:
                    self._resetRowVisuals(comp, self.endRow)

            self.dropType = None
            self.endRow = None

            if did_move:
                self.InitData()

        # During drag - show drop indicator
        elif not start and not end and self.dragRow:
            if endRow is not None and startRow != endRow:
                num_sources = len(names)
                lastRow = num_sources

                if endRow == 0:
                    comp.rowAttribs[endRow].bottomBorderOutColor = self.COLORS['drag_highlight']
                    self.dropType = 'header'
                elif endRow == -1 and lastRow > 0:
                    comp.rowAttribs[lastRow].bottomBorderOutColor = self.COLORS['drag_highlight']
                    self.dropType = 'end'
                elif endRow > 0:
                    rowAttribs = comp.rowAttribs[endRow]
                    if endCoords.v > 0.5:
                        rowAttribs.topBorderOutColor = self.COLORS['drag_highlight']
                        rowAttribs.bottomBorderOutColor = self.COLORS['border_bottom']
                        self.dropType = 'above'
                    else:
                        rowAttribs.bottomBorderOutColor = self.COLORS['drag_highlight']
                        rowAttribs.topBorderOutColor = self.COLORS['border_top']
                        self.dropType = 'below'

                # Reset previous row
                if self.endRow != endRow and self.endRow is not None:
                    if self.endRow == 0:
                        comp.rowAttribs[0].bottomBorderOutColor = self.COLORS['border_bottom']
                    elif self.endRow == -1 and lastRow > 0:
                        self._resetRowVisuals(comp, lastRow)
                    elif self.endRow > 0:
                        self._resetRowVisuals(comp, self.endRow)

                self.endRow = endRow

    def _resetRowVisuals(self, comp, row):
        """Reset row visuals based on selected/live state."""
        if row <= 0:
            return

        names = self.getSourceNames()
        if not names or row - 1 >= len(names):
            return

        rowAttribs = comp.rowAttribs[row]
        rowAttribs.topBorderOutColor = self.COLORS['border_top']
        rowAttribs.bottomBorderOutColor = self.COLORS['border_bottom']

        source_index = row - 1
        selected, primary = self.getSelection()
        active_index = self.sourcerer().ActiveSource['index']
        is_selected = (source_index in selected)
        is_active = (source_index == active_index)

        if is_selected:
            # Bold marks the primary row - the one whose values the parameter
            # panel is showing and editing from.
            rowAttribs.fontBold = (source_index == primary)
            rowAttribs.textColor = self.COLORS['cell_font_active']
            rowAttribs.bgColor = self.COLORS['cell_bg_live_active'] if is_active else self.COLORS['cell_bg_active']
        elif is_active:
            rowAttribs.fontBold = False
            rowAttribs.textColor = self.COLORS['cell_font']
            rowAttribs.bgColor = self.COLORS['cell_bg_live']
        else:
            rowAttribs.fontBold = False
            rowAttribs.textColor = self.COLORS['cell_font']
            rowAttribs.bgColor = self.COLORS['cell_bg']

    def _openContextMenu(self, source_index):
        """Open right-click context menu."""
        count = len(self.getSelection()[0])

        # Delete and Export act on the whole selection, so say how many when
        # that is more than the row under the cursor.
        self.menuLabels = {
            'Delete': f'Delete ({count})' if count > 1 else 'Delete',
            'Export Selected': f'Export Selected ({count})' if count > 1 else 'Export Selected',
        }

        items = ['Take', 'Copy', 'Paste',
                 self.menuLabels['Delete'], 'Import',
                 self.menuLabels['Export Selected'], 'Export All']
        disabled = [] if self.clipboard else ['Paste']

        op.TDResources.op('popMenu').Open(
            items=items,
            callback=self._onContextMenuSelect,
            callbackDetails={'source_index': source_index},
            disabledItems=disabled,
            dividersAfterItems=[self.menuLabels['Delete']],
        )

    def _onContextMenuSelect(self, info):
        """Handle context menu selection."""
        action = info['item']
        source_index = info['details']['source_index']
        sourcerer = op(self.ownerComp.par.Sourcerer)

        # Map the possibly count-suffixed labels back to their actions.
        labels = getattr(self, 'menuLabels', {})
        for base, label in labels.items():
            if action == label:
                action = base
                break

        if action == 'Take':
            sourcerer.Take(source_index)
        elif action == 'Copy':
            self.clipboard = sourcerer.CopySourceData(source_index)
        elif action == 'Paste' and self.clipboard:
            sourcerer.PasteSourceData(source_index, self.clipboard)
        elif action == 'Delete':
            sourcerer.DeleteSource()
        elif action == 'Import':
            sourcerer.Import()
        elif action == 'Export Selected':
            sourcerer.ExportSelected()
        elif action == 'Export All':
            sourcerer.ExportAll()

    def onRadio(self, comp, row, col, prevRow, prevCol):
        """Radio button callback (unused)."""
        pass

    def onFocus(self, comp, row, col, prevRow, prevCol):
        """Focus callback (unused)."""
        pass

    def onEdit(self, comp, row, col, val):
        """Handle inline rename."""
        if row > 0:
            op(self.ownerComp.par.Sourcerer).RenameSource(row - 1, val)

    def onDragHover(self, comp, info):
        """Accept file and TOP drops."""
        dragItems = info.get('dragItems', [])
        for item in dragItems:
            if isinstance(item, str):
                return True
            elif hasattr(item, 'OPType') and item.OPType == 'TOP':
                return True
        return True

    def onDrop(self, comp, info):
        """Handle dropped files/TOPs."""
        op(self.ownerComp.par.Sourcerer).DropSource(info.get('dragItems', []))
        return {'droppedOn': comp}
