import keyboard
from typing import Callable

class ShortcutHandler():
    """
    Handles keybindings for the application. Can set keybindings for key press and key release to
    call any functions or class methods (using lambda functions) when the keybinding is pressed or released.
    
    Note:
        - For usage with game controllers, you can remap the controller buttons to keyboard keys using
            third-party softwares like JoyToKey.
        - The ShortcutHandler is to be used in the main_controller.py file, and the keybindings are to be
            set in the config_shortcuts.py file.
    """
    def __init__(self):
        self._key_states_press = {}
    
    def set_keybinding_presshold(self, keybinding:str, callback:Callable):
        """
        Set a keybinding for the application for a key press that is continuously 
        called while the key is held down

        Args:
            keybinding (str): keybinding to be set
            callback (Callable): function to be called when keybinding is pressed
        """
        if not isinstance(keybinding, str) or keybinding == '': return
        keyboard.add_hotkey(keybinding, callback,trigger_on_release=False,suppress=True)
    
    def set_keybinding_press(self, keybinding:str, callback:Callable):
        """
        Set keybindings for the application for a key press
        
        Args:
            keybinding (str), keybinding to be set
            callback (Callable), function to be called when keybinding is pressed
        """
        if not isinstance(keybinding, str) or keybinding == '': return
        def on_key_press():
            if not self._key_states_press.get(keybinding):  # Check if key is already pressed
                self._key_states_press[keybinding] = True
                callback()

        def on_key_release():
            self._key_states_press[keybinding] = False

        keyboard.add_hotkey(keybinding, on_key_press,trigger_on_release=False,suppress=True)
        keyboard.add_hotkey(keybinding, on_key_release,trigger_on_release=True,suppress=True)
        
    def set_keybinding_release(self, keybinding:str, callback:Callable):
        """
        Set keybindings for the application for a key release
        
        Args:
            keybinding (str), keybinding to be set
            callback (Callable), function to be called when keybinding is released
        """
        if not isinstance(keybinding, str) or keybinding == '': return
        def on_key_release():
            self._key_states_press[keybinding] = False
            callback()

        keyboard.add_hotkey(keybinding, on_key_release,trigger_on_release=True,suppress=True)
        
if __name__ == '__main__':
    import tkinter as tk

    class tplvl(tk.Toplevel):
        def __init__(self, master):
            super().__init__(master)
            
        def hello(self):
            print('Toplevel: Hello World')
            
        def bye(self):
            print('Toplevel: Goodbye')

    class frm(tk.Frame):
        def __init__(self, master):
            super().__init__(master)
            
        def hello(self):
            print('Frame: Hello World')
            
        def bye(self):
            print('Frame: Goodbye')
            
    root = tk.Tk()
    frame = frm(root)
    frame.pack()

    toplevel = tplvl(root)

    sh = ShortcutHandler()

    sh.set_keybinding_press('a', frame.hello)
    sh.set_keybinding_press('s', toplevel.hello)

    sh.set_keybinding_release('a', frame.bye)
    sh.set_keybinding_release('s', toplevel.bye)

    root.mainloop()