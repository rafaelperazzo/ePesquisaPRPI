# -*- coding: utf-8 -*-
#https://stackoverflow.com/questions/8329741/issue-with-smtplib-sending-mail-with-unicode-characters-in-python-3-1

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
from email.header import Header

SITE = "https://programacao.ufca.edu.br/pesquisa/avaliacao"
LINK_RECUSA = "https://programacao.ufca.edu.br/pesquisa/"
UPLOAD_FOLDER = '/home/perazzo/flask/projetos/pesquisa/static/files/'
ALLOWED_EXTENSIONS = set(['pdf','xml'])
WORKING_DIR='/home/perazzo/flask/projetos/pesquisa/'
CURRICULOS_DIR='/home/perazzo/flask/projetos/pesquisa/static/files/'
#Obtendo senhas
lines = [line.rstrip('\n') for line in open(WORKING_DIR + 'senhas.pass')]
PASSWORD = lines[0]
GMAIL_PASSWORD = lines[1]

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

def enviarEmail(to,subject,body,html):
    gmail_user = 'pesquisa.prpi@ufca.edu.br'
    gmail_password = GMAIL_PASSWORD
    sent_from = gmail_user
    para = [to]
    msg = MIMEMultipart('alternative')
    part1 = MIMEText(body,'plain','utf-8')
    part2 = MIMEText(html, 'html','utf-8')
    msg['From'] = gmail_user
    msg['To'] = to
    msg['Subject'] = Header(subject, "utf-8")
    msg.attach(part1)
    msg.attach(part2)
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
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    #consulta = "SELECT e.id,e.titulo,e.resumo,a.avaliador,a.link FROM editalProjeto as e, avaliacoes as a WHERE e.id=a.idProjeto AND a.id=21"
    consulta = "SELECT e.id,e.titulo,e.resumo,a.avaliador,a.link,a.id,a.enviado,a.token,e.categoria FROM editalProjeto as e, avaliacoes as a WHERE e.id=a.idProjeto AND e.valendo=1 AND a.finalizado=0 AND a.enviado=0"
    cursor.execute(consulta)
    linhas = cursor.fetchall()
    for linha in linhas:
        titulo = unicode(linha[1])
        resumo = unicode(linha[2])
        email = unicode(linha[3])
        #email = "rafael.mota@ufca.edu.br"
        link = str(linha[4])
        id_avaliacao = str(linha[5])
        enviado = int(linha[6])
        token_avaliacao = unicode(linha[7])
        categoria_projeto = int(linha[8])
        link_recusa = LINK_RECUSA + "recusarConvite?token=" + token_avaliacao
        mensagem = unicode("Título do Projeto: " + titulo + "\n")
        mensagem = mensagem + "Link para avaliação: " + link + " \n"
        mensagem = mensagem + "Resumo do projeto\n" + resumo
        html = "<html><body>\n"
        html = html + "<h4><center>Universidade Federal do Cariri (UFCA) - Coordenadoria de Pesquisa</center></h4><BR>"
        html = html + "<h1><center>Solicitação de Avaliação de Projeto de Pesquisa</center></h1><BR>"
        if categoria_projeto==1:
            html = html + "Prezado(a) senhor(a), <BR>Gostaríamos de convida-lo(a) para avaliação do projeto de pesquisa e/ou plano(s) de trabalho descrito(s) abaixo. Os arquivos relativos ao projeto podem ser acessados no link informado abaixo.<BR>"
        else:
            html = html + "Prezado(a) senhor(a), <BR>Gostaríamos de convida-lo(a) para avaliação do(s) plano(s) de trabalho disponíveis a seguir. Os arquivos relativos ao(s) plano(s) podem ser acessados no link informado abaixo.<BR>"
        html = html + "O projeto está em avaliação para concessão de bolsas de Iniciação Científica e/ou Tecnológica.<BR>"
        html = html + "Quaisquer dúvidas estamos a disposição. A declaração de avaliação é gerada imediatamente após a conclusão da avaliação.<BR>"
        html = html + "<h4>Em caso de indisponibilidade de avaliação, favor <a href=\"" + link_recusa + "\">Clique aqui para recusar o convite</a>" + "</h4><BR>\n"
        html = html + "<h2>Link para envio da avaliação: <a href=\"" + link + "\">Clique Aqui</a></h2><BR>\n"
        html = html + "<h2>Título do projeto: " + titulo + "</h2><BR>\n"
        html = html + "<h3>Resumo do projeto <BR> " + resumo + "</h3><BR>\n"
        html = html + "</body></html>"
        enviarEmail(email,"[UFCA - Solicitação de Avaliação de Projeto de Pesquisa]",mensagem,html)
        print("E-mail enviado para: " + email)
        enviado = enviado + 1
        consulta_enviado = "UPDATE avaliacoes SET enviado=" + str(enviado) + " WHERE id=" + id_avaliacao
        atualizar(consulta_enviado)
        consulta_enviado = "UPDATE avaliacoes SET data_envio=CURRENT_TIMESTAMP() WHERE id=" + id_avaliacao
        atualizar(consulta_enviado)

    conn.close()




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
enviarLinksParaAvaliadores()
