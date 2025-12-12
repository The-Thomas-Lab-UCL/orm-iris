import PySide6.QtWidgets as qw
from PySide6.QtGui import QKeySequence, QShortcut, QKeyEvent # <-- Need QKeyEvent
from PySide6.QtCore import Qt, QObject, QEvent # <-- Need QObject, QEvent
from typing import Callable, Dict

# 1. CHANGE BASE CLASS TO QObject for event filtering
class ShortcutHandler(QObject):
    """
    Handles keybindings for the application by installing itself as an
    application-wide event filter to capture key press and key release events.
    """
    
    # MAPPING for simple keys (used for press/release pairs)
    _KEY_MAP:Dict[str,Qt.Key] = {
        'a': Qt.Key_A, 'b': Qt.Key_B, 'c': Qt.Key_C, 'd': Qt.Key_D, # pyright: ignore[reportAttributeAccessIssue] ; Qt.Key exists
        'e': Qt.Key_E, 'f': Qt.Key_F, 'g': Qt.Key_G, 'h': Qt.Key_H, # pyright: ignore[reportAttributeAccessIssue] ; Qt.Key exists
        'i': Qt.Key_I, 'j': Qt.Key_J, 'k': Qt.Key_K, 'l': Qt.Key_L, # pyright: ignore[reportAttributeAccessIssue] ; Qt.Key exists
        'm': Qt.Key_M, 'n': Qt.Key_N, 'o': Qt.Key_O, 'p': Qt.Key_P, # pyright: ignore[reportAttributeAccessIssue] ; Qt.Key exists
        'q': Qt.Key_Q, 'r': Qt.Key_R, 's': Qt.Key_S, 't': Qt.Key_T, # pyright: ignore[reportAttributeAccessIssue] ; Qt.Key exists
        'u': Qt.Key_U, 'v': Qt.Key_V, 'w': Qt.Key_W, 'x': Qt.Key_X, # pyright: ignore[reportAttributeAccessIssue] ; Qt.Key exists
        'y': Qt.Key_Y, 'z': Qt.Key_Z,                               # pyright: ignore[reportAttributeAccessIssue] ; Qt.Key exists
        'up': Qt.Key_Up, 'down': Qt.Key_Down, 'left': Qt.Key_Left, 'right': Qt.Key_Right,   # pyright: ignore[reportAttributeAccessIssue] ; Qt.Key exists
        'space': Qt.Key_Space,  # pyright: ignore[reportAttributeAccessIssue] ; Qt.Key exists
    }
    
    _KEY_MAP_MODIFIERS:Dict[str,Qt.Key] = {
        'ctrl': Qt.ControlModifier, # pyright: ignore[reportAttributeAccessIssue] ; Qt.Key exists
        'shift': Qt.ShiftModifier,  # pyright: ignore[reportAttributeAccessIssue] ; Qt.Key exists
        'alt': Qt.AltModifier,      # pyright: ignore[reportAttributeAccessIssue] ; Qt.Key exists
    }
    
    def __init__(self, parent: QObject):
        # 2. QObject accepts QObject as parent
        super().__init__(parent)
        
        # Store callbacks for key press/release pairs (for motion control)
        self._press_callbacks: Dict[int, Callable] = {}
        self._release_callbacks: Dict[int, Callable] = {}
        
        # Store modifier+key dict for press/release pairs
        self._press_callbacks_modifiers: Dict[tuple[int, int], Callable] = {}
        self._release_callbacks_modifiers: Dict[tuple[int, int], Callable] = {}
        
        # Store QShortcut instances (for key combos like Ctrl+A)
        self._shortcuts: list[QShortcut] = []
    
    # --- Methods for QShortcut Bindings (Key Combos, Press Only) ---
    
    def set_keybinding_press(self, keybinding: str, callback: Callable):
        """
        Sets a press-only keybinding (often a combo like Ctrl+S) using QShortcut.
        These are handled by Qt's built-in mechanism.
        """
        if not isinstance(keybinding, str) or keybinding == '': return
        
        # QShortcut MUST be parented by a QWidget, so we use the parent of this handler
        # (which we assume is a QWidget like QMainWindow).
        if not isinstance(self.parent(), qw.QWidget):
            print("Error: ShortcutHandler's parent must be a QWidget for QShortcut.")
            return

        shortcut = QShortcut(QKeySequence(keybinding), self.parent())
        shortcut.setContext(Qt.ApplicationShortcut) # pyright: ignore[reportAttributeAccessIssue] ; Qt.ApplicationShortcut exists
        shortcut.activated.connect(callback)
        
        self._shortcuts.append(shortcut)
        print(f"[QShortcut] Set: {keybinding}")

    # --- Methods for Raw Event Bindings (Press/Release Pairs) ---
    
    def set_keybinding_press_release(self, key: str, on_press: Callable, on_release: Callable):
        """
        Registers a raw key-down/key-up pair (e.g., 'w') for delegation.
        """
        key_parts = [part.strip() for part in key.lower().split('+')]
        if len(key_parts) > 1: self._register_keybinding_press_release_with_modifier(key_parts, on_press, on_release)
        elif len(key_parts) == 1: self._register_keybinding_press_release_no_modifier(key, on_press, on_release)
        else:
            qw.QMessageBox.warning(None, "Shortcut Error",
                    f"Invalid keybinding string for press/release: '{key}'\n"
                    "Currently, only one modifier keys (e.g., 'ctrl+w') are supported for raw key press/release bindings.\n"
                    "or simple keys without modifiers (e.g., 'w', 'a', 'up')."
                )
            return

    def _register_keybinding_press_release_with_modifier(self, key_parts: list[str], on_press: Callable, on_release: Callable):
        """
        Handles keybinding strings with modifiers (e.g., 'ctrl+w').
        
        Args:
            key_parts (list[str]): List of parts split by '+'.
            on_press (Callable): Callback for key press
            on_release (Callable): Callback for key release
        """
        assert len(key_parts) == 2, "Currently, only one modifier is supported for raw key press/release bindings."
        
        if not any([key_part in self._KEY_MAP_MODIFIERS for key_part in key_parts]):
            qw.QMessageBox.warning(None, "Shortcut Error",
                    f"Invalid modifier in keybinding string for press/release: '{'+'.join(key_parts)}'\n"
                    "Currently supported modifiers are: " + ', '.join(self._KEY_MAP_MODIFIERS.keys())
                )
            return
        
        if key_parts[0] in self._KEY_MAP_MODIFIERS:
            key_modifier = key_parts[0]
            key_main = key_parts[1]
        else:
            key_modifier = key_parts[1]
            key_main = key_parts[0]
        
        if key_main not in self._KEY_MAP:
            qw.QMessageBox.warning(None, "Shortcut Error",
                    f"Invalid main key in keybinding string for press/release: '{key_main}'\n"
                    "Please use simple keys (e.g., 'w', 'a', 'up') for raw bindings."
                )
            return
        
        key_qt = self._KEY_MAP[key_main]
        modifier_flag = self._KEY_MAP_MODIFIERS[key_modifier]
        
        # Store using the bitmask flag
        self._press_callbacks_modifiers[(modifier_flag, key_qt)] = on_press
        self._release_callbacks_modifiers[(modifier_flag, key_qt)] = on_release
        
    def _register_keybinding_press_release_no_modifier(self, key, on_press, on_release):
        """
        Registers a raw key-down/key-up pair (e.g., 'w') for delegation.
        
        Args:
            key (str): The key string (e.g., 'w', 'a', 'up').
            on_press (Callable): Callback for key press
            on_release (Callable): Callback for key release
            
        Raises:
            ValueError: If the key string is invalid.
        """
        key_qt = self._KEY_MAP.get(key.lower(), None)
        if key_qt is None:
            # Using print/exception here as QMessageBox may not be suitable in initialization
            raise ValueError(f'Invalid keybinding string for press/release: {key}')
        
        self._press_callbacks[key_qt] = on_press
        self._release_callbacks[key_qt] = on_release
        print(f"[RawEvent] Set: {key.upper()} (Press/Release)")
    
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """
        Intercepts all application events. Handles raw key press/release events.
        """
        
        # Check for KeyPress or KeyRelease events
        if event.type() not in (QEvent.KeyPress, QEvent.KeyRelease): # pyright: ignore[reportAttributeAccessIssue] ; QEvent.Type exists
            return super().eventFilter(watched, event)
        
        key_event: QKeyEvent = event # pyright: ignore[reportAssignmentType] ; event is QEvent but we know it's QKeyEvent here
        is_release = event.type() == QEvent.KeyRelease # pyright: ignore[reportAttributeAccessIssue] ; QEvent.Type exists
        
        # We only process the initial press and final release events.
        if key_event.isAutoRepeat():
            return False 

        key_code = key_event.key()
        modifiers = key_event.modifiers()

        if modifiers == Qt.NoModifier and key_code in self._press_callbacks: # pyright: ignore[reportAttributeAccessIssue] ; Qt.Modifier exists and is int
            if not is_release:
                self._press_callbacks[key_code]()
            else:
                self._release_callbacks.get(key_code, lambda: None)()
            return True
        elif (modifiers, key_code) in self._press_callbacks_modifiers:
            if not is_release:
                self._press_callbacks_modifiers[(modifiers, key_code)]() # pyright: ignore[reportArgumentType] ; Qt.Modifier is int
            else:
                self._release_callbacks_modifiers.get((modifiers, key_code), lambda: None)() # pyright: ignore[reportArgumentType, reportCallIssue] ; Qt.Modifier is int ; modifiers is int
            return True
                
        return super().eventFilter(watched, event)
        
