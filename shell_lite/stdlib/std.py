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

    def m_b9ab84cf522a_get(url):
        return std_net_get(url)

    def m_b9ab84cf522a_post(url, data):
        return std_net_post(url, data)

    def m_1b7f504dbbcc_std_json_parse(s):
        return py_json.loads(s)

    def m_1b7f504dbbcc_std_json_stringify(obj):
        return py_json.dumps(obj)

    def m_16d9b51e2b0b_db_open(path):
        return std_db_open(path)

    def m_16d9b51e2b0b_db_close():
        std_db_close()

    def m_16d9b51e2b0b_db_exec(sql, params):
        return std_db_exec(sql, params)

    def m_16d9b51e2b0b_db_query(sql, params):
        return std_db_query_rows(sql, params)

    def m_10ff7d1e007c_web_on_request(path, handler):
        std_web_on_request(path, handler)

    def m_10ff7d1e007c_web_listen(port):
        std_web_listen(port)

    def m_10ff7d1e007c_web_serve_static(url, folder):
        std_web_serve_static(url, folder)

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
