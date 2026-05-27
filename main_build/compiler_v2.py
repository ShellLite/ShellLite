from .__shl_runtime__ import *
__SHL_MODULES = {}
import subprocess
import os
import os.path as path
import sys
import hashlib
import time

def CompilerPage():

    def __shl_tmp_1_body():

        def __shl_tmp_2_body():
            title('Interactive Playground - ShellLite')
            link(rel='stylesheet', href='/static/style.css?v=0.6.1')
            meta(charset='utf-8')
            meta(name='viewport', content='width=device-width, initial-scale=1.0')
        head(body=__shl_tmp_2_body)

        def __shl_tmp_3_body():
            GlobalNavigation()

            def __shl_tmp_4_body():

                def __shl_tmp_5_body():

                    def __shl_tmp_6_body():

                        def __shl_tmp_7_body():
                            span('main.shl', style='font-size: 0.85rem; font-weight: 600; color: #94a3b8;')
                        div(style='display: flex; align-items: center; gap: 12px;', body=__shl_tmp_7_body)
                        button('Run', class='run-btn', onclick='runCode()')
                    div(class='compiler-header', body=__shl_tmp_6_body)

                    def __shl_tmp_8_body():

                        def __shl_tmp_9_body():
                            div('1', id='line-numbers', class='line-numbers')

                            def __shl_tmp_10_body():
                                textarea("say 'Welcome to the ShellLite Playground!'", id='code-input', spellcheck='false')
                            div(class='editor-wrapper', body=__shl_tmp_10_body)
                        div(class='editor-pane', body=__shl_tmp_9_body)

                        def __shl_tmp_11_body():

                            def __shl_tmp_12_body():
                                span('TERMINAL')
                                button('CLEAR', class='btn', style='background: transparent; color: #64748b; font-size: 0.7rem; padding: 4px 8px;', onclick='clearOutput()')
                            div(class='output-header', body=__shl_tmp_12_body)
                            div('// Program output will appear here...', id='output-display')
                        div(class='output-pane', body=__shl_tmp_11_body)
                    div(class='compiler-body', body=__shl_tmp_8_body)
                div(class='compiler-container', body=__shl_tmp_5_body)

                def __shl_tmp_13_body():
                    p('Tip: Your code is cached for 10 minutes. Running the same code twice is instant.')
                div(style='margin-top: 20px; color: #64748b; font-size: 0.9rem; text-align: center;', body=__shl_tmp_13_body)
            div(class='container', style='padding-top: 40px;', body=__shl_tmp_4_body)
            script(src='/static/compiler.js')
            UniversalFooter()
        body(body=__shl_tmp_3_body)
    html(body=__shl_tmp_1_body)

def __shl_tmp_14_body():
    CompilerPage()
std_web_on_request('/compiler', body=__shl_tmp_14_body)

def __shl_tmp_15_body():
    received_data = request['json']
    program_code = received_data['code']
    if program_code == '':
        program_code = "say 'Hello World'"
    current_time = time.time()
    for entry in os.listdir('.'):
        if entry.startswith('run_'):
            file_stats = os.stat(entry)
            file_age = current_time - file_stats.st_mtime
            if file_age > 600:
                os.remove(entry)
    content_hash = hashlib.md5(program_code.encode('utf-8')).hexdigest()
    script_filename = mixed_concat(mixed_concat('run_', content_hash), '.shl')
    if path.exists(script_filename) == False:
        std_io_write(script_filename, program_code)
    execution_env = os.environ.copy()
    shell_command = [sys.executable, '-m', 'shell_lite.main', 'run', script_filename]
    final_output = 'Error: Execution failed'
    try:
        execution_result = subprocess.run(shell_command, capture_output=True, text=True, timeout=5, env=execution_env)
        standard_output = execution_result.stdout
        error_output = execution_result.stderr
        final_output = standard_output
        if final_output == '' or final_output == None:
            final_output = error_output
        if final_output != None:
            final_output = final_output.trim()
    except Exception as execution_error:
        final_output = mixed_concat('Execution Error: ', str(execution_error))
    if (final_output == '' or final_output == None) or final_output == 'None':
        final_output = 'Executed successfully (No Output)'
    return final_output
std_web_on_request('/api/run', body=__shl_tmp_15_body)