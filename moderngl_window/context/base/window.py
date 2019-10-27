from functools import wraps
from pathlib import Path
import logging
import sys
from typing import Any, Tuple, Type

import moderngl
from moderngl_window.context.base import KeyModifiers, BaseKeys
from moderngl_window.timers.base import BaseTimer
from moderngl_window import resources
from moderngl_window.geometry.attributes import AttributeNames
from moderngl_window.meta import (
    TextureDescription,
    ProgramDescription,
    SceneDescription,
    DataDescription,
)
from moderngl_window.scene import Scene

logger = logging.getLogger(__name__)


def require_callable(func):
    """Decorator ensuring assigned callbacks are valid callables"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not callable(args[1]):
            raise ValueError("{} is not a callable".format(args[1]))
        return func(*args, **kwargs)
    return wrapper


class MouseButtons:
    """Maps what button id to a name"""
    left = 1
    right = 2
    middle = 3


class MouseButtonStates:
    """Namespace for storing the current mouse button states"""
    left = False
    right = False
    middle = False

    @property
    def any(self):
        """bool: if any mouse buttons are pressed"""
        return self.left or self.right or self.middle

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return "<MouseButtonStates left={} right={} middle={}".format(self.left, self.right, self.middle)


class BaseWindow:
    """
    Helper base class for a generic window implementation
    """
    #: Window specific key constants
    keys = BaseKeys
    #: Mouse button enum
    mouse = MouseButtons

    def __init__(self, title="ModernGL", gl_version=(3, 3), size=(1280, 720), resizable=True,
                 fullscreen=False, vsync=True, aspect_ratio: float = None, samples=4, cursor=True,
                 **kwargs):
        """Initialize a window instance.

        Args:
            title (str): The window title
            gl_version (tuple): Major and minor version of the opengl context to create
            size (tuple): Window size x, y
            resizable (bool): Should the window be resizable?
            fullscreen (bool): Open window in fullsceeen mode
            vsync (bool): Enable/disable vsync
            aspect_ratio (float): The desired fixed aspect ratio. Can be set to ``None`` to make
                                  aspect ratio be based on the actual window size.
            samples (int): Number of MSAA samples for the default framebuffer
            cursor (bool): Enable/disable displaying the cursor inside the window
        """
        # Window parameters
        self._title = title
        self._gl_version = gl_version
        self._width, self._height = int(size[0]), int(size[1])
        self._resizable = resizable
        self._buffer_width, self._buffer_height = size
        self._fullscreen = fullscreen
        self._vsync = vsync
        self._fixed_aspect_ratio = aspect_ratio
        self._samples = samples
        self._cursor = cursor

        # Callback functions
        self._render_func = dummy_func
        self._resize_func = dummy_func
        self._iconify_func = dummy_func
        self._key_event_func = dummy_func
        self._mouse_position_event_func = dummy_func
        self._mouse_press_event_func = dummy_func
        self._mouse_release_event_func = dummy_func
        self._mouse_drag_event_func = dummy_func
        self._mouse_scroll_event_func = dummy_func
        self._unicode_char_entered_func = dummy_func

        # Internal states
        self._ctx = None  # type: moderngl.Context
        self._viewport = None
        self._position = 0, 0
        self._frames = 0  # Frame counter
        self._close = False
        self._config = None
        self._key_pressed_map = {}
        self._modifiers = KeyModifiers()
        self._mouse_buttons = MouseButtonStates()
        # Manual tracking of mouse position used by some windows
        self._mouse_pos = 0, 0
        self._mouse_exclusivity = False

        # Do not allow resize in fullscreen
        if self._fullscreen:
            self._resizable = False

        if not self.keys:
            raise ValueError("Window class {} missing keys attribute".format(self.__class__))

    def init_mgl_context(self) -> None:
        """
        Create or assign a ModernGL context. If no context is supplied a context will be
        created using the window's ``gl_version``.

        Keyword Args:
            ctx: An optional custom ModernGL context
        """
        self._ctx = moderngl.create_context(require=self.gl_version_code)
        err = self._ctx.error
        if err != "GL_NO_ERROR":
            logger.info("Consumed the following error during context creation: %s", err)

    @property
    def ctx(self) -> moderngl.Context:
        """moderngl.Context: The ModernGL context for the window"""
        return self._ctx

    @property
    def fbo(self) -> moderngl.Framebuffer:
        """moderngl.Framebuffer: The default framebuffer"""
        return self._ctx.screen

    @property
    def title(self) -> str:
        """str: Window title.

        This property can also be set::

            window.title = "New Title"
        """
        return self._title

    @title.setter
    def title(self, value: str):
        self._title = value

    @property
    def gl_version(self) -> Tuple[int, int]:
        """Tuple[int, int]: (major, minor) required OpenGL version"""
        return self._gl_version

    @property
    def width(self) -> int:
        """int: The current window width"""
        return self._width

    @property
    def height(self) -> int:
        """int: The current window height"""
        return self._height

    @property
    def size(self) -> Tuple[int, int]:
        """Tuple[int, int]: current window size.

        This property also support assignment::

            # Resize the window to 1000 x 1000
            window.size = 1000, 1000
        """
        return self._width, self._height

    @size.setter
    def size(self, value: Tuple[int, int]):
        self._width, self._height = int(value[0]), int(value[1])

    @property
    def buffer_width(self) -> int:
        """int: the current window buffer width"""
        return self._buffer_width

    @property
    def buffer_height(self) -> int:
        """int: the current window buffer height"""
        return self._buffer_height

    @property
    def buffer_size(self) -> Tuple[int, int]:
        """Tuple[int, int]: tuple with the current window buffer size"""
        return self._buffer_width, self._buffer_height

    @property
    def position(self) -> Tuple[int, int]:
        """Tuple[int, int]: The current window position.

        This property can also be set to move the window::

            # Move window to 100, 100
            window.position = 100, 100
        """
        return self._position

    @position.setter
    def position(self, value: Tuple[int, int]):
        self._position = int(value[0]), int(value[1])

    @property
    def pixel_ratio(self) -> float:
        """float: The frambuffer/window size ratio"""
        return self.buffer_size[0] / self.size[0]

    @property
    def viewport(self) -> Tuple[int, int, int, int]:
        """Tuple[int, int, int, int]: current window viewport"""
        return self._viewport

    @property
    def viewport_size(self) -> Tuple[int, int]:
        """Tuple[int,int]: Size of the viewport.

        Equivalent to ``self.viewport[2], self.viewport[3]``
        """
        return self._viewport[2], self._viewport[3]

    @property
    def viewport_width(self) -> int:
        """int: The width of the viewport.

        Equivalent to ``self.viewport[2]``.
        """
        return self.viewport[2]

    @property
    def viewport_height(self) -> int:
        """int: The height of the viewport

        Equivalent to ``self.viewport[3]``.
        """
        return self.viewport[3]

    @property
    def frames(self) -> int:
        """int: Number of frames rendered"""
        return self._frames

    @property
    def resizable(self) -> bool:
        """bool: Window is resizable"""
        return self._resizable

    @property
    def fullscreen(self) -> bool:
        """bool: Window is in fullscreen mode"""
        return self._fullscreen

    @property
    def config(self) -> 'WindowConfig':
        """Get the current WindowConfig instance

        This property can also be set.
        Assinging a WindowConfig instance will automatically
        set up the necessary event callback methods::

            window.config = window_config_instance
        """
        return self._config

    @property
    def vsync(self) -> bool:
        """bool: vertical sync enabled/disabled"""
        return self._vsync

    @property
    def aspect_ratio(self) -> float:
        """float: The current aspect ratio of the window.
        If a fixed aspect ratio was passed to the window
        initializer this value will always be returned.
        Otherwise ``width / height`` will be returned.

        This property is read only.
        """
        if self._fixed_aspect_ratio:
            return self._fixed_aspect_ratio

        return self.width / self.height

    @property
    def fixed_aspect_ratio(self):
        """float: The fixed aspect ratio for the window.

        Can be set to ``None`` to disable fixed aspect ratio
        making the aspect ratio adjust to the actual window size

        This will affects how the viewport is calculated and
        the reported value from the ``aspect_ratio`` property::

            # Enabled fixed aspect ratio
            window.fixed_aspect_ratio = 16 / 9

            # Disable fixed aspect ratio
            window.fixed_aspect_ratio = None
        """
        return self._fixed_aspect_ratio

    @fixed_aspect_ratio.setter
    def fixed_aspect_ratio(self, value: float):
        self._fixed_aspect_ratio = value

    @property
    def samples(self) -> float:
        """float: Number of Multisample anti-aliasing (MSAA) samples"""
        return self._samples

    @property
    def cursor(self) -> bool:
        """bool: Should the mouse cursor be visible inside the window?

        This property can also be assigned to::

            # Disable cursor
            window.cursor = False
        """
        return self._cursor

    @cursor.setter
    def cursor(self, value: bool):
        self._cursor = value

    @property
    def mouse_exclusivity(self) -> bool:
        """bool: If mouse exclusivity is enabled.

        When you enable mouse-exclusive mode, the mouse cursor is no longer
        available. It is not merely hidden – no amount of mouse movement
        will make it leave your application. This is for example useful
        when you don't want the mouse leaving the screen when rotating
        a 3d scene.

        This property can also be set::

            window.mouse_exclusivity = True
        """
        return self._mouse_exclusivity

    @mouse_exclusivity.setter
    def mouse_exclusivity(self, value: bool):
        self._mouse_exclusivity = value

    @config.setter
    def config(self, config):
        self.render_func = getattr(config, 'render', dummy_func)
        self.resize_func = getattr(config, 'resize', dummy_func)
        self.iconify_func = getattr(config, 'iconify', dummy_func)
        self.key_event_func = getattr(config, 'key_event', dummy_func)
        self.mouse_position_event_func = getattr(config, 'mouse_position_event', dummy_func)
        self.mouse_press_event_func = getattr(config, 'mouse_press_event', dummy_func)
        self.mouse_release_event_func = getattr(config, 'mouse_release_event', dummy_func)
        self.mouse_drag_event_func = getattr(config, 'mouse_drag_event', dummy_func)
        self.mouse_scroll_event_func = getattr(config, 'mouse_scroll_event', dummy_func)
        self.unicode_char_entered_func = getattr(config, 'unicode_char_entered', dummy_func)

        self._config = config

    @property
    def render_func(self):
        """callable: The render callable

        This property can also be used to assign a callable.
        """
        return self._render_func

    @render_func.setter
    @require_callable
    def render_func(self, func):
        self._render_func = func

    @property
    def resize_func(self):
        """callable: The resize callable

        This property can also be used to assign a callable.
        """
        return self._resize_func

    @resize_func.setter
    @require_callable
    def resize_func(self, func):
        self._resize_func = func

    @property
    def iconify_func(self):
        """callable: The iconify/show/hide callback function

        The property can also be used to assign a callable.
        """
        return self._iconify_func

    @iconify_func.setter
    @require_callable
    def iconify_func(self, func):
        self._iconify_func = func

    @property
    def key_event_func(self):
        """callable: The key_event callable

        This property can also be used to assign a callable.
        """
        return self._key_event_func

    @key_event_func.setter
    @require_callable
    def key_event_func(self, func):
        self._key_event_func = func

    @property
    def mouse_position_event_func(self):
        """callable: The mouse_position callable

        This property can also be used to assign a callable.
        """
        return self._mouse_position_event_func

    @mouse_position_event_func.setter
    @require_callable
    def mouse_position_event_func(self, func):
        self._mouse_position_event_func = func

    @property
    def mouse_drag_event_func(self):
        """callable: The mouse_drag callable

        This property can also be used to assign a callable.
        """
        return self._mouse_drag_event_func

    @mouse_drag_event_func.setter
    @require_callable
    def mouse_drag_event_func(self, func):
        self._mouse_drag_event_func = func

    @property
    def mouse_press_event_func(self):
        """callable: The mouse_press callable

        This property can also be used to assign a callable.
        """
        return self._mouse_press_event_func

    @mouse_press_event_func.setter
    @require_callable
    def mouse_press_event_func(self, func):
        self._mouse_press_event_func = func

    @property
    def mouse_release_event_func(self):
        """callable: The mouse_release callable

        This property can also be used to assign a callable.
        """
        return self._mouse_release_event_func

    @mouse_release_event_func.setter
    @require_callable
    def mouse_release_event_func(self, func):
        self._mouse_release_event_func = func

    @property
    def unicode_char_entered_func(self):
        """callable: The unicode_char_entered callable

        This property can also be used to assign a callable.
        """
        return self._unicode_char_entered_func

    @unicode_char_entered_func.setter
    @require_callable
    def unicode_char_entered_func(self, func):
        self._unicode_char_entered_func = func

    @property
    def mouse_scroll_event_func(self):
        """callable: The mouse_scroll_event calable

        This property can also be used to assign a callable.
        """
        return self._mouse_scroll_event_func

    @mouse_scroll_event_func.setter
    @require_callable
    def mouse_scroll_event_func(self, func):
        self._mouse_scroll_event_func = func

    @property
    def modifiers(self) -> Type[KeyModifiers]:
        """(KeyModifiers) The current keyboard modifiers"""
        return self._modifiers

    @property
    def mouse_states(self) -> MouseButtonStates:
        """MouseButtonStates: Mouse button state structure.

        The current mouse button states.

        .. code::

            window.mouse_buttons.left
            window.mouse_buttons.right
            window.mouse_buttons.middle
        """
        return self._mouse_buttons

    def _handle_mouse_button_state_change(self, button: int, pressed: bool):
        """Updates the internal mouse button state object.

        Args:
            button (int): The button number [1, 2 or 3]
            pressed (bool): Pressed (True) or released (False)
        """
        if button == self.mouse.left:
            self._mouse_buttons.left = pressed
        elif button == self.mouse.right:
            self._mouse_buttons.right = pressed
        elif button == self.mouse.middle:
            self._mouse_buttons.middle = pressed
        else:
            raise ValueError("Incompatible mouse button number: {}".format(button))

    def is_key_pressed(self, key) -> bool:
        """Returns: The press state of a key"""
        return self._key_pressed_map.get(key) is True

    @property
    def is_closing(self) -> bool:
        """bool: Is the window about to close?"""
        return self._close

    def close(self) -> None:
        """Signal for the window to close"""
        self._close = True

    def use(self):
        """Bind the window's framebuffer"""
        self._ctx.screen.use()

    def clear(self, red=0.0, green=0.0, blue=0.0, alpha=0.0, depth=1.0, viewport=None):
        """
        Binds and clears the default framebuffer

        Args:
            red (float): color component
            green (float): color component
            blue (float): color component
            alpha (float): alpha component
            depth (float): depth value
            viewport (tuple): The viewport
        """
        self.use()
        self._ctx.clear(red=red, green=green, blue=blue, alpha=alpha, depth=depth, viewport=viewport)

    def render(self, time=0.0, frame_time=0.0) -> None:
        """
        Renders a frame by calling the configured render callback

        Keyword Args:
            time (float): Current time in seconds
            frame_time (float): Delta time from last frame in seconds
        """
        self.render_func(time, frame_time)

    def swap_buffers(self) -> None:
        """
        Library specific buffer swap method. Must be overridden.
        """
        raise NotImplementedError()

    def resize(self, width, height) -> None:
        """
        Should be called every time window is resized
        so the example can adapt to the new size if needed
        """
        if self._resize_func:
            self._resize_func(width, height)

    def destroy(self) -> None:
        """
        A library specific destroy method is required
        """
        raise NotImplementedError()

    def set_default_viewport(self) -> None:
        """
        Calculates the and sets the viewport based on window configuration.

        The viewport will based on the configured fixed aspect ratio if set.
        If no fixed aspect ratio is set the viewport will be scaled
        to the entire window size regardless of size.

        Will add black borders and center the viewport if the window
        do not match the configured viewport (fixed only)
        """
        if self._fixed_aspect_ratio:
            expected_width = int(self._buffer_height * self._fixed_aspect_ratio)
            expected_height = int(expected_width / self._fixed_aspect_ratio)

            if expected_width > self._buffer_width:
                expected_width = self._buffer_width
                expected_height = int(expected_width / self._fixed_aspect_ratio)

            blank_space_x = self._buffer_width - expected_width
            blank_space_y = self._buffer_height - expected_height

            self._viewport = (
                blank_space_x // 2,
                blank_space_y // 2,
                expected_width,
                expected_height,
            )
        else:
            self._viewport = (0, 0, self._buffer_width, self._buffer_height)

        self._ctx.viewport = self._viewport

    @property
    def gl_version_code(self) -> int:
        """int: Generates the version code integer for the selected OpenGL version.

        gl_version (4, 1) returns 410
        """
        return self.gl_version[0] * 100 + self.gl_version[1] * 10

    def print_context_info(self):
        """
        Prints moderngl context info.
        """
        logger.info("Context Version:")
        logger.info('ModernGL: %s', moderngl.__version__)
        logger.info('vendor: %s', self._ctx.info['GL_VENDOR'])
        logger.info('renderer: %s', self._ctx.info['GL_RENDERER'])
        logger.info('version: %s', self._ctx.info['GL_VERSION'])
        logger.info('python: %s', sys.version)
        logger.info('platform: %s', sys.platform)
        logger.info('code: %s', self._ctx.version_code)

    def _calc_mouse_delta(self, xpos: int, ypos: int) -> Tuple[int, int]:
        """Calculates the mouse position delta for events that don's support this

        Args:
            xpos (int): current mouse x
            ypos (int): current mouse y
        Returns:
            Tuple[int, int]: The x, y delta values
        """
        dx, dy = xpos - self._mouse_pos[0], ypos - self._mouse_pos[1]
        self._mouse_pos = xpos, ypos
        return dx, dy


