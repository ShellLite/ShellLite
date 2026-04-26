import os
import sys
import shutil
import winreg
from pathlib import Path
def is_admin():
    try:
        return os.getuid() == 0
    except AttributeError:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
def add_to_path(folder_path):
    folder_path = str(folder_path)
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS)
        try:
            path_val, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            path_val = ""
        if folder_path not in path_val:
            new_path = path_val + ";" + folder_path + ";" if path_val else folder_path + ";"
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
            print(f"Added {folder_path} to User PATH.")
        else:
            print(f"{folder_path} is already in PATH.")
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Failed to set PATH: {e}")
        return False
def install():
    print("Installing ShellLite...")
    appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
    install_dir = Path(appdata) / "ShellLite"
    bin_path = install_dir / "shl.exe"
    if not install_dir.exists():
        install_dir.mkdir(parents=True)
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    source_exe = Path(base_path) / "shl.exe"
    if not source_exe.exists():
        source_exe = Path(base_path) / "dist" / "shl.exe"
    if not source_exe.exists():
        print(f"Error: shl.exe not found at {source_exe}")
        input("Press Enter to exit...")
        return
    print(f"Copying {source_exe} to {bin_path}...")
    try:
        shutil.copy2(source_exe, bin_path)
        print("Copy successful.")
    except Exception as e:
        print(f"Error copying file: {e}")
    add_to_path(install_dir)
    print("\nInstallation Complete!")
    print("You may need to restart your terminal for 'shl' command to work.")
    input("Press Enter to close...")
if __name__ == "__main__":
    try:
        install()
    except Exception as e:
        print(f"An error occurred: {e}")
        input("Press Enter to close...")
