from shell_lite.compiler.runtime_lib import *
__SHL_MODULES = {}

def main():

    def m_16d9b51e2b0b_db_open(path):
        return std_db_open(path)

    def m_16d9b51e2b0b_db_close():
        std_db_close()

    def m_16d9b51e2b0b_db_exec(sql, params):
        return std_db_exec(sql, params)

    def m_16d9b51e2b0b_db_query(sql, params):
        return std_db_query_rows(sql, params)
if __name__ == '__main__':
    main()