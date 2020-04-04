# Changelog

## 2.1.0

New Features

* moderngl and moderngl-window integration for imgui thought the pyimgui project.
  This is fairly experimental and the rendered should probably be moved to the pyimgui project soon

> Dear ImGui is a bloat-free graphical user interface library for C++. It outputs optimized vertex buffers that you can render anytime in your 3D-pipeline enabled application. It is fast, portable, renderer agnostic and self-contained (no external dependencies)

* Compute shader support. `WindowConfig.load_compute_shader` and added `compute_shader` parameter for `ProgramDescription`.
* Shaders now support `#include` up to a maximum of 100 levels
* Added support for gif anim. This can be loaded as a `Texture` or `TextureArray`
* Added support for loading cube maps
* `WindowConfig.run()` shortcut
* Each window backend now has a `name` property so the user can easily detect what window type they are given
* `WindowConfig` now as a `vsync` property so the user can easily control this from python code
* Scene: New methods to find materials and node by name

Slightly Breaking Changes

* All windows now use 0 samples (MSAA) by default. The default `samples = 4` caused way too much issues
  for people with older integrated gpus and when doing headless rendering when multisampling is not supported.

Bug fixes

* Fixed several issues with glft2 scenes and object orientation
* pyglet window: Fixed incorrect mouse position on retina screens and windows
  with pixel ratio > 1.
* sdl2: mouse press/release events was reversed
* pygame2: Fix broken mouse wheel reading
* glfw: Incorrect mapping of BACKSPACE key
* glfw: Fixed an issue not setting vsync properly¨
* headless: We now call `ctx.finish()` in `swap_buffers`
* Shader errors should now report the error line more accurately
* Various typo fixes

## 2.0.5

Improvements

* Windows now has an `exit_key` property that can be used to change
  or disable the exit key. This key is `ESCAPE` by default and can
  be disabled by setting the property to `None`. This is useful
  for users that don't want the default exit key behavior.
* Log consumed glerrors after context creation as warnings

Bug fixes

* Pyglet mouse coordinates was translated wrong in cases were the
  framebuffer size is larger that then window. The mouse position
  should always use window coordinates.
* VAOs should now properly support 64 bit floats / dvec
* VAOs should be better at detecting/ignoring built in attributes
* `Camera.look_at` had broken input validation when passing in a vector
* Various typos in docstrings

## 2.0.4

Resolved an issue with version constraints causing some dependencies to install pre-release versions

## 2.0.3

* Missing `WindowConfig.close` method and support for close callback for all window types
* Bug: KeyboardCamera's matrix is now always returned as a 32bit floats
* Bug: Projection3D's matrix is now always returned as a 32bit floats
* Example cleanup and improvements

## 2.0.2

* Bug: An `INVALID_ENUM` glerror triggered after querying context info is now consumed.

## 2.0.1

Bug fixes

- SDL2 window now allows highdpi framebuffers when available
- pygame2 window should only initialize the display module

## 2.0.0

Breaking Changes

* `mouse_position_event` signature has changed from `(x, y)` to `(x, y, dx, dy)`.
  This means you will also be getting the relative position change.
* `mouse_drag_event` signature has changed from `(x, y)` to `(x, y, dx, dy)`.
  This means you will also be getting the relative position change.
* `KeyboardCamera.rot_state` now takes dx and dy instead of x and y

Improvements

* Python 3.8 support (PySide2 will take a few more months. SDL2 has issues on windows)
* Added pygame2 window
* Added window callback `iconify` for all window types that will be called
  when a window is minimized or restored
* Window property `mouse_exclusivity` added for all window types.
  When enabled the mouse cursor is invisible and mouse position changes
  are only reported through the dx and dy values.
* Window property `size` is now assignable for all window types
* Window property `position` is now assignable for all window types
* Window property `title` is now assignable for all window types
* Window property `cursor` is now assignable for all window types
* The `KeyboardCamera` class should now be better at reducing the
  chance of rotation and movement popping
* All windows now properly separate viewport calculations when
  using fixed and free viewport (derived from window size)
* The window `aspect_ratio` property should always return
  the a value based on if the aspect ratio is fixed or free
* Added window `fixed_aspect_ratio` property so users can freely
  control this after window creation

## 1.5.2

* Added window property `position` for getting and setting window position for all window types
* Added window properties: `viewport_size`, `viewport_width`, `viewport_height`
* Upgraded dependency for tkinter window. `pyopengltk>=0.0.3`
* Loosened up most of the requirements
* Bug: Missing call to `tk.destroy()` in tk window

## 1.5.1

* Upgraded dependency for tkinter window. `pyopengltk==0.0.2`.

## 1.5.0

* Added experimental support for tkinter window. Relies on
  Jon Wright's pyopengltk package: https://github.com/jonwright/pyopengltk.
  Currently only supports windows and linux, but that might change
  in the future.
* KeyboardCamera: Exposed `mouse_sensitivity`, `velocity` and `projection` attributes
* Various missing docstring and docstring improvements
* Various missing type hints

## 1.4.0

* Added support for mouse_drag events for all window types
* Added support for unicode_char_entered (text input) for all windows
* Added support for mouse wheel events for all window types

## 1.3.0

* Fixed several issue related to python 3.5 support
* Upgraded to pywavefront 1.2.x
* Renamed some modules and classes to better reflect their capabiltities
* Renamed some inconsistent parameter names in the codebase
* Complete overhaul of docstrings in the entire codebase
* Added missing type hints
* Revived the STL loader
* Documentation
* Added `moderngl_window.__version__` attribute

## 1.2.0

* GL errors during window creation is now consumed. This is to avoid confusion when this state is set in the rendering loop.
* Default anisotropy for textures loaders is now 1.0 (disabled, isotropy)
* Mipmaps are no longer generated by default. You must explicitly enable this in parameters.
* WindowConfig.load_texture_2d now exposes more parameters
* WindowConfig.load_texture_array now exposes more parameters
* WindowConfig.load_scene now exposes more parameters
* Texture loaders supports specifying mipmap levels
* Texture loaders supports specifying anisotropy
* VAO wrapper supports normalized float/uint/int
* More tests

## 1.1.0

* Supported buffer formats in the VAO wrapper now matches moderngl better
* VAO wrapper now uses buffer format strings matching moderngl including divisors
* Fixed some logging issues

## 1.0.0

Initial release
