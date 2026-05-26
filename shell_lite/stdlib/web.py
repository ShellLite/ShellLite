from shell_lite.compiler.runtime_lib import *

__SHL_MODULES = {}


def main():

    def m_10ff7d1e007c_web_on_request(path, handler):
        std_web_on_request(path, handler)

    def m_10ff7d1e007c_web_listen(port):
        std_web_listen(port)

    def m_10ff7d1e007c_web_serve_static(url, folder):
        std_web_serve_static(url, folder)


if __name__ == "__main__":
    main()
