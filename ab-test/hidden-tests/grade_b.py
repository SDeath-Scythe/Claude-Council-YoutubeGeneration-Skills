import sys, os, runpy
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import cases, cases_b
cases.CASES[:] = cases_b.CASES
runpy.run_path(os.path.join(here, 'grade.py'), run_name='__main__')
