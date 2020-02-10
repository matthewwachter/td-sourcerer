# Author: Matthew Wachter
# License: MIT


class Source:
    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        self.parPages = ownerComp.customPages
        self.parPageNames = [p.name for p in self.parPages]
        self.glslTransPars = {
            'Blinds': ['Blindsnum'],
            'Blood': ['Seed'],
            'Circle_Reveal': ['Circlerevealfuzzy'],
            'Color_Burn': ['Colorburncolor'],
            'Color_Distance': ['Colordistancepower'],
            'Cube_Left': ['Cubeperspective', 'Cubeunzoom'],
            'Cube_Right': ['Cubeperspective', 'Cubeunzoom'],
            'Dissolve': ['Seed'],
            'Fade_Color': ['Fadecolor'],
            'Linear Blur': ['Linearblurintensity', 'Linearblurpasses'],
            'Maximum': ['Maximumdistance', 'Maximumfadeindistance'],
            'Morph1': ['Morph1strength'],
            'Perlin': ['Perlinscale', 'Seed', 'Perlinsmoothness'],
            'Pixelize': ['Pixelizesquaresmin'],
            'Radial_Blur': ['Radialblurcenter'],
            'Random_Squares': ['Randomsquaressize', 'Randomsquaressmoothness'],
            'Ripple': ['Rippleamplitude', 'Ripplecenter', 'Ripplefrequency', 'Ripplespeed'],
            'Slide': ['Slidedirection'],
            'Swap_Left': ['Swapperspective', 'Swapdepth'],
            'Swap_Right': ['Swapperspective', 'Swapdepth']
        }

    def SaveChanges(self):
        return

    # PARAMETER CHANGES

    def _HandleParChange(self, par):
        if hasattr(self, par.name):
            getattr(self, par.name)(par)

    # change source type
    def Sourcetype(self, par):
        if par.val == 'top':
            self._enableSourceTypeTOP()
        elif par.val == 'file':
            self._enableSourceTypeFile()

    def Cuepulse(self, par):
        self.ownerComp.op('moviefilein1').par.cuepulse.pulse()

    def Commandpulse(self, par):
        parent.SOURCERER.op('commandScript').text = parent().par.Command
        parent.SOURCERER.op('commandScript').run()

    def Deinterlace(self, par):
        if str(par) == 'off':
            self.ownerComp.par.Fieldprecedence.enable = False
        else:
            self.ownerComp.par.Fieldprecedence.enable = True

    def Doneonfile(self, par):
        done_on = str(par)
        if done_on == 'none':
            self.ownerComp.par.Playntimes.enable = False
            self.ownerComp.par.Timertimefile.enable = False
            self.ownerComp.par.Chopfile.enable = False
        elif done_on == 'play_n_times':
            self.ownerComp.par.Playntimes.enable = True
            self.ownerComp.par.Timertimefile.enable = False
            self.ownerComp.par.Chopfile.enable = False
        elif done_on == 'timer':
            self.ownerComp.par.Playntimes.enable = False
            self.ownerComp.par.Timertimefile.enable = True
            self.ownerComp.par.Chopfile.enable = False
        elif done_on == 'chop':
            self.ownerComp.par.Playntimes.enable = False
            self.ownerComp.par.Timertimefile.enable = False
            self.ownerComp.par.Chopfile.enable = True

    def Followactionfile(self, par):
        follow_action = str(par)
        if follow_action in ['none', 'play_next']:
            self.ownerComp.par.Gotoindexfile.enable = False
            self.ownerComp.par.Gotonamefile.enable = False
        elif follow_action == 'goto_index':
            self.ownerComp.par.Gotoindexfile.enable = True
            self.ownerComp.par.Gotonamefile.enable = False
        elif follow_action == 'goto_name':
            self.ownerComp.par.Gotoindexfile.enable = False
            self.ownerComp.par.Gotonamefile.enable = True

    def Doneontop(self, par):
        done_on = str(par)

        if done_on == 'none':
            self.ownerComp.par.Timertimetop.enable = False
            self.ownerComp.par.Choptop.enable = False
        elif done_on == 'timer':
            self.ownerComp.par.Timertimetop.enable = True
            self.ownerComp.par.Choptop.enable = False
        elif done_on == 'chop':
            self.ownerComp.par.Timertimetop.enable = False
            self.ownerComp.par.Choptop.enable = True

    def Followactiontop(self, par):
        follow_action = str(par)
        if follow_action in ['none', 'play_next']:
            self.ownerComp.par.Gotoindextop.enable = False
            self.ownerComp.par.Gotonametop.enable = False
        elif follow_action == 'goto_index':
            self.ownerComp.par.Gotoindextop.enable = True
            self.ownerComp.par.Gotonametop.enable = False
        elif follow_action == 'goto_name':
            self.ownerComp.par.Gotoindextop.enable = False
            self.ownerComp.par.Gotonametop.enable = True

    def Name(self, par):
        names = [ext.SOURCERER._getParVal(s['Settings']['Name']) for s in ext.SOURCERER.Sources]

        name = str(par.val)
        i = 0
        while name in names:
            name = name.rstrip('0123456789')
            name = name + str(i)
            i += 1

        if par.val != name:
            par.val = name

        if self.ownerComp.par.Storechanges.val:
            ext.SOURCERER.StoreSourceToSelected(self.ownerComp)

    def Transitionprogressshape(self, par):
        if par.val == 'custom':
            self.ownerComp.par.Customtransitionshape.enable = True
        else:
            self.ownerComp.par.Customtransitionshape.enable = False

    def Transitiontype(self, par):
        glsl = False
        file = False
        top = False

        if par.val == 'glsl':
            glsl = True
        elif par.val == 'file':
            file = True
        elif par.val == 'top':
            top = True

        self.ownerComp.par.Glsltransition.enable = glsl
        self._updateGLSLPars()
        self.ownerComp.par.Transitionfile.enable = file
        self.ownerComp.par.Transitiontop.enable = top

    def Glsltransition(self, par):
        self._updateGLSLPars()
        return

    def _updateGLSLPars(self):
        for p in self.ownerComp.customPages[1]:
            p.enable = False

        trans_type = self.ownerComp.par.Transitiontype

        if trans_type == 'glsl':
            glsl_trans = str(self.ownerComp.par.Glsltransition)

            if glsl_trans in self.glslTransPars.keys():
                par_names = self.glslTransPars[glsl_trans]

                for p_name in par_names:
                    for p in self.ownerComp.pars(p_name + '*'):
                        p.enable = True

    def Useglobaltransitiontime(self, par):
        self.ownerComp.par.Transitiontime.enable = not par.val

    def _enableSourceTypeFile(self):
        file_pars = self.parPages[self.parPageNames.index('File')]

        for p in file_pars:
            p.enable = True

        top_pars = self.parPages[self.parPageNames.index('TOP')]

        for p in top_pars:
            p.enable = False

        # set enable state for field precedence
        deinterlace = self.ownerComp.par.Deinterlace
        if deinterlace != 'none':
            self.ownerComp.par.Fieldprecedence.enable = True
        else:
            self.ownerComp.par.Fieldprecedence.enable = False

        # set enable states for 'done on' parameters
        done_on = self.ownerComp.par.Doneonfile
        if done_on == 'none':
            self.ownerComp.par.Playntimes.enable = False
            self.ownerComp.par.Timertimefile.enable = False
            self.ownerComp.par.Chopfile.enable = False
        elif done_on == 'play_n_times':
            self.ownerComp.par.Playntimes.enable = True
            self.ownerComp.par.Timertimefile.enable = False
            self.ownerComp.par.Chopfile.enable = False
        elif done_on == 'timer':
            self.ownerComp.par.Playntimes.enable = False
            self.ownerComp.par.Timertimefile.enable = True
            self.ownerComp.par.Chopfile.enable = False
        elif done_on == 'chop':
            self.ownerComp.par.Playntimes.enable = False
            self.ownerComp.par.Timertimefile.enable = False
            self.ownerComp.par.Chopfile.enable = True

        # set follow action enable states
        follow_action = self.ownerComp.par.Followactionfile
        if follow_action in ['none', 'play_next']:
            self.ownerComp.par.Gotoindexfile.enable = False
            self.ownerComp.par.Gotonamefile.enable = False
        elif follow_action == 'goto_index':
            self.ownerComp.par.Gotoindexfile.enable = True
            self.ownerComp.par.Gotonamefile.enable = False
        elif follow_action == 'goto_name':
            self.ownerComp.par.Gotoindexfile.enable = False
            self.ownerComp.par.Gotonamefile.enable = True
        return

    def _enableSourceTypeTOP(self):
        file_pars = self.parPages[self.parPageNames.index('File')]

        for p in file_pars:
            p.enable = False

        top_pars = self.parPages[self.parPageNames.index('TOP')]

        for p in top_pars:
            p.enable = True

        # set enable states for 'done on' parameters
        done_on = self.ownerComp.par.Doneontop
        if done_on == 'none':
            self.ownerComp.par.Timertimetop.enable = False
            self.ownerComp.par.Choptop.enable = False
        elif done_on == 'timer':
            self.ownerComp.par.Timertimetop.enable = True
            self.ownerComp.par.Choptop.enable = False
        elif done_on == 'chop':
            self.ownerComp.par.Timertimetop.enable = False
            self.ownerComp.par.Choptop.enable = True

        # set follow action enable states
        follow_action = self.ownerComp.par.Followactionfile
        if follow_action in ['none', 'play_next']:
            self.ownerComp.par.Gotoindextop.enable = False
            self.ownerComp.par.Gotonametop.enable = False
        elif follow_action == 'goto_index':
            self.ownerComp.par.Gotoindextop.enable = True
            self.ownerComp.par.Gotonametop.enable = False
        elif follow_action == 'goto_name':
            self.ownerComp.par.Gotoindextop.enable = False
            self.ownerComp.par.Gotonametop.enable = True
        return

    def _handleFollowAction(self):

        source_type = str(self.ownerComp.par.Sourcetype)
        if source_type == 'file':
            follow_action = self.ownerComp.par.Followactionfile
        elif source_type == 'top':
            follow_action = self.ownerComp.par.Followactiontop
        else:
            print('_handleFollowAction error:', 'not valid source type', source_type)
            return

        if self.ownerComp.par.Active:
            if self.ownerComp.name in ['source0', 'source1']:
                if self.ownerComp.digits == ext.SOURCERER.State:
                    # play next
                    if follow_action == 'play_next':
                        cur_index = parent.SOURCERER.ActiveSource['index']
                        parent.SOURCERER.SwitchToSource(cur_index+1)

                    # go to index
                    elif follow_action == 'goto_index':
                        if source_type == 'file':
                            goto_index = self.ownerComp.par.Gotoindexfile
                        else:
                            goto_index = self.ownerComp.par.Gotoindextop

                        parent.SOURCERER.SwitchToSource(int(goto_index))

                    # go to name
                    elif follow_action == 'goto_name':
                        if source_type == 'file':
                            goto_name = self.ownerComp.par.Gotonamefile
                        else:
                            goto_name = self.ownerComp.par.Gotonametop
                        parent.SOURCERER.SwitchToSource(str(goto_name))
