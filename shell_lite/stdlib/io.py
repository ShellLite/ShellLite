from shell_lite.compiler.runtime_lib import *

__SHL_MODULES = {}


def main():

    def m_d9cb0ed438f8_read(path):
        return std_io_read(path)

    def m_d9cb0ed438f8_write(path, content):
        std_io_write(path, content)

    def m_d9cb0ed438f8_append(path, content):
        std_io_append(path, content)

    def m_d9cb0ed438f8_exists(path):
        return std_io_exists(path)

    def m_d9cb0ed438f8_delete(path):
        std_io_delete(path)

    def m_d9cb0ed438f8_copy(src, dest):
        std_io_copy(src, dest)

    def m_d9cb0ed438f8_rename(old, new):
        std_io_rename(old, new)

    def m_d9cb0ed438f8_mkdir(path):
        std_io_mkdir(path)

    def m_d9cb0ed438f8_listdir(path):
        return std_io_listdir(path)


if __name__ == "__main__":
    main()
