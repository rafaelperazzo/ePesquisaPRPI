#
# Conteudo do arquivo `wsgi.py`
#
import sys

sys.path.insert(0, "/home/perazzo/flask/projetos/pesquisa/")

from pesquisa import app as application
