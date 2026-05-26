from shell_lite.compiler.runtime_lib import *

__SHL_MODULES = {}


def main():

    def m_f6300afc404c_std_automation_click(x, y):
        automation_click(x, y)

    def m_f6300afc404c_std_automation_type(text):
        automation_type(text)

    def m_f6300afc404c_std_automation_press(key):
        automation_press(key)

    def m_f6300afc404c_std_automation_notify(title, message):
        automation_notify(title, message)

    def m_f6300afc404c_std_automation_copy(text):
        clipboard_copy(text)

    def m_f6300afc404c_std_automation_paste():
        return clipboard_paste()


if __name__ == "__main__":
    main()
