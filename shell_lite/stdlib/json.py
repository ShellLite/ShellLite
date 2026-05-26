from shell_lite.compiler.runtime_lib import *
__SHL_MODULES = {}

def main():

    def m_1b7f504dbbcc_std_json_parse(s):
        return py_json.loads(s)

    def m_1b7f504dbbcc_std_json_stringify(obj):
        return py_json.dumps(obj)
if __name__ == '__main__':
    main()