class WindowConfig:
    """
    Creating a ``WindowConfig`` instance is the simplest interface
    this library provides to open and window, handle inputs and provide simple
    shortcut method for loading basic resources. It's appropriate
    for projects with basic needs.

    Example:

    .. code:: python

        class MyConfig(mglw.WindowConfig):
            gl_version = (3, 3)
            window_size = (1920, 1080)
            aspect_ratio = 16 / 9
            title = "My Config"
            resizable = False
            samples = 8

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                # Do other initialization here

            def render(self, time: float, frametime: float):
                # Render stuff here with ModernGL

            def resize(self, width: int, height: int):
                print("Window was resized. buffer size is {} x {}".format(width, height))

            def mouse_position_event(self, x, y):
                print("Mouse position:", x, y)

            def mouse_press_event(self, x, y, button):
                print("Mouse button {} pressed at {}, {}".format(button, x, y))

            def mouse_release_event(self, x: int, y: int, button: int):
                print("Mouse button {} released at {}, {}".format(button, x, y))

            def key_event(self, key, action, modifiers):
                print(key, action, modifiers)

    """
    window_size = (1280, 720)
    """
    Size of the window.

    .. code:: python

        # Default value
        window_size = (1280, 720)
    """
    resizable = True
    """
    Determines of the window should be resizable

    .. code:: python

        # Default value
        resizable = True
    """
    gl_version = (3, 3)
    """
    The minimum required OpenGL version required

    .. code:: python

        # Default value
        gl_version = (3, 3)
    """
    title = "Example"
    """
    Title of the window

    .. code:: python

        # Default value
        title = "Example"
    """
    aspect_ratio = 16 / 9
    """
    The endorced aspect ratio of the viewport. When specified back borders
    will be calulcated both vertically and horizontally if needed.

    This property can be set to ``None`` to disable the fixed viewport system.

    .. code:: python

        # Default value
        aspect_ratio = 16 / 9
    """
    cursor = True
    """
    Determines if the mouse cursor should be visible inside the window.
    If enabled on some platforms

    .. code:: python

        # Default value
        cursor = True
    """
    samples = 4
    """
    Number of samples to use in multisampling.

    .. code:: python

        # Default value
        samples = 4
    """
    resource_dir = None
    """
    Absolute path to your resource directory containing textures, scenes,
    shaders/programs or data files. The ``load_`` methods in this class will
    look for resources in this path. This attribute can be a ``str`` or
    a ``pathlib.Path``.

    .. code:: python

        # Default value
        resource_dir = None
    """
    log_level = logging.INFO
    """
    Sets the log level for this library using the standard `logging` module.

    .. code:: python

        # Default value
        log_level = logging.INFO
    """
    def __init__(self, ctx: moderngl.Context = None, wnd: BaseWindow = None, timer: BaseTimer = None, **kwargs):
        """Initialize the window config

        Keyword Args:
            ctx (moderngl.Context): The moderngl context
            wnd: The window instance
            timer: The timer instance
        """
        self.ctx = ctx
        self.wnd = wnd
        self.timer = timer

        if self.resource_dir:
            resources.register_dir(Path(self.resource_dir).resolve())

        if not self.ctx or not isinstance(self.ctx, moderngl.Context):
            raise ValueError("WindowConfig requires a moderngl context. ctx={}".format(self.ctx))

        if not self.wnd or not isinstance(self.wnd, BaseWindow):
            raise ValueError("WindowConfig requires a window. wnd={}".format(self.wnd))

    def render(self, time: float, frame_time: float):
        """Renders the assigned effect

        Args:
            time (float): Current time in seconds
            frame_time (float): Delta time from last frame in seconds
        """
        raise NotImplementedError("WindowConfig.render not implemented")

    def resize(self, width: int, height: int):
        """
        Called every time the window is resized
        in case the we need to do internal adjustments.

        Args:
            width (int): width in buffer size (not window size)
            height (int): height in buffer size (not window size)
        """

    def iconify(self, iconified: bool):
        """
        Called when the window is minimized/iconified
        or restored from this state

        Args:
            iconified (bool): If ``True`` the window is iconified/minimized. Otherwise restored.
        """

    def key_event(self, key: Any, action: Any, modifiers: KeyModifiers):
        """
        Called for every key press and release.
        Depending on the library used, key events may
        trigger repeating events during the pressed duration
        based on the configured key repeat on the users
        operating system.

        Args:
            key: The key that was press. Compare with self.wnd.keys.
            action: self.wnd.keys.ACTION_PRESS or ACTION_RELEASE
            modifiers: Modifier state for shift and ctrl
        """

    def mouse_position_event(self, x: int, y: int, dx: int, dy: int):
        """Reports the current mouse cursor position in the window

        Args:
            x (int): X postion of the mouse cursor
            y Iint): Y position of the mouse cursor
            dx (int): X delta postion
            dy Iint): Y delta position
        """

    def mouse_drag_event(self, x: int, y: int, dx: int, dy: int):
        """Called when the mouse is moved while a button is pressed.

        Args:
            x (int): X postion of the mouse cursor
            y (int): Y position of the mouse cursor
            dx (int): X delta postion
            dy Iint): Y delta position
        """

    def mouse_press_event(self, x: int, y: int, button: int):
        """Called when a mouse button in pressed

        Args:
            x (int): X position the press occured
            y (int): Y position the press occured
            button (int): 1 = Left button, 2 = right button
        """

    def mouse_release_event(self, x: int, y: int, button: int):
        """Called when a mouse button in released

        Args:
            x (int): X position the release occured
            y (int): Y position the release occured
            button (int): 1 = Left button, 2 = right button
        """

    def mouse_scroll_event(self, x_offset: float, y_offset: float):
        """Called when the mouse wheel is scrolled.

        Some input devices also support horisontal scrolling,
        but vertical scrolling is fairly universal.

        Args:
            x_offset (int): X scroll offset
            y_offset Iint): Y scroll offset
        """

    def unicode_char_entered(self, char: str):
        """Called when the user entered a unicode character.

        Args:
            char (str): The character entered
        """

    def load_texture_2d(self, path: str, flip=True, mipmap=False, mipmap_levels: Tuple[int, int] = None,
                        anisotropy=1.0, **kwargs) -> moderngl.Texture:
        """Loads a 2D texture

        Args:
            path (str): Path to the texture relative to search directories
        Keyword Args:
            flip (boolean): Flip the image horisontally
            mipmap (bool): Generate mipmaps. Will generate max possible levels unless
                           `mipmap_levels` is defined.
            mipmap_levels (tuple): (base, max_level) controlling mipmap generation.
                                   When defined the `mipmap` parameter is automatically `True`
            anisotropy (float): Number of samples for anisotropic filtering
            **kwargs: Additonal parameters to TextureDescription
        Returns:
            moderngl.Texture: Texture instance
        """
        return resources.textures.load(TextureDescription(
            path=path,
            flip=flip,
            mipmap=mipmap,
            mipmap_levels=mipmap_levels,
            anisotropy=anisotropy,
            **kwargs,
        ))

    def load_texture_array(self, path: str, layers: int = 0, flip=True,
                           mipmap=False, mipmap_levels: Tuple[int, int] = None,
                           anisotropy=1.0, **kwargs) -> moderngl.TextureArray:
        """Loads a texture array.

        Args:
            path (str): Path to the texture relative to search directories
        Keyword Args:
            layers (int): How many layers to split the texture into vertically
            flip (boolean): Flip the image horisontally
            mipmap (bool): Generate mipmaps. Will generate max possible levels unless
                           `mipmap_levels` is defined.
            mipmap_levels (tuple): (base, max_level) controlling mipmap generation.
                                   When defined the `mipmap` parameter is automatically `True`
            anisotropy (float): Number of samples for anisotropic filtering

            **kwargs: Additonal parameters to TextureDescription
        Returns:
            moderngl.TextureArray: The texture instance
        """
        if not kwargs:
            kwargs = {}

        if 'kind' not in kwargs:
            kwargs['kind'] = "array"

        return resources.textures.load(TextureDescription(
            path=path,
            layers=layers,
            flip=flip,
            mipmap=mipmap,
            mipmap_levels=mipmap_levels,
            anisotropy=anisotropy,
            **kwargs
        ))

    def load_program(self, path=None, vertex_shader=None, geometry_shader=None, fragment_shader=None,
                     tess_control_shader=None, tess_evaluation_shader=None) -> moderngl.Program:
        """Loads a shader program.

        Note that `path` should only be used if all shaders are defined
        in the same glsl file separated by defines.

        Keyword Args:
            path (str): Path to a single glsl file
            vertex_shader (str): Path to vertex shader
            geometry_shader (str): Path to geometry shader
            fragment_shader (str): Path to fragment shader
            tess_control_shader (str): Path to tessellation control shader
            tess_evaluation_shader (str): Path to tessellation eval shader
        Returns:
            moderngl.Program: The program instance
        """
        return resources.programs.load(
            ProgramDescription(
                path=path,
                vertex_shader=vertex_shader,
                geometry_shader=geometry_shader,
                fragment_shader=fragment_shader,
                tess_control_shader=tess_control_shader,
                tess_evaluation_shader=tess_evaluation_shader,
            )
        )

    def load_text(self, path: str, **kwargs) -> str:
        """Load a text file.

        Args:
            path (str): Path to the file relative to search directories
            **kwargs: Additional parameters to DataDescription
        Returns:
            str: Contents of the text file
        """
        if not kwargs:
            kwargs = {}

        if 'kind' not in kwargs:
            kwargs['kind'] = 'text'

        return resources.data.load(DataDescription(path=path, **kwargs))

    def load_json(self, path: str, **kwargs) -> dict:
        """Load a json file

        Args:
            path (str): Path to the file relative to search directories
            **kwargs: Additional parameters to DataDescription
        Returns:
            dict: Contents of the json file
        """
        if not kwargs:
            kwargs = {}

        if 'kind' not in kwargs:
            kwargs['kind'] = 'json'

        return resources.data.load(DataDescription(path=path, **kwargs))

    def load_binary(self, path: str, **kwargs) -> bytes:
        """Load a file in binary mode.

        Args:
            path (str): Path to the file relative to search directories
            **kwargs: Additional parameters to DataDescription
        Returns:
            bytes: The byte data of the file
        """
        if not kwargs:
            kwargs = {}

        if 'kind' not in kwargs:
            kwargs['kind'] = 'binary'

        return resources.data.load(DataDescription(path=path, kind="binary"))

    def load_scene(self, path: str, cache=False, attr_names=AttributeNames,
                   kind=None, **kwargs) -> Scene:
        """Loads a scene.

        Keyword Args:
            path (str): Path to the file relative to search directories
            cache (str): Use the loader caching system if present
            attr_names (AttributeNames): Attrib name config
            kind (str): Override loader kind
            **kwargs: Additional parameters to SceneDescription
        Returns:
            Scene: The scene instance
        """
        return resources.scenes.load(SceneDescription(
            path=path,
            cache=cache,
            attr_names=attr_names,
            kind=kind,
            **kwargs,
        ))


def dummy_func(*args, **kwargs) -> None:
    """Dummy function used as the default for callbacks"""
    pass
