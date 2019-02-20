# -*- coding: utf-8 -*-
import logging
import os
import sys
import MySQLdb
import xml.etree.ElementTree as ET
from modules import scoreLattes as SL
import smtplib
from email.mime.multipart import MIMEMultipart
from email.MIMEImage import MIMEImage
from email.mime.text import MIMEText

SITE = "https://programacao.ufca.edu.br/pesquisa/avaliacao"

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

def atualizar(consulta):
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.autocommit(False)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    try:
        cursor.execute(consulta)
        conn.commit()
    except MySQLdb.Error, e:
        e = sys.exc_info()[0]
        logging.debug(e)
        conn.rollback()
    finally:
        conn.close()


def gerarLinkAvaliacao():
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    consulta = "SELECT id,idProjeto,token FROM avaliacoes ORDER by id"
    cursor.execute(consulta)
    linhas = cursor.fetchall()
    for linha in linhas:
        id = str(linha[0])
        idProjeto = str(linha[1])
        token = str(linha[2])
        link = SITE + "?id=" + idProjeto + "&token=" + token
        consulta = "UPDATE avaliacoes SET link=\"" + link + "\"" + " WHERE id=" + id
        atualizar(consulta)

    conn.close()

def enviarEmail(to,subject,body):
    gmail_user = 'pesquisa.prpi@ufca.edu.br'
    gmail_password = GMAIL_PASSWORD
    sent_from = gmail_user
    para = [to]
    #msg = MIMEMultipart()
    msg = MIMEText(body)
    msg['From'] = gmail_user
    msg['To'] = to
    msg['Subject'] = subject
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(gmail_user, gmail_password)
        server.sendmail(sent_from, to, msg.as_string())
        server.close()
        logging.debug("E-Mail enviado com sucesso.")
        return (True)
    except:
        e = sys.exc_info()[0]
        logging.debug("Erro ao enviar e-mail: " + str(e))
        return (False)

def enviarLinksParaAvaliadores():
    pass


UPLOAD_FOLDER = '/home/perazzo/flask/projetos/pesquisa/static/files/'
ALLOWED_EXTENSIONS = set(['pdf','xml'])
WORKING_DIR='/home/perazzo/flask/projetos/pesquisa/'
CURRICULOS_DIR='/home/perazzo/flask/projetos/pesquisa/static/files/'
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
reload(sys)
sys.setdefaultencoding('utf-8')

#GERAR LINK PARA AVALIADORES
gerarLinkAvaliacao()
