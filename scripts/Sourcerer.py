# Author: Matthew Wachter
# License: MIT

import json
import os
from TDStoreTools import StorageManager, DependList
TDJSON = op.TDModules.mod.TDJSON


class Sourcerer:
    def __init__(self, ownerComp):
        # The component to which this extension is attached
        self.ownerComp = ownerComp
        self.DataComp = ownerComp.op('data')
        self.transitionComp = ownerComp.op('transitions')
        self.switcherState = ownerComp.op('state')
        self.selectedSourceComp = ownerComp.op('selectedSource')
        self.extraAttrs = [
            'val',
            'order',
            'mode',
            'startSection',
            'expr',
            'enable'
        ]

        storedItems = [
            {'name': 'Sources', 'default': [], 'dependable': False},
            {'name': 'SourceList', 'default': [], 'dependable': True},
            {'name': 'SelectedSource', 'default': 0, 'dependable': True},
            {
                'name': 'ActiveSource',
                'default': {'index': 0, 'name': ''},
                'dependable': True
            },
            {'name': 'State', 'default': 0, 'dependable': True}
        ]

        self.stored = StorageManager(self, self.DataComp, storedItems)
        self._updateSourceList()

    def _updateSourceList(self):
        source_list = [str(s['Settings']['Name']['val']) for s in self.stored['Sources']]
        self.stored['SourceList'] = source_list
        #self.ownerComp.op('UI/_ui_list').par.reset.pulse()

    def _getSource(self, source):
        source_json = None
        name = None
        index = None

        if isinstance(source, str):
            sources = self.stored['Sources']
            source_names = [
                self._getParVal(s['Settings']['Name']) for s in sources
            ]
            if source in source_names:
                s = source_names.index(source)
                source_json = self.stored['Sources'][s]
                name = source
                index = s
            else:
                print('no source', source, 'in', source_names)

        elif isinstance(source, int):
            s = source
            index = source
            source_json = self.stored['Sources'][s]
            if source <= len(self.stored['Sources'])-1:
                name = self._getParVal(source_json['Settings']['Name'])
            else:
                print('source index', s, 'is out of range')

        else:
            print('wrong source type', source)

        return source_json, index, name

    def SwitchToSource(self, source):
        state = self.stored['State']
        next_state = 1-state

        source_comp = self.ownerComp.op('source' + str(next_state))

        source, index, name = self._getSource(source)

        # update the source comp
        self.UpdateSourceCompQuick(source_comp, index)

        # set the timers and reload the movie
        source_type = self._getParVal(source['Settings']['Sourcetype'])

        source_comp.op('count1').par.resetpulse.pulse()
        source_comp.op('timerFile').par.initialize.pulse()
        source_comp.op('timerTOP').par.initialize.pulse()

        if source_type == 'file':
            source_comp.op('moviefilein0').par.reloadpulse.pulse()

            done_on = self._getParVal(source['File']['Doneonfile'])
            if done_on == 'timer':
                source_comp.op('startTimerFile').run(delayFrames=1)

        else:
            done_on = self._getParVal(source['TOP']['Doneontop'])
            if done_on == 'timer':
                source_comp.op('startTimerTOP').run(delayFrames=1)

            cue_vid = self._getParVal(source['TOP']['Enablecuetop'])

            if cue_vid:
                vid = self._getParVal(source['TOP']['Cuetop'])
                op(vid).par.cuepulse.pulse()

        # set the transition
        settings = source['Settings']
        tcomp_par = self.transitionComp.par

        trans_type = self._getParVal(settings['Transitiontype'])
        tcomp_par.Transitiontype = trans_type

        if trans_type == 'glsl':
            glsl_trans = self._getParVal(settings['Glsltransition'])
            tcomp_par.Glsltransition = glsl_trans

            glsl_transitions = {
                'Blinds': ['Blindsnum'],
                'Blood': ['Seed'],
                'Circle Reveal': ['Circlerevealfuzzy'],
                'Color Burn': ['Colorburncolor'],
                'Color Distance': ['Colordistancepower'],
                'Cube Left': ['Cubeperspective', 'Cubeunzoom'],
                'Cube Right': ['Cubeperspective', 'Cubeunzoom'],
                'Dissolve': ['Seed'],
                'Fade Color': ['Fadecolor'],
                'Linear Blur': ['Linearblurintensity', 'Linearblurpasses'],
                'Maximum': ['Maximumdistance', 'Maximumfadeindistance'],
                'Morph1': ['Morph1strength'],
                'Perlin': ['Perlinscale', 'Seed', 'Perlinsmoothness'],
                'Pixelize': ['Pixelizesquaresmin'],
                'Radial Blur': ['Radialblurcenter'],
                'Random Squares': ['Randomsquaressize', 'Randomsquaressmoothness'],
                'Ripple': ['Rippleamplitude', 'Ripplecenter', 'Ripplefrequency', 'Ripplespeed'],
                'Slide': ['Slidedirection'],
                'Swap Left': ['Swapperspective', 'Swapdepth'],
                'Swap Right': ['Swapperspective', 'Swapdepth']
            }
            # print(glsl_trans)
            if glsl_trans in glsl_transitions.keys():
                transition_pars = glsl_transitions[glsl_trans]
                for p in transition_pars:
                    self._setParVal(source['GLSL Transition'][p], self.transitionComp)

        elif trans_type == 'file':
            tcomp_par.Transitionfile = self._getParVal(settings['Transitionfile'])
        elif trans_type == 'top':
            tcomp_par.Transitiontop = self._getParVal(settings['Transitiontop'])

        # set the transition time
        if self._getParVal(settings['Useglobaltransitiontime']):
            trans_time = self.ownerComp.par.Globaltransitiontime.eval()
        else:
            trans_time = self._getParVal(settings['Transitiontime'])
        tcomp_par.Transitiontime = trans_time

        # set the progress shape
        trans_shape = self._getParVal(settings['Transitionshape'])
        tcomp_par.Transitionshape = trans_shape
        if trans_shape == 'custom':
            tcomp_par.Customtransitionshape = self._getParVal(settings['Customtransitionshape'])

        # update the stored information
        self.stored['State'] = next_state
        self.stored['ActiveSource'] = {
            'index': index,
            'name': name,
            'source': source
        }

        try:
            self.ownerComp.mod.callbacks.onSwitchToSource(index, name, source)
        except Exception as e:
            debug('switch to source callback error')
            debug(e)
        return

    def SwitchToSelectedSource(self):
        s = self.stored['SelectedSource']
        self.SwitchToSource(s)

    def DelaySwitchToSource(self, source, delay=0):
        self.ownerComp.op('delaySwitchToSource').run(source, delayMilliSeconds=delay)

    def RunCommand(self, command):
        self.ownerComp.op('commandScript').text = command
        self.ownerComp.op('commandScript').run(delayFrames=1)

    # SOURCES
    def Import(self):
        f = ui.chooseFile(load=True, fileTypes=['json'], title='Import Sources')

        if f is not None:
            with open(f, 'r') as json_file:
                imported_sources = json.load(json_file)

                if imported_sources:
                    a = ui.messageBox('Sourcerer Import Location', 'Select a location:', buttons=['Prepend', 'Insert (above selected)', 'Append'])

                    sources = []
                    sources.extend(self.stored['Sources'].getRaw())

                    # prepend
                    if a == 0:
                        new_sources = imported_sources.copy()
                        new_sources.extend(sources)
                        self.stored['Sources'] = new_sources

                        for i in range(0, len(imported_sources)):
                            self._checkUniqueName(self.stored['Sources'][i], count=1)

                    # insert
                    elif a == 1:
                        s = self.stored['SelectedSource']
                        new_sources = sources[:s].copy()
                        new_sources.extend(imported_sources)
                        new_sources.extend(sources[s:].copy())
                        self.stored['Sources'] = new_sources

                        for i in range(s, s + len(imported_sources)):
                            self._checkUniqueName(self.stored['Sources'][i], count=1)

                    # append
                    elif a == 2:
                        new_sources = sources.copy()
                        new_sources.extend(imported_sources)
                        self.stored['Sources'] = new_sources

                        for i in range(len(sources), len(new_sources)):
                            self._checkUniqueName(self.stored['Sources'][i], count=1)
                    self._updateSourceList()
        return

    def ExportAll(self):
        f = ui.chooseFile(load=False, fileTypes=['json'], title='Export Sources')

        if f is not None:
            sources = self.stored['Sources'].getRaw()

            with open(f, 'w') as json_file:
                json.dump(sources, json_file)
        return

    def ExportSelected(self):
        f = ui.chooseFile(load=False, fileTypes=['json'], title='Export Sources')

        if f is not None:
            selected_source = self.stored['SelectedSource']
            sources = [self.stored['Sources'][selected_source].getRaw()]

            with open(f, 'w') as json_file:
                json.dump(sources, json_file)
        return

    def ExportRange(self, range_start=None, range_end=None):
        f = ui.chooseFile(load=False, fileTypes=['json'], title='Export Sources')

        if f is not None:
            if range_start is None:
                range_start = self.ownerComp.par.Exportrangeval1
            if range_end is None:
                range_end = self.ownerComp.par.Exportrangeval2

            sources = self.stored['Sources'].getRaw()
            sources = sources[range_start:range_end+1]

            with open(f, 'w') as json_file:
                json.dump(sources, json_file)
        return

    # set the sources to their initial state
    def InitSources(self):
        # clear the sources list
        self.stored['Sources'] = []

        # set the selected source to 0
        self.stored['SelectedSource'] = 0

        # add a default source
        self.AddSource()
        self._updateSourceList()
        return

    # get the desired source template as a JSON op
    def _getSourceTemplate(self, template):
        # get a reference to the template op
        template_op = self.ownerComp.op(template)

        # get  and return a json op of the template
        json_op = TDJSON.opToJSONOp(template_op, extraAttrs=self.extraAttrs, forceAttrLists=False)
        return json_op

    # get a parameter value from a json par
    def _getParVal(self, jsonpar):
        # get the parameter mode
        mode = jsonpar['mode']

        # if the mode is constant, pass the value
        if mode == 'CONSTANT':
            val = jsonpar['val']

        # if the mode is python, evaluate the expression
        elif mode == 'EXPRESSION':
            val = eval(jsonpar['expr'])

        # if the mode is export, get the value
        elif mode == 'EXPORT':
            val = jsonpar['val']

        return val

    def _setParVal(self, p, source_comp):
        size = p.get('size', 1)
        pStyle = p['style']
        pName = p['name']
        # check if we can just replace an already existing parameter
        newPars = None
        # if replace:
        # print(pName, pStyle, size)

        if size > 1 or len(Page.styles[pStyle].suffixes) > 1:
            # special search for multi-value pars
            checkPars = source_comp.pars(pName + '*')

            if checkPars:
                checkPar = checkPars[0]
                if checkPar.tupletName == pName and \
                        checkPar.style == pStyle:
                    newPars = checkPar.tuplet

        elif hasattr(source_comp.par, pName) and \
                getattr(source_comp.par, pName).style == pStyle\
                and len(getattr(source_comp.par, pName).tuplet) == 1:

            newPars = getattr(source_comp.par, pName).tuplet

        pMode = p['mode']
        pEnable = p['enable']

        for index, newPar in enumerate(newPars):

            setattr(newPar, 'enable', pEnable)

            if pMode in ['CONSTANT', 'EXPORT']:
                pValue = p['val']
                if isinstance(pValue, (list, tuple, DependList)):
                    try:
                        setattr(newPar, 'val', pValue[index])
                    except:
                        debug(newPar, 'val', pValue)
                else:
                    try:
                        setattr(newPar, 'val', pValue)
                    except Exception as e:
                        debug(e)
                        print(newPar, 'val', pValue)

            else:
                pExpr = p['expr']
                if isinstance(pExpr, (list, tuple, DependList)):

                    try:
                        setattr(newPar, 'expr', pExpr[index])

                    except:
                        debug(newPar, 'expr', pExpr)
                else:
                    try:
                        setattr(newPar, 'expr', pExpr)
                    except:
                        debug(newPar, 'expr', pExpr)

    # update the source ui comp
    def UpdateSelectedSourceComp(self):
        # get the selected source
        s = self.stored['SelectedSource']

        # update the source comp
        self.UpdateSourceCompQuick(self.selectedSourceComp, s, active=False, store_changes=True)
        return

    def UpdateSourceCompQuick(self, source_comp, source_index, active=True, store_changes=False):
        # disable the callbacks for changing parameters just to be safe
        source_comp.op('parexec1').par.active = False

        # get the source as a json op
        jsonOp = self.stored['Sources'][source_index]

        for page in jsonOp.values():
            for p in page.values():
                self._setParVal(p, source_comp)

        # re-enable parameter change callbacks
        source_comp.op('enable').run(delayFrames = 1)
        source_comp.par.Storechanges = store_changes
        source_comp.par.Active = active
        source_comp.par.Index = source_index

        if active:
            if source_comp.par.Enablecommand:
                try:
                    source_comp.op('command').run()
                except:
                    pass

            if source_comp.par.Enablecuetop:
                try:
                    op(source_comp.par.Cuetop).par.cue.pulse()
                except:
                    pass

        if source_comp.par.Sourcetype.val == 'top':
            source_comp.ext.SOURCE._enableSourceTypeTOP()
        elif source_comp.par.Sourcetype.val == 'file':
            source_comp.ext.SOURCE._enableSourceTypeFile()

    def UpdateSourceComp(self, source_comp, source_index,  active=True, store_changes=False,):
        # disable the callbacks for changing parameters just to be safe
        source_comp.op('parexec1').par.active = False

        # get the source as a json op
        jsonOp = self.stored['Sources'][source_index]

        # update the source comp with the json op data
        newPars = TDJSON.addParametersFromJSONOp(
            source_comp,
            jsonOp,
            replace=True,
            setValues=True,
            destroyOthers=True,
            newAtEnd=False
            #sortByOrder=True
        )

        # re-enable parameter change callbacks
        source_comp.op('enable').run(delayFrames=1)
        source_comp.par.Storechanges = store_changes
        source_comp.par.Active = active
        source_comp.par.Index = source_index

        if active:
            if source_comp.par.Enablecommand:
                try:
                    source_comp.op('command').run()
                except:
                    pass

            if source_comp.par.Enablecuetop:
                try:
                    op(source_comp.par.Cuetop).par.cue.pulse()
                except:
                    pass
        return

    # store the selected source
    def StoreSourceToSelected(self, source_comp, update_selected_comp=False):
        # get the selected source
        source = self.stored['SelectedSource']

        self.StoreSource(source_comp, source)

        if update_selected_comp:
            self.UpdateSelectedSourceComp()
        self._updateSourceList()
        return

    def StoreSource(self, source_comp, source):
        # create a json op from the source comp
        jsonOp = TDJSON.opToJSONOp(source_comp, extraAttrs=self.extraAttrs, forceAttrLists=False)
        # Ensure the jsonOp is JSON-serializable before storing
        try:
            serializable_jsonOp = json.loads(json.dumps(jsonOp))
        except Exception as e:
            debug('Error serializing source for storage:', e)
            serializable_jsonOp = jsonOp  # fallback, but this may still cause issues

        # store the json op to the selected source
        self.stored['Sources'][source] = serializable_jsonOp
        self._updateSourceList()
        return

    # initialize the selected source
    def InitSource(self):
        # get the default source template
        jsonOp = self._getSourceTemplate('defaultSource')

        # get the selected source
        s = self.stored['SelectedSource']

        # store the json op to the selected source
        self.stored['Sources'][s] = jsonOp
        self._updateSourceList()
        return

    def _checkUniqueName(self, source, count=0):
        names = [self._getParVal(s['Settings']['Name']) for s in self.stored['Sources']]

        orig_name = str(self._getParVal(source['Settings']['Name']))

        if names.count(orig_name) > count:
            name = orig_name
            i = 0
            while name in names:
                name = name.rstrip('0123456789')
                name = name + str(i)
                i += 1

            if orig_name != name:
                source['Settings']['Name']['val'] = name
        self._updateSourceList()
        return source

    # new comp source
    def AddSource(self, source_type=None, source_path=None, source_name=None):
        # get the selected source
        s = self.stored['SelectedSource']

        # get the default source template
        if source_type == None:
            source = self._getSourceTemplate('defaultSource')

        elif source_type == 'file':
            source = self._getSourceTemplate('fileSource')
            if source_path is not None:
                debug(source_path)
                debug(type(source_path))
                source['File']['File']['val'] = source_path

        elif source_type == 'top':
            source = self._getSourceTemplate('topSource')
            if source_path is not None:
                source['TOP']['Top']['val'] = source_path

        if source_name is not None:
            source['Settings']['Name']['val'] = source_name

        source = self._checkUniqueName(source)

        # Ensure the source is JSON-serializable before storing
        try:
            serializable_source = json.loads(json.dumps(source))
        except Exception as e:
            debug('Error serializing source for storage:', e)
            serializable_source = source  # fallback, but this may still cause issues

        # insert the template into the sources list
        self.stored['Sources'].insert(s+1, serializable_source)

        self.SelectSource(s+1)

        # update the source comp parameters
        self.UpdateSourceCompQuick(self.selectedSourceComp, s+1, store_changes=True)
        self._updateSourceList()
        return

    def _DropSource(self, args):
        # for each dropped item
        for dropped in args:

            # file source
            if isinstance(dropped, str):
                if os.path.isfile(dropped):
                    source_type = 'file'
                    source_path = dropped
                    base = os.path.basename(dropped)
                    source_name = os.path.splitext(base)[0]
                    file_ext = os.path.splitext(base)[1][1:]

                    if file_ext in tdu.fileTypes['movie'] or file_ext in tdu.fileTypes['image']:
                        self.AddSource(source_type, source_path, source_name)

            # top source
            elif hasattr(dropped, 'family'):
                if dropped.family == 'TOP':
                    source_type = 'top'
                    source_path = dropped.path
                    source_name = dropped.name
                    self.AddSource(source_type, source_path, source_name)

            else:
                debug('not valid source type')
                debug(type(source_type))
                debug(source_type)
        return

    # copy source
    def CopySource(self):
        # get the selected source
        s = self.stored['SelectedSource']

        # get a copy of the source
        source = self.stored['Sources'][s].getRaw()

        source = self._checkUniqueName(source)

        # insert the new source
        self.stored['Sources'].insert(s, source)

        # select the new source
        self.SelectSource(s)
        self._updateSourceList()
        return

    # delete an source
    def DeleteSource(self):
        # get the selected source
        s = self.stored['SelectedSource']
        print(s)
        # get the list of sources
        a = self.stored['Sources']

        if len(a) > 1:
            # pop the source from the list
            a.pop(s)
            # If we deleted the last item, select the new last item
            if s >= len(a):
                self.SelectSource(len(a) - 1)
            else:
                self.SelectSource(s)
        self._updateSourceList()
        return

    # select an source
    def SelectSource(self, index):

        if index > len(self.stored['Sources'])-1:
            index = index - 1

        # set the selected source
        self.stored['SelectedSource'] = index

        # update the sources comp
        self.UpdateSelectedSourceComp()
        return

    # select source up
    def SelectSourceUp(self):
        # get the selected source
        s = self.stored['SelectedSource']

        # select an source up if it exists
        if(s > 0):
            self.SelectSource(s - 1)
        return

    # select source down
    def SelectSourceDown(self):
        # get the selected source
        s = self.stored['SelectedSource']

        # get a list of sources
        a = self.stored['Sources']

        # select an source down if it exists
        if(s < len(a) - 1):
            self.SelectSource(s+1)
        return

    # move source up
    def MoveSourceUp(self):
        # get the selected source
        s = self.stored['SelectedSource']

        # check if the selected source can go up
        if(s > 0):
            # get the list of actoins
            a = self.stored['Sources'][s]

            # delete the selected source
            self.stored['Sources'].pop(s)

            # insert it again a spot up
            self.stored['Sources'].insert(s - 1, a)

            # select the source
            self.SelectSourceUp()
        self._updateSourceList()
        return

    # move source down
    def MoveSourceDown(self):
        # get the selected source
        s = self.stored['SelectedSource']

        # get the sources list
        a = self.stored['Sources']

        # check if the selected source can go down
        if(s < len(a) - 1):
            # get the selected source
            a = self.stored['Sources'][s]

            # delete the selected source
            self.stored['Sources'].pop(s)

            # insert the source one spot down
            self.stored['Sources'].insert(s + 1, a)

            # select the source
            self.SelectSourceDown()
        self._updateSourceList()
        return
