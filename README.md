# Sourcerer

## Introduction

Sourcerer is a media organization solution that provides an efficient and flexible system for the playback, processing, and switching of image files and generative sources from within a TouchDesigner scene.

![sourcerer_screen1](images/screen1.jpg)

## Description
In a typical show file, there may be a large number of sources that need to be displayed. Without the help of any organizational tools, a programmer might find themselves lost in a "Sourcerer's Apprentice" type disaster of nodes and wires plugged into one absolute unit of a Switch TOP. This can leave the wizard feeling overwhelmed with the complexity of their scene and when a simple change needs to be made to a particular source, they might have a difficult time finding that magical elusive operator that needs a slight tweak.

Apart from the many parameters that an image file or a generative source within the scene might have, a few post-processing effects might need to be applied to a source such as:

- Crop
- Tile
- Flip
- Brightness
- Gamma
- Contrast
- Color 
- H/S/V
- Translation
- Scale
- Rotation	

Additionally, one might need to deal with some playback logic like:
	
- How long should a source play/loop or how do we know it is finished?
- What do we play next?
- What type of transition do we need?
- How long is the transition?
- Do we need to run a script?

If there are a great number of sources in a scene that require these effects or logic, things can quickly become quite taxing on the system. Often times, the programmer will find themselves in a position where they've run out of the physical resources needed to achieve their desired framerate.

Sourcerer aims to consolidate all of the above mentioned into a list of "sources" (presets) that can be recalled via 2 interfaces: the UI buttons, and the promoted extension methods. 

##How to Use

Sources are created, arranged, and triggered by using the buttons above the list of sources. The selected source's parameters are editable in the top right section of the interface (labeled "Selected") and the "Live" (or currently playing) source is editable in the bottom right section. Once changes have been made to a "Live" source, the user can click the "Save To Selected Source" button to write the parameter values back to the selected source if desired.

###Buttons

The buttons at the top of the source list are as follows:

- ![add](images/add_new.jpg) Add a new source,
- ![copy](images/copy.jpg) Copy a Source,
- ![delete](images/delete.jpg) Delete a source,
- ![move_up](images/move_up.jpg) Move a source up in the list
- ![move_down](images/move_down.jpg) Move a source down in the list
- ![switch_to_source](images/switch_to_source.jpg) Switch to the selected source
- ![edit](images/edit.jpg) Enable/Disable the editing interface to save system resources.

###Promoted Extension Method

The user may also choose to use the promoted extension method SwitchToSource(source) where the "source" variable can either be an integer value to switch to a source by index or a string value to switch to a source by name.

Examples:
	
- Switch to a source by index (int):

	```
	op('Sourcerer').SwitchToSource(1)
	```

- Switch to a source by name (str):
	
	```
	op('Sourcerer').SwitchToSource('Blackout')
	```

###Transitions

The transition **into** each source may be defined under the settings parameter page for each source.

Transition time is set in seconds via the **Transition Time** parameter. Setting this parameter to 

The **Transition Progress Shape** parameter sets the filter shape (or slope shape) of the transition's progress. This parameter can affect the feeling of the transition by rounding out the start and/or end of the transition's speed.

There are 3 types of progress shapes to choose from:

- **Box (Linear)** - A constant linear slope that can feel a bit mechanical. Usually desired for a custom transition file.
- **Left Half Gaussian** - Starts with a linear slope shape but smoothens the end.
- **Gaussian** - Buttery start and end. Feels very fluid.
- **Custom** - Provide the path to a CHOP in the **Custom Transition Shape** parameter. This CHOP should have a single channel with many samples that start at 0 and end at 1. Ideally the number of samples is a function of the desired transition time multiplied by the frame rate of the scene but this is not required as the samples will be automatically interpolated.

There are 3 primary types of transitions: **GLSL**, **File**, and **TOP**.

- **GLSL** - Pick from a list of 24 premade transitions.
	- Additive
	- Average
	- Blinds
	- Blood
	- Circle Reveal
	- Circle Stretch
	- Cloud Reveal
	- Color Burn
	- Color Distance
	- Cross Warp
	- Difference
	- Dissolve
	- Dreamy
	- Fade
	- Fade Black
	- Linear Burn
	- Maximum
	- Morph 1
	- Morph 2
	- Perlin
	- Radial Blur
	- Random Squares
	- Ripple
	- Stretch

- **File** - Specify a file on the disk 
	- Should start in black and end in white.
	- The file is played over the duration of the transition set with the **Transition Time** parameter

- **TOP** - Specify a TOP in the scene
	- Should start in black and end in white.
	- A **transition_progress** channel is provided in the CHOP output of the Sourcerer component to easily drive a generative transition while using the TOP transition type. 



###Follow Actions

Each source is provided a "Follow Action" parameter that defines what happens when the source is done playing. Sourcerer can automatically play the next source or go to another source by index or name. While working with image/movie files, follow actions can be triggered by setting a timer, a number of times to play, a chop channel, or by pulsing the "Done" pulse parameter. Generative (TOP) sources can either use a timer, a chop channel, or a "Done" pulse. For those of you familiar with Ableton, this can be thought of as clip follow actions. 

##Configuration

###Sourcerer Parameters

####Settings

- **Resolution** - The resolution of the background that the sources are composited over.


###Source Parameters

####Settings

- **Name** - The name that is displayed in the list of sources. This is callable via the SwitchToSource method outlined below. Names should be unique in order for the SwitchToSource method to be able to find a source by name (str). 

- **Source Type** - Either File (location on disk) or TOP (path of a top in your scene). This selection enables/disables the two following parameter pages.

