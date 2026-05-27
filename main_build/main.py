from .__shl_runtime__ import *
__SHL_MODULES = {}
import subprocess
import os
import os.path as path
import random
from .compiler_v2 import *
std_web_serve_static('/static', 'public')

def PageMetadata(title_text):

    def __shl_tmp_16_body():
        title(title_text)
        link(rel='stylesheet', href='/static/style.css?v=0.6.1')
        meta(charset='utf-8')
        meta(name='viewport', content='width=device-width, initial-scale=1.0')
    head(body=__shl_tmp_16_body)

def LandingPageMetadata(title_text):

    def __shl_tmp_17_body():
        title(title_text)
        link(rel='stylesheet', href='/static/style.css?v=0.6.1')
        meta(charset='utf-8')
        meta(name='viewport', content='width=device-width, initial-scale=1.0')

        def __shl_tmp_18_body():
            """{"@context": "https://schema.org", "@type": "SoftwareApplication", "name": "ShellLite", "applicationCategory": "DeveloperApplication", "operatingSystem": "Cross-platform", "url": "https://shelllite.tech", "author": { "@type": "Person", "name": "Shrey Naithani", "url": "https://shreyn.tech" }, "description": "An English like programming language designed for human readability and native LLVM performance.", "license": "https://www.gnu.org/licenses/gpl-3.0.html", "softwareVersion": "0.6.0", "offers": { "@type": "Offer", "price": "0.00", "priceCurrency": "USD" }, "codeRepository": "https://github.com/ShellLite/ShellLite"}"""
        script(type='application/ld+json', body=__shl_tmp_18_body)
    head(body=__shl_tmp_17_body)

def GlobalNavigation():

    def __shl_tmp_19_body():

        def __shl_tmp_20_body():

            def __shl_tmp_21_body():
                div('ShellLite', class='logo')

                def __shl_tmp_22_body():
                    a('Home', href='/')
                    a('Compiler', href='/compiler')
                    a('Docs', href='/docs')
                    a('Contact', href='/contact')
                    a('GitHub', href='https://github.com/ShellLite/ShellLite')
                div(class='nav-links', body=__shl_tmp_22_body)
            nav(body=__shl_tmp_21_body)
        div(class='container', body=__shl_tmp_20_body)
    header(body=__shl_tmp_19_body)

def UniversalFooter():

    def __shl_tmp_23_body():

        def __shl_tmp_24_body():

            def __shl_tmp_25_body():
                span('This website was written using ')
                strong('ShellLite.')
                span(' Code like you think!', style='font-style: italic; color: #60a5fa;')
            p(body=__shl_tmp_25_body)
            p('© 2025-Present Shrey Naithani', style='font-size: 0.8em; margin-top: 10px;')
        div(class='container', body=__shl_tmp_24_body)
    footer(body=__shl_tmp_23_body)

def LandingPage():

    def __shl_tmp_26_body():
        LandingPageMetadata('ShellLite - Code like you think')

        def __shl_tmp_27_body():
            GlobalNavigation()

            def __shl_tmp_28_body():

                def __shl_tmp_29_body():
                    h1('Code like you think.')
                    p('ShellLite is a programming language designed to be as readable as plain English :)', class='tagline')

                    def __shl_tmp_30_body():
                        a('Try Online Compiler', href='/compiler', class='btn btn-primary')
                        a('Download ShellLite (v0.6.0.P)', href='/static/shl.exe', class='btn btn-outline')
                    div(class='action-buttons', body=__shl_tmp_30_body)
                div(class='container', body=__shl_tmp_29_body)
            div(class='hero', body=__shl_tmp_28_body)

            def __shl_tmp_31_body():
                h2('Publications & Research')

                def __shl_tmp_32_body():

                    def __shl_tmp_33_body():
                        h3('The ShellLite Book')
                        p('Learn the architecture of ShellLite and Natural Language Programming.')

                        def __shl_tmp_34_body():
                            a('Read Now', href='https://books2read.com/b/mVpoXM', class='btn btn-outline')
                        div(style='margin-top: 15px;', body=__shl_tmp_34_body)
                    div(class='card', body=__shl_tmp_33_body)

                    def __shl_tmp_35_body():
                        h3('Research Artifacts')
                        p('Scientific papers detailing the theory of geometric binding and ShellLite.')

                        def __shl_tmp_36_body():
                            a('Geometric Binding Parser', href='https://doi.org/10.5281/zenodo.18385614', class='btn btn-outline')
                            a('Natural Language Programming', href='https://doi.org/10.5281/zenodo.18228699', class='btn btn-outline')
                        div(style='margin-top: 15px; display: flex; flex-direction: column; gap: 10px;', body=__shl_tmp_36_body)
                    div(class='card', body=__shl_tmp_35_body)
                div(class='grid', body=__shl_tmp_32_body)
            div(class='container', style='margin-top: 40px;', body=__shl_tmp_31_body)
            UniversalFooter()
        body(body=__shl_tmp_27_body)
    html(body=__shl_tmp_26_body)

