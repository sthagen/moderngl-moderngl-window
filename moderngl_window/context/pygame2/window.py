from typing import Tuple
import pygame
import pygame.display
import pygame.event

from moderngl_window.context.base import BaseWindow
from moderngl_window.context.pygame2.keys import Keys


class Window(BaseWindow):
    """
    Basic window implementation using pygame2.
    """
    #: Name of the window
    name = 'pygame2'
    #: pygame specific key constants
    keys = Keys

    _mouse_button_map = {
        1: 1,
        3: 2,
        2: 3,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        pygame.display.init()

        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, self.gl_version[0])
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, self.gl_version[1])
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_FORWARD_COMPATIBLE_FLAG, 1)
        pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)
        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)

        if self.samples > 1:
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, self.samples)

        self._depth = 24
        self._flags = pygame.OPENGL | pygame.DOUBLEBUF
        if self.fullscreen:
            self._flags |= pygame.FULLSCREEN

            info = pygame.display.Info()
            desktop_size = info.current_w, info.current_h
            self._width, self._height = desktop_size
            self._buffer_width, self._buffer_height = self._width, self._height
        else:
            if self.resizable:
                self._flags |= pygame.RESIZABLE

        self._set_mode()
        self.title = self._title
        self.cursor = self._cursor
        self.init_mgl_context()
        self.set_default_viewport()

    def _set_mode(self):
        self._surface = pygame.display.set_mode(
            size=(self._width, self._height),
            flags=self._flags,
            depth=self._depth,
        )

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
        self._width, self._height = value
        self._set_mode()
        self.resize(value[0], value[1])

    @property
    def position(self) -> Tuple[int, int]:
        """Tuple[int, int]: The current window position.

        This property can also be set to move the window::

            # Move window to 100, 100
            window.position = 100, 100
        """
        # FIXME: pygame don't seem to support this
        return (0, 0)

    @position.setter
    def position(self, value: Tuple[int, int]):
        # FIXME: pygame don't seem to support this
        pass

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
        pygame.mouse.set_visible(value)
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
        if self._cursor:
            self.cursor = False

        pygame.event.set_grab(value)
        self._mouse_exclusivity = value

    @property
    def title(self) -> str:
        """str: Window title.

        This property can also be set::

            window.title = "New Title"
        """
        return self._title

    @title.setter
    def title(self, value: str):
        pygame.display.set_caption(value)
        self._title = value

    def swap_buffers(self) -> None:
        """Swap buffers, set viewport, trigger events and increment frame counter"""
        pygame.display.flip()
        self.set_default_viewport()
        self.process_events()
        self._frames += 1

    def resize(self, width, height) -> None:
        """Resize callback

        Args:
            width: New window width
            height: New window height
        """
        self._width = width
        self._height = height
        self._buffer_width, self._buffer_height = self._width, self._height
        self.set_default_viewport()

        super().resize(self._buffer_width, self._buffer_height)

    def close(self):
        """Close the window"""
        super().close()
        self._close_func()

    def _handle_mods(self) -> None:
        """Update key mods"""
        mods = pygame.key.get_mods()
        self._modifiers.shift = mods & pygame.KMOD_SHIFT
        self._modifiers.ctrl = mods & pygame.KMOD_CTRL
        self._modifiers.alt = mods & pygame.KMOD_ALT

    def process_events(self) -> None:
        """Handle all queued events in pygame2 dispatching events to standard methods"""

        for event in pygame.event.get():
            if event.type == pygame.MOUSEMOTION:
                self._handle_mods()
                if self.mouse_states.any:
                    self._mouse_drag_event_func(
                        event.pos[0], event.pos[1],
                        event.rel[0], event.rel[1],
                    )
                else:
                    self._mouse_position_event_func(
                        event.pos[0], event.pos[1],
                        event.rel[0], event.rel[1],
                    )

            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_mods()
                button = self._mouse_button_map.get(event.button, None)
                if button is not None:
                    self._handle_mouse_button_state_change(button, True)
                    self._mouse_press_event_func(
                        event.pos[0], event.pos[1],
                        button,
                    )

            elif event.type == pygame.MOUSEBUTTONUP:
                self._handle_mods()
                button = self._mouse_button_map.get(event.button, None)
                if button is not None:
                    self._handle_mouse_button_state_change(button, False)
                    self._mouse_release_event_func(
                        event.pos[0], event.pos[1],
                        button,
                    )

            elif event.type in [pygame.KEYDOWN, pygame.KEYUP]:
                self._handle_mods()

                if self._exit_key is not None and event.key == self._exit_key:
                    self.close()

                if event.type == pygame.KEYDOWN:
                    self._key_pressed_map[event.key] = True
                elif event.type == pygame.KEYUP:
                    self._key_pressed_map[event.key] = False

                self._key_event_func(event.key, event.type, self._modifiers)

            elif event.type == pygame.TEXTINPUT:
                self._handle_mods()
                self._unicode_char_entered_func(event.text)

            elif event.type == pygame.MOUSEWHEEL:
                self._handle_mods()
                self._mouse_scroll_event_func(float(event.x), float(event.y))

            elif event.type == pygame.QUIT:
                self.close()

            elif event.type == pygame.VIDEORESIZE:
                self.resize(event.size[0], event.size[1])

            elif event.type == pygame.ACTIVEEVENT:

                # # We might support these in the future
                # Mouse cursor state
                # if event.state == 0:
                #     if event.gain:
                #         print("Mouse enters viewport")
                #     else:
                #         print("Mouse leaves viewport")

                # Window focus state
                # if event.state == 1:
                #     if event.gain:
                #         print("Window gained focus")
                #     else:
                #         print("Window lost focus")

                # Window iconify state
                if event.state == 2:
                    if event.gain:
                        self._iconify_func(False)
                    else:
                        self._iconify_func(True)

            # This is also a problem on linux, but is too disruptive during resize events
            # elif event.type == pygame.VIDEOEXPOSE:
            #     # On OS X we only get VIDEOEXPOSE when restoring the windoe
            #     self._iconify_func(False)

    def destroy(self) -> None:
        """Gracefully close the window"""
        pygame.quit()
