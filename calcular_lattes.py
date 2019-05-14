# -*- coding: utf-8 -*-
import logging
import os
import sys
import MySQLdb
import xml.etree.ElementTree as ET
from modules import scoreLattes as SL

WORKING_DIR='/home/perazzo/pesquisa/'
CURRICULOS_DIR='/home/perazzo/pesquisa/static/files/'
lines = [line.rstrip('\n') for line in open(WORKING_DIR + 'senhas.pass')]
PASSWORD = lines[0]
'''
Calcula a pontuação lattes para cada pesquisador
'''
def calcularScoreLattes(tipo,area,since,until,arquivo):
    #Tipo = 0: Apenas pontuacao; Tipo = 1: Sumário
    pasta = WORKING_DIR + "modules/"
    if tipo==1:
        command = "python " + pasta + "scorerun.py -v -p 2016 -s " +  since + " -u " + until + " \"" + area + "\" " +  arquivo
    else:
        command = "python " + pasta + "scorerun.py -p 2016 -s " +  since + " -u " + until + " \"" + area + "\" " +  arquivo
    s = os.popen(command).read()
    return (s)



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

def lattes_detalhado(codigoEdital):
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    consulta = "SELECT arquivo_lattes,area_capes,id FROM editalProjeto WHERE tipo=" + codigoEdital + " AND valendo=1 ORDER BY nome"
    try:
        cursor.execute(consulta)
        linhas = cursor.fetchall()
        for linha in linhas:
            arquivo = CURRICULOS_DIR + str(linha[0])
            area_capes = str(linha[1])
            idProjeto = str(linha[2])
            producao = "INDISPONIVEL"
            try:
                producao = calcularScoreLattes(1,area_capes,"2014","2019",arquivo)
            except e:
                e = sys.exc_info()[0]
                logging.debug(e)
                print("Não foi possível calcular o lattes do ID: " + idProjeto)
                producao = "INDISPONIVEL"
            finally:
                update = "UPDATE editalProjeto SET scorelattes_detalhado=\"" + producao + "\" WHERE id=" + idProjeto
                atualizar(update)

    except MySQLdb.Error, e:
        e = sys.exc_info()[0]
        logging.debug(e)
        print(e)
    finally:
        conn.close()


codigoEdital = "0"
if (len(sys.argv)>1):
    codigoEdital = str(sys.argv[1])

lattes_detalhado(codigoEdital)