- **Transition Type** - The type of transition to use when switching to _THIS_ source.

- **Transition Time** - The length of the transition when switching to _THIS_ source.

- **Enable Command** - Enable the command in the Command parameter to be executed when _THIS_ source is switched to.

- **Command** - The python command to execute when _THIS_ source is switched to if the Enable Command parameter is True.

- **Command Pulse** - A test button to fire off the command.

####File

- **File** - The path of the file.

- **File Length Frames** (read only) - The length of the file in frames.

- **Trim** - Enable file trimming.

- **Trim Start Frames** - The frame to start the file on.

- **Trim End Frames** - The frame to end the file on.

- **Speed** - File playback speed multiplier (1=100%).

- **Interpolate frames** - Blend between frames when playing slower than 100%.

- **Cue** - A toggle switch to cue the video at the Cue Point Frames parameter.

- **Cue Pulse** - A pulse to cue the video at the Cue Point Frames parameter.

- **Cue Point Frames** - The point in the video (in frames) to cue from.

- **Loop Crossfade Frames** - The number of frames to crossfade a loop.

- **Deinterlace** - Deinterlace the playback (Even/Odd/Bob(split)).

- **Field Precedence** - Deinterlace mode (Even/Odd).

- **Extend Right** - Define what happens at the end of the file.

- **Done On** - When to evaluate the Follow Action (None, Play (n) Times, Timer, CHOP Channel).

- **Play (n) Times** - Number of times to play the file before the Follow Action is triggered.

- **Timer Time (sec)** - Amount of time to play the file before the Follow Action is triggered.

- **CHOP** - Path to a chop who's first channel can trigger the Follow Action when toggled from off (0) to on (1).

- **Done Pulse** - Trigger the Follow Action immediately.

- **Follow Action** - The type of follow action to use (None, Play Next, Go to Index, Go to Name).

- **Go To Index** - The index (int) of the next source to play.

- **Go To Name** - The name (str) of the next source to play.


####TOP

- **TOP** - The path to the TOP to be displayed.

- **Enable Cue Top** - Enable this parameter to allow the Moviefilein TOP in the following parameter to be cued when <u>THIS</u> source is switched to.

- **Cue TOP** - The path to the Moviefilein TOP to pulse the cue parameter on.

- **Cue TOP Pulse** - Send a cue pulse to the operator defined in the Cue TOP Parameter.

- **Done On** - When to evaluate the Follow Action (None, Timer, CHOP Channel).

- **Timer Time (sec)** - Amount of time to play the file before the Follow Action is triggered.

- **CHOP** - Path to a chop who's first channel can trigger the Follow Action when toggled from off (0) to on (1).

- **Done Pulse** - Trigger the Follow Action immediately.

- **Follow Action** - The type of follow action to use (None, Play Next, Go to Index, Go to Name).

- **Go To Index** - The index (int) of the next source to play.

- **Go To Name** - The name (str) of the next source to play.


####Crop / Tile

- **Crop Left** - 0 to 1 fraction of where to crop the left side of the image.

- **Crop Right** - 0 to 1 fraction of where to crop the right side of the image.

- **Crop Bottom** - 0 to 1 fraction of where to crop the bottom of the image.

- **Crop Top** - 0 to 1 fraction of where to crop to top of the image.

- **Crop Extend** - Defines what to do with the image when the crop value exceeds the 0 to 1 space.

- **Transpose** - Swap the x and y coordinate space of the image.

- **Flip X** - Flip the x coordinate space of the image.

- **Flip Y** - Flip the y coordinate space of the image.

- **Repeat X** - Number of times to repeat the image in x.

- **Repeat Y** - Number of times to repeat the image in y.

- **Reflect X** - Reflect the image in x if repeated.

- **Reflect Y** - Reflect the image in y if repeated.

- **Overlap U** - Overlap the image in u to create a soft edge.

- **Overlap V** - Overlap the image in v to create a soft edge.


####Color

- **Invert** - Inverts the colors in the image. Black becomes white, white becomes black.

- **Black Level** - Any pixel with a value less than or equal to this will be black.  

- **Brightness** - Increases or decreases the brightness of an image. Brightness can be considered the arithmetic mean of the RGB channels. The Brightness parameter adds or subtracts an offset into the R, G, and B channels.

- **Gamma** - The Gamma parameter applies a gamma correction to the image. Gamma is the relationship between the brightness of a pixel as it appears on the screen, and the numerical value of that pixel.

- **Contrast** - Contrast applies a scale factor (gain) to the RGB channels. Increasing contrast will brighten the light areas and darken the dark areas of the image, making the difference between the light and dark areas of the image stronger.

- **Red** - Clamps the maximum level of the red channel.

- **Green** - Clamps the maximum level of the green channel.

- **Blue** - Clamps the maximum level of the blue channel.

- **Hue** - Shifts the hue of the image.

- **Saturation** - Adjusts the saturation of the image.

- **Value** - Adjusts the overall color value of the image.


####Transform

- **Pre-Fit Overlay** - Defines how the image is placed over the component's resolution (Fill, Fit Horizontal, Fit Vertical, Fit Best, Fit Outside, Native Resolution).

- **Justify Horizontal** - Where to justify the image horizontally (Left, Center, Right).

- **Justify Vertical** - Where to justify the image vertically (Bottom, Center, Top).

- **Extend Overlay** - What to do with the negative space around the image if it exists.

- **Translate** - Translates the image in x and y (0 to 1 space).

- **Scale** - Scales the image in x and y (0 to 1 space).

- **Rotate** - Rotates the image.