if __name__ == '__main__':
    from PySide6.QtGui import QCloseEvent, QKeyEvent # <-- Import QKeyEvent
    import PySide6.QtWidgets as qw
    from PySide6.QtCore import Signal, Slot, QTimer, QThread
    
    import sys


    class Dummy_MainWindow(qw.QMainWindow):
        def __init__(self):
            super().__init__()
            
        def hello(self):
            print('Hello World from MainWindow!')
            
        def bye(self):
            print('Goodbye from MainWindow!')
            
        def start_move_y(self):
            print("STAGE: Moving Up (W down)")
            
        def stop_move_y(self):
            print("STAGE: Stopping (W up)")
            
        def start_move_x(self):
            print("STAGE: Moving Right (D down)")
            
        def stop_move_x(self):
            print("STAGE: Stopping (D up)")
            
    root = qw.QApplication(sys.argv)
    mw = Dummy_MainWindow()
    mwdg = qw.QWidget()
    mw.setCentralWidget(mwdg)
    lyt = qw.QVBoxLayout(mwdg)

    # 1. Initialize the handler, passing the QMainWindow as the parent
    shortcuthandler = ShortcutHandler(mw) 
    
    # --- 2. CRITICAL: Install the handler as the application event filter ---
    root.installEventFilter(shortcuthandler)
    
    # --- Test Bindings ---
    
    # A. QShortcut (Press only, for combos/menu actions)
    shortcuthandler.set_keybinding_press('f1', mw.hello)
    shortcuthandler.set_keybinding_press('ctrl+f1', mw.bye)

    # B. Raw Event Handler (Press/Release for continuous motion)
    shortcuthandler.set_keybinding_press_release('ctrl+w', mw.start_move_y, mw.stop_move_y)
    shortcuthandler.set_keybinding_press_release('d', mw.start_move_x, mw.stop_move_x)
    
    mw.show()
    sys.exit(root.exec())