def DocumentationBrowser():

    def __shl_tmp_37_body():

        def __shl_tmp_38_body():
            title('Documentation - ShellLite')
            link(rel='stylesheet', href='/static/style.css?v=0.6.1')
            meta(charset='utf-8')
            meta(name='viewport', content='width=device-width, initial-scale=1.0')
            script(src='https://cdn.jsdelivr.net/npm/3d-force-graph@1/dist/3d-force-graph.min.js')
        head(body=__shl_tmp_38_body)

        def __shl_tmp_39_body():
            GlobalNavigation()

            def __shl_tmp_40_body():
                h1('Documentation')
                p('Master the art of programming in ShellLite!', class='tagline')

                def __shl_tmp_41_body():
                    h2('Visual Learning Path')
                    p('Click a topic to explore. Follow the arrows for recommended learning order.', class='tagline', style='margin-bottom: 20px;')
                    div(id='docs-graph', class='docs-graph-container', style='height: 500px;')
                div(class='graph-section', body=__shl_tmp_41_body)

                def __shl_tmp_42_body():

                    def __shl_tmp_43_body():
                        h3('Essentials')

                        def __shl_tmp_44_body():
                            a('01. Getting Started', href='/docs/01_Getting_Started.md', class='sidebar-link')
                            a('02. Language Basics', href='/docs/02_Language_Basics.md', class='sidebar-link')
                            a('03. Control Flow', href='/docs/03_Control_Flow.md', class='sidebar-link')
                            a('04. Data Structures', href='/docs/04_Data_Structures.md', class='sidebar-link')
                            a('05. Functions & OOP', href='/docs/05_Functions_and_OOP.md', class='sidebar-link')
                        div(class='docs-list', body=__shl_tmp_44_body)
                    div(class='card', body=__shl_tmp_43_body)

                    def __shl_tmp_45_body():
                        h3('Advanced Mastery')

                        def __shl_tmp_46_body():
                            a('06. Modules & StdLib', href='/docs/06_Modules_and_StdLib.md', class='sidebar-link')
                            a('07. System Mastery', href='/docs/07_System_Mastery.md', class='sidebar-link')
                            a('08. Web Development', href='/docs/08_Web_Development.md', class='sidebar-link')
                            a('09. Advanced Features', href='/docs/09_Advanced_Features.md', class='sidebar-link')
                            a('10. Compilation', href='/docs/10_Compilation_and_Performance.md', class='sidebar-link')
                            a('11. Testing & Debugging', href='/docs/11_Testing_and_Debugging.md', class='sidebar-link')
                        div(class='docs-list', body=__shl_tmp_46_body)
                    div(class='card', body=__shl_tmp_45_body)

                    def __shl_tmp_47_body():
                        h3('Reference')

                        def __shl_tmp_48_body():
                            a('12. API Reference', href='/docs/12_API_Reference.md', class='sidebar-link')
                            a('13. Security Guide', href='/docs/13_Security_Guide.md', class='sidebar-link')
                            a('14. Migration Guide', href='/docs/14_Migration_Guide.md', class='sidebar-link')
                            a('15. Troubleshooting', href='/docs/15_Troubleshooting.md', class='sidebar-link')
                            a('16. Examples', href='/docs/16_Examples_and_Tutorials.md', class='sidebar-link')
                            a('17. Best Practices', href='/docs/17_Best_Practices.md', class='sidebar-link')
                        div(class='docs-list', body=__shl_tmp_48_body)
                    div(class='card', body=__shl_tmp_47_body)
                div(class='grid', body=__shl_tmp_42_body)
            div(class='container', style='padding-top: 40px;', body=__shl_tmp_40_body)
            script(src='/static/docs_graph.js')
            UniversalFooter()
        body(body=__shl_tmp_39_body)
    html(body=__shl_tmp_37_body)

