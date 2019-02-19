import logging
import sqlite3
import logging
import os
import sys

'''
Calcula a pontuação lattes para cada pesquisador
'''
def calcularScoreLattes(cursor,TABELA):
    consulta = "SELECT B.nome,A.idlattes,A.siape,B.capes from docentes as A,edital_05_2018 as B WHERE A.siape=B.siape ORDER BY nome"
    cursor.execute(consulta)
    i = 1
    for linha in cursor.fetchall():
        idlattes = linha[1]
        siape = linha[2]
        area = linha[3]
        nomeDocente = linha[0]
        logger.info(nomeDocente)
        try:
            #Preparando o parser XML
            tree = ET.parse("../pesquisa/docentes/" + str(idlattes) + ".xml")
            root = tree.getroot()
            score = Score(root,2013, 2018, area, 2016)
            print(score.get_score())
            logger.info(nomeDocente + " - [" + str(score.get_score()) + "]")
            update = "UPDATE " + TABELA + " SET scorelattes=" + str(score.get_score()) + " WHERE siape=" + str(siape)
            cursor.execute(update)
            update = "UPDATE " + TABELA + " SET id=" + str(i) + " WHERE siape=" + str(siape)
            cursor.execute(update)
            i = i + 1
        except:
            e = sys.exc_info()[0]
            logger.error(e)
            

UPLOAD_FOLDER = '/home/perazzo/flask/projetos/pesquisa/static/files'
ALLOWED_EXTENSIONS = set(['pdf','xml'])
WORKING_DIR='/home/perazzo/flask/projetos/pesquisa/'
CURRICULOS_DIR='/home/perazzo/flask/projetos/pesquisa/static/pdf/'
#Obtendo senhas
lines = [line.rstrip('\n') for line in open(WORKING_DIR + 'senhas.pass')]
PASSWORD = lines[0]
GMAIL_PASSWORD = lines[1]
    
#INICIO DO PROGRAMA PRINCIPAL
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
# create a file handler
handler = logging.FileHandler('processar.log')
handler.setLevel(logging.INFO)
# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(handler)
#CONECTANDO AO BANCO DE DADOS
sys.path.append("/home/perazzo/Private/rafael/ufca/software/edital-apoio-05-2018/scoreLattes-master")
from scoreLattes import *
reload(sys)
sys.setdefaultencoding('utf-8')
#CONECTANDO AO BANCO DE DADOS
conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
conn.select_db('pesquisa')
cursor  = conn.cursor()

conn.commit()
conn.close()