def DocumentReader():

    def __shl_tmp_49_body():

        def __shl_tmp_50_body():
            title('Documentation Reader - ShellLite')
            link(rel='stylesheet', href='/static/style.css?v=0.6.1')
            link(rel='stylesheet', href='https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css')
            script(src='https://cdn.jsdelivr.net/npm/marked/marked.min.js')
            script(src='https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js')
            script(src='https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js')
            script(src='/static/doc_viewer.js')
        head(body=__shl_tmp_50_body)

        def __shl_tmp_51_body():
            GlobalNavigation()

            def __shl_tmp_52_body():

                def __shl_tmp_53_body():

                    def __shl_tmp_54_body():
                        p('Loading navigation...', style='color: var(--text-secondary); font-size: 0.8rem;')
                    div(id='sidebar', class='docs-sidebar', body=__shl_tmp_54_body)

                    def __shl_tmp_55_body():

                        def __shl_tmp_56_body():
                            h1('Opening document...')
                            p('Please wait while we fetch the contents.')
                        div(id='content', class='docs-content markdown-body', body=__shl_tmp_56_body)

                        def __shl_tmp_57_body():
                            div(class='nav-btn', id='prev-btn')
                            div(class='nav-btn', id='next-btn')
                        div(id='nav-footer', class='docs-nav-footer', body=__shl_tmp_57_body)
                    div(class='docs-main', body=__shl_tmp_55_body)
                div(class='docs-layout', body=__shl_tmp_53_body)
            div(class='container', body=__shl_tmp_52_body)
            UniversalFooter()
        body(body=__shl_tmp_51_body)
    html(body=__shl_tmp_49_body)

def ContactPage():

    def __shl_tmp_58_body():
        PageMetadata('Contact Us - ShellLite')

        def __shl_tmp_59_body():
            GlobalNavigation()

            def __shl_tmp_60_body():

                def __shl_tmp_61_body():
                    h1('Have questions? We are here to help :)')

                    def __shl_tmp_62_body():

                        def __shl_tmp_63_body():
                            strong('Email: ')
                            span('contact@shelllite.tech')
                        p(body=__shl_tmp_63_body)

                        def __shl_tmp_64_body():
                            strong('GitHub: ')
                            a('Report a bug or request a feature', href='https://github.com/ShellLite/ShellLite/issues')
                        p(body=__shl_tmp_64_body)
                    div(style='margin-top: 40px; text-align: left;', body=__shl_tmp_62_body)
                div(class='card', style='max-width: 700px; margin: 0 auto; text-align: center;', body=__shl_tmp_61_body)
            div(class='container', style='padding-top: 60px; min-height: 70vh;', body=__shl_tmp_60_body)
            UniversalFooter()
        body(body=__shl_tmp_59_body)
    html(body=__shl_tmp_58_body)

def __shl_tmp_65_body():
    LandingPage()
std_web_on_request('/', body=__shl_tmp_65_body)

def __shl_tmp_66_body():
    DocumentationBrowser()
std_web_on_request('/docs', body=__shl_tmp_66_body)

def __shl_tmp_67_body():
    DocumentReader()
std_web_on_request('/docs/:file', body=__shl_tmp_67_body)

def __shl_tmp_68_body():
    ContactPage()
std_web_on_request('/contact', body=__shl_tmp_68_body)
std_web_listen(8080)