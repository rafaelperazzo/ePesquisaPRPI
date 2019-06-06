# -*- coding: utf-8 -*-
#https://stackoverflow.com/questions/89228/calling-an-external-command-in-python
#SELECT sec_to_time(TIMESTAMPDIFF(SECOND,avaliacoes.data_envio,avaliacoes.data_avaliacao)) as tempoAvaliacao FROM avaliacoes;
#SELECT TIMESTAMPDIFF(DAY,avaliacoes.data_envio,avaliacoes.data_avaliacao) as dias FROM avaliacoes;
#SELECT avaliacoes.idProjeto,sum(avaliacoes.finalizado),editalProjeto.titulo FROM avaliacoes,editalProjeto WHERE editalProjeto.tipo=1 and editalProjeto.id=avaliacoes.idProjeto GROUP BY idProjeto;
#SELECT editalProjeto.titulo, (SELECT sum(avaliacoes.finalizado) FROM avaliacoes WHERE avaliacoes.idProjeto=editalProjeto.id) as soma FROM editalProjeto WHERE id=25;
from flask import Flask
from flask import render_template
from flask import request,url_for,send_file,send_from_directory,redirect,flash,Markup,Response,session
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import sqlite3
import MySQLdb
from werkzeug.utils import secure_filename
import os
import string
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.MIMEImage import MIMEImage
from email.mime.text import MIMEText
from email.header import Header
import logging
import sys
import xml.etree.ElementTree as ET
from modules import scoreLattes as SL
import json
import numpy as np
import pdfkit
from functools import wraps

UPLOAD_FOLDER = '/home/perazzo/pesquisa/static/files'
ALLOWED_EXTENSIONS = set(['pdf','xml'])
WORKING_DIR='/home/perazzo/pesquisa/'
PLOTS_DIR = '/home/perazzo/pesquisa/static/plots/'
CURRICULOS_DIR='/home/perazzo/pesquisa/static/files/'
SITE = "https://yoko.pet/pesquisa/static/files/"
IMAGENS_URL = "https://yoko.pet/pesquisa/static/"
DECLARACOES_DIR = '/home/perazzo/pesquisa/pdfs/'
ROOT_SITE = 'https://yoko.pet'

app = Flask(__name__)
auth = HTTPBasicAuth()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CURRICULOS_FOLDER'] = CURRICULOS_DIR
app.config['DECLARACOES_FOLDER'] = DECLARACOES_DIR

## TODO: Preparar o log geral
logging.basicConfig(filename=WORKING_DIR + 'app.log', filemode='w', format='%(asctime)s %(name)s - %(levelname)s - %(message)s',level=logging.DEBUG)

#Obtendo senhas
lines = [line.rstrip('\n') for line in open(WORKING_DIR + 'senhas.pass')]
PASSWORD = lines[0]
GMAIL_PASSWORD = lines[1]
SESSION_SECRET_KEY = lines[2]
app.config['SECRET_KEY'] = SESSION_SECRET_KEY

def removerAspas(texto):
    resultado = texto.replace('"',' ')
    resultado = resultado.replace("'"," ")
    return(resultado)

def calcularScoreLattes(tipo,area,since,until,arquivo):
    #Tipo = 0: Apenas pontuacao; Tipo = 1: Sumário
    pasta = WORKING_DIR + "modules/"
    if tipo==1:
        command = "python " + pasta + "scorerun.py -v -p 2016 -s " +  since + " -u " + until + " \"" + area + "\" " +  arquivo
    else:
        command = "python " + pasta + "scorerun.py -p 2016 -s " +  since + " -u " + until + " \"" + area + "\" " +  arquivo
    s = os.popen(command).read()
    return (s)


def enviarEmail(to,subject,body):
    gmail_user = 'pesquisa.prpi@ufca.edu.br'
    gmail_password = GMAIL_PASSWORD
    sent_from = gmail_user
    para = [to]
    #msg = MIMEMultipart()
    msg = MIMEText(body,'plain','utf-8')
    msg['From'] = gmail_user
    msg['To'] = to
    msg['Subject'] = Header(subject, "utf-8")
    msg['Cc'] = "rafael.mota@ufca.edu.br"
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

def atualizar(consulta):
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.autocommit(True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    try:
        cursor.execute(consulta)
        conn.commit()
    except MySQLdb.Error, e:
        #e = sys.exc_info()[0]
        logging.debug(e)
	logging.debug(consulta)
        #conn.rollback()
    finally:
        cursor.close()
        conn.close()


def id_generator(size=20, chars=string.ascii_uppercase + string.digits + string.ascii_lowercase):
        return ''.join(random.choice(chars) for _ in range(size))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def getData():
    Meses=('janeiro','fevereiro',u'março','abril','maio','junho',
       'julho','agosto','setembro','outubro','novembro','dezembro')
    agora = datetime.date.today()
    dia = agora.day
    mes=(agora.month-1)
    mesExtenso = Meses[mes]
    ano = agora.year
    resultado = str(dia) + " de " + mesExtenso + " de " + str(ano) + "."
    return resultado


def gerarDeclaracao(identificador):
    #CONEXÃO COM BD
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    consulta = "SELECT nome,cpf,modalidade,orientador,projeto,inicio,fim,id,ch FROM alunos WHERE id=" + str(identificador)
    cursor.execute(consulta)
    linha = cursor.fetchone()

    #RECUPERANDO DADOS
    nome = linha[0]
    cpf = linha[1]
    modalidade = linha[2]
    orientador = linha[3]
    projeto = linha[4]
    ch = linha[8]
    vigencia_inicio = linha[5]
    vigencia_fim = linha[6]
    id_projeto = linha[7]
    carga_horaria = linha[8]

    consulta = "INSERT INTO autenticacao (idAluno,codigo,data) VALUES (" + str(identificador) + ",FLOOR(RAND()*(100000000-10000+1))+10000,NOW())"
    cursor.execute(consulta)
    conn.commit()
    conn.close()
    return (linha)

def gerarDeclaracaoOrientador(identificador):
    #CONEXÃO COM BD
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    consulta = "SELECT id,coordenador,siape,titulo,inicio,fim FROM projetos WHERE id=" + identificador
    cursor.execute(consulta)
    linha = cursor.fetchone()
    consultaBolsistas = "SELECT a.nome FROM alunos a, projetos p WHERE a.projeto=p.titulo AND p.id=" + str(identificador)
    cursor.execute(consultaBolsistas)
    bolsistas = cursor.fetchall()
    #Montando lista de bolsistas:
    total_bolsistas = len(bolsistas)
    i = 0
    frase_bolsistas = ""
    for bolsista in bolsistas:
	if i==total_bolsistas: #Se for o ultimo bolsista
		frase_bolsistas = frase_bolsistas + unicode(bolsista[0])
	else: #Se nao for o ultimo bolsista
		frase_bolsistas = frase_bolsistas + unicode(bolsista[0]) + ", "
	i = i + 1
    conn.close()
    return (linha,frase_bolsistas)


def gerarProjetosPorAluno(nome):
    #CONEXÃO COM BD
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    consulta = "SELECT nome,cpf,modalidade,orientador,projeto,inicio,fim,id FROM alunos WHERE nome LIKE " + "\"%" + unicode(nome) + "%\" AND cpf!=\"\" AND projeto!=\"\""
    cursor.execute(consulta)
    linhas = cursor.fetchall()

    conn.close()
    return (linhas)

def gerarProjetosPorOrientador(identificador):
    #CONEXÃO COM BD
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    consulta = "SELECT id,coordenador,titulo,inicio,fim FROM projetos WHERE SIAPE=" + str(identificador)
    cursor.execute(consulta)
    linhas = cursor.fetchall()
    conn.close()
    return (linhas)


def gerarAutenticacao(identificador):
    #CONEXÃO COM BD
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    consulta = "SELECT a.nome,a.cpf,a.modalidade,a.orientador,a.projeto,a.inicio,a.fim,b.codigo FROM alunos a, autenticacao b WHERE a.id=b.idAluno and b.codigo=" + identificador + " ORDER BY b.data DESC LIMIT 1"
    cursor.execute(consulta)
    linha = cursor.fetchone()
    conn.close()
    return (linha)

def getEditaisAbertos():
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    consulta = """SELECT id,nome,DATE_FORMAT(deadline,'%d/%m/%Y - %H:%i') FROM editais WHERE now()<deadline ORDER BY id DESC"""
    cursor.execute(consulta)
    linhas = cursor.fetchall()
    cursor.close()
    conn.close()
    return(linhas)

'''
INÍCIO AUTENTICAÇÃO
**************************************************************
'''
@auth.verify_password
def verify_password(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    try:
        conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
        conn.select_db('pesquisa')
        cursor  = conn.cursor()
        consulta = """SELECT id FROM users WHERE username='""" + username + """' AND password=PASSWORD('""" + password + """')"""
        cursor.execute(consulta)
        total = cursor.rowcount
        if (total==0):
            return (False)
        else:
            return (True)
    except:
        e = sys.exc_info()[0]
        logging.error(e)
        logging.error("ERRO Na função check_auth. Ver consulta abaixo.")
        logging.error(consulta)
    finally:
        cursor.close()
        conn.close()

'''
FIM AUTENTICAÇÃO
**************************************************************
'''

@app.route('/segredo')
@auth.login_required
def secret_page():
    session['username'] = auth.username()
    return (session['username'])

@app.route("/")
def home():
    editaisAbertos = getEditaisAbertos()
    return (render_template('cadastrarProjeto.html',abertos=editaisAbertos))

@app.route("/declaracao", methods=['GET', 'POST'])
def declaracao():
    if request.method == "GET":
        if 'idProjeto' in request.args:
            texto_declaracao = gerarDeclaracao(str(request.args['idProjeto']))
            data_agora = getData()
            try:
                options = {
                    'page-size': 'A4',
                    'margin-top': '20mm',
                    'margin-right': '20mm',
                    'margin-bottom': '20mm',
                    'margin-left': '20mm',
}
                arquivoDeclaracao = app.config['DECLARACOES_FOLDER'] + 'declaracao.pdf'
                #pdfkit.from_string(render_template('a4.html',texto=texto_declaracao,data=data_agora,identificador=texto_declaracao[7],raiz=ROOT_SITE),arquivoDeclaracao)
                #return send_from_directory(app.config['DECLARACOES_FOLDER'], 'declaracao.pdf')
                #return send_file(arquivoDeclaracao, attachment_filename='arquivo.pdf')
            except:
                e = sys.exc_info()[0]
                logging.error(e)
                logging.error(arquivoDeclaracao)
                logging.error("Nao foi possivel gerar o PDF da declaração.")
            finally:
                return render_template('a4.html',texto=texto_declaracao,data=data_agora,identificador=texto_declaracao[7],raiz=ROOT_SITE)
        else:
            logging.debug("Tentativa de gerar declaração, sem o id do projeto!")
            return("OK")

@app.route("/projetosAluno", methods=['GET', 'POST'])
def projetos():
    try:
        projetosAluno = gerarProjetosPorAluno(unicode(request.form['txtNome']))
        return render_template('alunos.html',listaProjetos=projetosAluno)
    except:
        e = sys.exc_info()[0]
        logging.error(e)
        logging.error("Nao foi possivel gerar os projetos do aluno.")
        return("Erro! Não utilize acentos ou caracteres especiais na busca.")

@app.route("/autenticacao", methods=['GET', 'POST'])
def autenticar():
    #dadosAutenticacao = gerarAutenticacao(str(request.form['txtCodigo']))
    #return render_template('autenticacao.html',linha=dadosAutenticacao)
    tipo = int(request.form['tipo'])
    codigo = str(request.form['codigo'])
    if tipo==0:
		return redirect("/pesquisa/orientadorDeclaracao?idProjeto=" + codigo)
    else:
		return redirect("/pesquisa/declaracao?idProjeto=" + codigo)


@app.route("/projetosPorOrientador", methods=['GET', 'POST'])
def projetosOrientador():
    projetosOrientador = gerarProjetosPorOrientador(str(request.form['txtSiape']))
    return render_template('projetos_orientador.html',listaProjetos=projetosOrientador)

@app.route("/orientadorDeclaracao", methods=['GET', 'POST'])
def declaracaoOrientador():
    resultados = gerarDeclaracaoOrientador(str(request.args['idProjeto']))
    texto_declaracao = resultados[0]
    bolsistas = resultados[1]
    data_agora = getData()
    return render_template('orientador.html',texto=texto_declaracao,data=data_agora,identificador=texto_declaracao[0],bolsistas=bolsistas)

@app.route("/cadastrarProjeto", methods=['GET', 'POST'])
def cadastrarProjeto():

    #CADASTRAR DADOS DO PROPONENTE
    tipo = int(request.form['tipo'])
    nome = unicode(request.form['nome'])
    categoria_projeto = int(request.form['categoria_projeto'])
    siape = int(request.form['siape'])
    email = unicode(request.form['email'])
    ua = unicode(request.form['ua'])
    area_capes = unicode(request.form['area_capes'])
    grande_area = unicode(request.form['grande_area'])
    grupo = unicode(request.form['grupo'])
    #CONEXÃO COM BD
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()

    #DADOS PESSOAIS E BÁSICOS DO PROJETO
    consulta = "INSERT INTO editalProjeto (categoria,tipo,nome,siape,email,ua,area_capes,grande_area,grupo,data) VALUES (" + str(categoria_projeto) + "," + str(tipo) + "," +  "\"" + nome + "\"," + str(siape) + "," + "\"" + email + "\"," + "\"" + ua + "\"," + "\"" + area_capes + "\"," + "\"" + grande_area + "\"," + "\"" + grupo + "\"," + "CURRENT_TIMESTAMP())"
    #atualizar(consulta)
    try:
        cursor.execute(consulta)
        conn.commit()
    except MySQLdb.Error, e:
        conn.rollback()
        return(str(e))

    getID = "SELECT LAST_INSERT_ID()"
    cursor.execute(getID)
    ultimo_id = int(cursor.fetchone()[0])
    ultimo_id_str = "%03d" % (ultimo_id)
    if tipo==0:
        tipo_str = "Fluxo Continuo"
    else:
        tipo_str= "Edital"

    if categoria_projeto==0:
        categoria_str = "Projeto em andamento"
    else:
        categoria_str= "Projeto Novo"

    logging.debug("Projeto [" + tipo_str + "] [" + categoria_str + "] com ID: " + ultimo_id_str + " cadastrado. Proponente: " + nome)
    #CADASTRAR DADOS DO PROJETO

    titulo = unicode(request.form['titulo'])
    titulo = removerAspas(titulo)
    validade = int(request.form['validade'])
    palavras_chave = unicode(request.form['palavras_chave'])
    palavras_chave = removerAspas(palavras_chave)
    descricao_resumida = unicode(request.form['descricao_resumida'])
    descricao_resumida = removerAspas(descricao_resumida)
    if 'numero_bolsas' in request.form:
        bolsas = int(request.form['numero_bolsas'])
    else:
        bolsas = 0
    transporte = unicode(request.form['transporte'])
    consulta = "UPDATE editalProjeto SET titulo=\"" + titulo + "\", validade=" + str(validade) + ", palavras=\"" + palavras_chave + "\", resumo=\"" + descricao_resumida + "\", bolsas=" + str(bolsas) +  " WHERE id=" + str(ultimo_id)
    logging.debug("Preparando para atualizar dados do projeto.")
    atualizar(consulta)
    consulta = "UPDATE editalProjeto SET transporte=" + transporte + " WHERE id=" + str(ultimo_id)
    atualizar(consulta)
    inicio = unicode(request.form['inicio'])
    fim = unicode(request.form['fim'])
    consulta = "UPDATE editalProjeto SET inicio=\"" + inicio + "\" WHERE id=" + str(ultimo_id)
    atualizar(consulta)
    consulta = "UPDATE editalProjeto SET fim=\"" + fim + "\" WHERE id=" + str(ultimo_id)
    atualizar(consulta)
    logging.debug("Dados do projeto cadastrados.")
    arquivo_curriculo_lattes = ""
    codigo = id_generator()
    if ('arquivo_lattes' in request.files):
        arquivo_lattes = request.files['arquivo_lattes']
        if arquivo_lattes and allowed_file(arquivo_lattes.filename):
            arquivo_lattes.filename = str(siape) + "_" + codigo + ".xml"
            filename = secure_filename(arquivo_lattes.filename)
            arquivo_lattes.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            caminho = str(app.config['UPLOAD_FOLDER'] + "/" + filename)
            consulta = "UPDATE editalProjeto SET arquivo_lattes=\"" + filename + "\" WHERE id=" + str(ultimo_id)
            arquivo_curriculo_lattes = filename
            atualizar(consulta)
        elif not allowed_file(arquivo_lattes.filename):
    		return ("Arquivo de curriculo lattes não permitido")
    else:
        logging.debug("Não foi incluído um arquivo de curriculo")
    logging.debug("Arquivo lattes cadastrado.")

    if ('arquivo_projeto' in request.files):
        arquivo_projeto = request.files['arquivo_projeto']
        if arquivo_projeto and allowed_file(arquivo_projeto.filename) :
            arquivo_projeto.filename = "projeto_" + ultimo_id_str + "_" + str(siape) + "_" + codigo + ".pdf"
            filename = secure_filename(arquivo_projeto.filename)
            arquivo_projeto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            caminho = str(app.config['UPLOAD_FOLDER'] + "/" + filename)
            consulta = "UPDATE editalProjeto SET arquivo_projeto=\"" + filename + "\" WHERE id=" + str(ultimo_id)
            atualizar(consulta)
            logging.debug("Arquivo de projeto cadastrado.")
        elif not allowed_file(arquivo_projeto.filename):
    		return ("Arquivo de projeto não permitido")
    else:
        logging.debug("Não foi incluído um arquivo de projeto")


    if ('arquivo_plano1' in request.files):

        arquivo_plano1 = request.files['arquivo_plano1']
        if arquivo_plano1 and allowed_file(arquivo_plano1.filename):
            arquivo_plano1.filename = "plano1_" + ultimo_id_str + "_" + str(siape) + "_" + codigo + ".pdf"
            filename = secure_filename(arquivo_plano1.filename)
            arquivo_plano1.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            caminho = str(app.config['UPLOAD_FOLDER'] + "/" + filename)
            consulta = "UPDATE editalProjeto SET arquivo_plano1=\"" + filename + "\" WHERE id=" + str(ultimo_id)
            atualizar(consulta)
            logging.debug("Arquivo Plano 1 cadastrado.")
        elif not allowed_file(arquivo_plano1.filename):
    		return ("Arquivo de plano 1 de trabalho não permitido")
    else:
        logging.debug("Não foi incluído um arquivo de plano 1")


    if ('arquivo_plano2' in request.files):
        arquivo_plano2 = request.files['arquivo_plano2']
        if arquivo_plano2 and allowed_file(arquivo_plano2.filename):
            arquivo_plano2.filename = "plano2_" + ultimo_id_str + "_" + str(siape) + "_" + codigo + ".pdf"
            filename = secure_filename(arquivo_plano2.filename)
            arquivo_plano2.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            caminho = str(app.config['UPLOAD_FOLDER'] + "/" + filename)
            consulta = "UPDATE editalProjeto SET arquivo_plano2=\"" + filename + "\" WHERE id=" + str(ultimo_id)
            atualizar(consulta)
            logging.debug("Arquivo Plano 2 cadastrado.")
        elif not allowed_file(arquivo_plano2.filename):
    		return ("Arquivo de plano 2 de trabalho não permitido")
    else:
        logging.debug("Não foi incluído um arquivo de plano 2")

    #LATTES EM PDF
    if ('arquivo_lattes_pdf' in request.files):
        arquivo_lattes_pdf = request.files['arquivo_lattes_pdf']
        if arquivo_lattes_pdf and allowed_file(arquivo_lattes_pdf.filename):
            arquivo_lattes_pdf.filename = "LATTES_" + ultimo_id_str + "_" + str(siape) + "_" + codigo + ".pdf"
            filename = secure_filename(arquivo_lattes_pdf.filename)
            arquivo_lattes_pdf.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            caminho = str(app.config['UPLOAD_FOLDER'] + "/" + filename)
            consulta = "UPDATE editalProjeto SET arquivo_lattes_pdf=\"" + filename + "\" WHERE id=" + str(ultimo_id)
            atualizar(consulta)
            logging.debug("Arquivo Lattes PDF cadastrado.")
        elif not allowed_file(arquivo_lattes_pdf.filename):
    		return ("Arquivo de LATTES PDF não permitido")
    else:
        logging.debug("Não foi incluído um arquivo de LATTES PDF")

    #ARQUIVO DE COMPROVANTES
    if ('arquivo_comprovantes' in request.files):
        arquivo_comprovantes = request.files['arquivo_comprovantes']
        if arquivo_comprovantes and allowed_file(arquivo_comprovantes.filename):
            arquivo_comprovantes.filename = "Comprovantes_" + ultimo_id_str + "_" + str(siape) + "_" + codigo + ".pdf"
            filename = secure_filename(arquivo_comprovantes.filename)
            arquivo_comprovantes.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            caminho = str(app.config['UPLOAD_FOLDER'] + "/" + filename)
            consulta = "UPDATE editalProjeto SET arquivo_comprovantes=\"" + filename + "\" WHERE id=" + str(ultimo_id)
            atualizar(consulta)
            logging.debug("Arquivo COMPROVANTES cadastrado.")
        elif not allowed_file(arquivo_comprovantes.filename):
    		return ("Arquivo de COMPROVANTES não permitido")
    else:
        logging.debug("Não foi incluído um arquivo de COMPROVANTES")

    #CADASTRAR AVALIADORES SUGERIDOS
    avaliador1_email = unicode(request.form['avaliador1_email'])
    if avaliador1_email!='':
        token = id_generator(40)
        consulta = "INSERT INTO avaliacoes (avaliador,token,idProjeto) VALUES (\"" + avaliador1_email + "\", \"" + token + "\", " + str(ultimo_id) + ")"
        atualizar(consulta)
        logging.debug("Avaliador 1 sugerido cadastrado.")

    avaliador2_email = unicode(request.form['avaliador2_email'])
    if avaliador2_email!='':
        token = id_generator(40)
        consulta = "INSERT INTO avaliacoes (avaliador,token,idProjeto) VALUES (\"" + avaliador2_email + "\", \"" + token + "\", " + str(ultimo_id) + ")"
        atualizar(consulta)
        logging.debug("Avaliador 2 sugerido cadastrado.")

    avaliador3_email = unicode(request.form['avaliador3_email'])
    if avaliador3_email!='':
        token = id_generator(40)
        consulta = "INSERT INTO avaliacoes (avaliador,token,idProjeto) VALUES (\"" + avaliador3_email + "\", \"" + token + "\", " + str(ultimo_id) + ")"
        atualizar(consulta)
        logging.debug("Avaliador 3 sugerido cadastrado.")

    #CALCULANDO scorelattes

    pontuacao = -100
    sumario = "---"
    try:
        logging.debug("Iniciando o cálculo do scorelattes...")
        s = calcularScoreLattes(0,area_capes,"2014","2019",CURRICULOS_DIR + arquivo_curriculo_lattes)
        pontuacao = float(s)
        sumario = calcularScoreLattes(1,area_capes,"2014","2019",CURRICULOS_DIR + arquivo_curriculo_lattes)
        logging.debug("Calculo do scorelattes finalizado com sucesso.")
    except:
        e = sys.exc_info()[0]
        logging.error(e)
        logging.error(CURRICULOS_DIR + arquivo_curriculo_lattes)
        pontuacao = -1
        logging.error("Nao foi possivel calcular o scorelattes.")

    try:
        consulta = "UPDATE editalProjeto SET scorelattes=" + str(pontuacao) + " WHERE id=" + str(ultimo_id)
        atualizar(consulta)
        logging.debug("Procedimento de atualizacao do scorelattes para o ID: " + ultimo_id_str + " finalizado com sucesso.")
    except:
        e = sys.exc_info()[0]
        logging.error(e)
        logging.error("Procedimento para o ID: " + ultimo_id_str + " finalizado. Erros ocorreram ao tentar atualizar o scorelattes.")
    finally:
        cursor.close()
        conn.close()

    try:
        #ENVIAR E-MAIL DE CONFIRMAÇÃO
        Texto_email = "Projeto [" + tipo_str + "] [" + categoria_str + "] com ID: " + ultimo_id_str + " cadastrado. Proponente: " + nome
        if enviarEmail(email,u"[PIICT - CONFIRMACAO] - Cadastro de Projeto de Pesquisa",Texto_email):
            logging.debug("E-mail de confirmacao enviado com sucesso.")
            return ("E-mail de confirmação enviado com sucesso.<BR>ID do seu projeto: " + str(ultimo_id))
        else:
            logging.error("Nao foi possivel enviar e-mail de confirmacao.[" + str(ultimo_id) + "]")
            return("Não foi possível enviar o e-mail de confirmação. Anote o ID de seu projeto: " + str(ultimo_id))
    except:
        e = sys.exc_info()[0]
        logging.error(e)
        logging.error("Procedimento para o ID: " + ultimo_id_str + " finalizado. Erros ocorreram ao enviar e-mail.")
    finally:
        #return("Projeto cadastrado com sucesso! Anote o ID de seu projeto: " + str(ultimo_id))
        return (render_template('confirmacao_submissao.html',email_proponente=email,id_projeto=ultimo_id,proponente=nome,titulo_projeto=titulo,resumo_projeto=descricao_resumida,score=pontuacao))

@app.route("/score", methods=['GET', 'POST'])
def getScoreLattesFromFile():
    codigo = id_generator()
    arquivo_curriculo_lattes = ""
    area_capes = unicode(request.form['area_capes'])
    if ('arquivo_lattes' in request.files):
        arquivo_lattes = request.files['arquivo_lattes']
        if arquivo_lattes and allowed_file(arquivo_lattes.filename):
            arquivo_lattes.filename = "000_CONSULTA" + "_" + codigo + ".xml"
            filename = secure_filename(arquivo_lattes.filename)
            arquivo_lattes.save(os.path.join(app.config['CURRICULOS_FOLDER'], filename))
            caminho = str(app.config['CURRICULOS_FOLDER'] + "/" + filename)

            arquivo_curriculo_lattes = filename

        elif not allowed_file(arquivo_lattes.filename):
    		return ("Arquivo de curriculo lattes não permitido")
    else:
        return("Não foi incluído um arquivo de curriculo")

    #CALCULANDO scorelattes
    pontuacao = -100
    try:
        s = calcularScoreLattes(1,area_capes,"2014","2019",CURRICULOS_DIR + arquivo_curriculo_lattes)
        return(s)
    except:
        e = sys.exc_info()[0]
        logging.error("[SCORELATTES] Erro ao calcular o scorelattes.")
        logging.error(e)
        pontuacao = -1
        return("Erro ao calcular pontuacao! Favor, comunicar para o e-mail: atendimento.prpi@ufca.edu.br")

#Devolve os nomes dos arquivos do projeto e dos planos, caso existam
def getFiles(idProjeto):
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    consulta = "SELECT arquivo_projeto,arquivo_plano1,arquivo_plano2 FROM editalProjeto WHERE id=" + idProjeto
    cursor.execute(consulta)
    linha = cursor.fetchone()
    conn.close()
    return(linha)

def naoEstaFinalizado(token):
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    consulta = "SELECT finalizado FROM avaliacoes WHERE token=\"" + token + "\""
    cursor.execute(consulta)
    linha = cursor.fetchone()
    finalizado = int(linha[0])
    conn.close()
    if finalizado==0:
        return (True)
    else:
        return (False)

def podeAvaliar(idProjeto):
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    #consulta = "SELECT deadline_avaliacao,CURRENT_TIMESTAMP() FROM editais WHERE CURRENT_TIMESTAMP()<deadline_avaliacao AND id=" + codigoEdital
    consulta = "SELECT e.id as codigoEdital,e.deadline_avaliacao,p.id FROM editais e, editalProjeto p WHERE p.tipo=e.id and deadline_avaliacao>CURRENT_TIMESTAMP() AND p.id=" + idProjeto
    cursor.execute(consulta)
    total = cursor.rowcount
    conn.close()
    if (total==0): #Edital com avaliacoes encerradas
        return(False)
    else: #Edital com avaliacoes em andamento
        return(True)

#Gerar pagina de avaliacao (testes) para o avaliador
@app.route("/testes", methods=['GET', 'POST'])
def getPaginaAvaliacaoTeste():
    arquivos = "TESTE"
    return render_template('avaliacao.html',arquivos=arquivos)

#Gerar pagina de avaliacao para o avaliador
@app.route("/avaliacao", methods=['GET', 'POST'])
def getPaginaAvaliacao():
    if request.method == "GET":
        idProjeto = str(request.args.get('id'))
        if podeAvaliar(idProjeto): #Se ainda está no prazo para receber avaliações
            tokenAvaliacao = str(request.args.get('token'))
            arquivos = getFiles(idProjeto)
            if str(arquivos[0])!="0":
                link_projeto = SITE + str(arquivos[0])
            if str(arquivos[1])!="0":
                link_plano1 = SITE + str(arquivos[1])
            if str(arquivos[2])!="0":
                link_plano2 = SITE + str(arquivos[2])
            links = ""
            if 'link_projeto' in locals():
                links = links + "<a href=\"" + link_projeto + "\">PROJETO</a><BR>"
            if 'link_plano1' in locals():
                links = links + "<a href=\"" + link_plano1 + "\">PLANO DE TRABALHO 1</a><BR>"
            if 'link_plano2' in locals():
                links = links + "<a href=\"" + link_plano2 + "\">PLANO DE TRABALHO 2</a><BR>"
            links = links + "<input type=\"hidden\" id=\"token\" name=\"token\" value=\"" + tokenAvaliacao + "\">"
            links = Markup(links)
            if naoEstaFinalizado(tokenAvaliacao):
                consulta = "UPDATE avaliacoes SET aceitou=1 WHERE token=\"" + tokenAvaliacao + "\""
                atualizar(consulta)
                return render_template('avaliacao.html',arquivos=links)
            else:
                logging.debug("[AVALIACAO] Tentativa de reavaliar projeto")
                return("Projeto já foi avaliado! Não é possível modificar a avaliação!")
        else:
            return("Prazo de avaliação expirado!")
#Gravar avaliacao gerada pelo avaliador
@app.route("/avaliar", methods=['GET', 'POST'])
def enviarAvaliacao():
    if request.method == "POST":
        comentarios = unicode(request.form['txtComentarios'])
        recomendacao = str(request.form['txtRecomendacao'])
        nome_avaliador = unicode(request.form['txtNome'])
        token = str(request.form['token'])
        c1 = str(request.form['c1'])
        c2 = str(request.form['c2'])
        c3 = str(request.form['c3'])
        c4 = str(request.form['c4'])
        c5 = str(request.form['c5'])
        c6 = str(request.form['c6'])
        c7 = str(request.form['c7'])
        comite = str(request.form['comite'])
        try:
            consulta = "UPDATE avaliacoes SET recomendacao=" + recomendacao + " WHERE token=\"" + token + "\""
            atualizar(consulta)
            consulta = "UPDATE avaliacoes SET finalizado=1" + " WHERE token=\"" + token + "\""
            atualizar(consulta)
            consulta = "UPDATE avaliacoes SET data_avaliacao=CURRENT_TIMESTAMP()" + " WHERE token=\"" + token + "\""
            atualizar(consulta)
            consulta = "UPDATE avaliacoes SET nome_avaliador=\"" + nome_avaliador + "\"" + " WHERE token=\"" + token + "\""
            atualizar(consulta)
            comentarios = comentarios.replace('"',' ')
            comentarios = comentarios.replace("'"," ")
            consulta = "UPDATE avaliacoes SET comentario=\"" + comentarios + "\"" + " WHERE token=\"" + token + "\""
            atualizar(consulta)
            consulta = "UPDATE avaliacoes SET c1=" + c1 + " WHERE token=\"" + token + "\""
            atualizar(consulta)
            consulta = "UPDATE avaliacoes SET c2=" + c2 + " WHERE token=\"" + token + "\""
            atualizar(consulta)
            consulta = "UPDATE avaliacoes SET c3=" + c3 + " WHERE token=\"" + token + "\""
            atualizar(consulta)
            consulta = "UPDATE avaliacoes SET c4=" + c4 + " WHERE token=\"" + token + "\""
            atualizar(consulta)
            consulta = "UPDATE avaliacoes SET c5=" + c5 + " WHERE token=\"" + token + "\""
            atualizar(consulta)
            consulta = "UPDATE avaliacoes SET c6=" + c6 + " WHERE token=\"" + token + "\""
            atualizar(consulta)
            consulta = "UPDATE avaliacoes SET c7=" + c7 + " WHERE token=\"" + token + "\""
            atualizar(consulta)
            consulta = "UPDATE avaliacoes SET cepa=" + comite + " WHERE token=\"" + token + "\""
            atualizar(consulta)
        except:
            e = sys.exc_info()[0]
            logging.error(e)
            logging.error("[AVALIACAO] ERRO ao gravar a avaliação: " + token)
            return("Não foi possível gravar a avaliação. Favor entrar contactar pesquisa.prpi@ufca.edu.br.")
        data_agora = getData()
        consulta = "SELECT editais.id,editais.nome FROM editais,avaliacoes,editalProjeto WHERE avaliacoes.idProjeto=editalProjeto.id AND editalProjeto.tipo=editais.id AND avaliacoes.token=\"" + token + "\""
        linhas = consultar(consulta)
        for linha in linhas:
            descricaoEdital = unicode(linha[1])
        return(render_template('declaracao_avaliador.html',nome=nome_avaliador,data=data_agora,edital=descricaoEdital))
    else:
        return("OK")

## TODO: Revisar função abaixo
def descricaoEdital(codigoEdital):
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    consulta = "SELECT id,nome FROM editais WHERE id=" + codigoEdital
    cursor.execute(consulta)
    linhas = cursor.fetchall()
    nomeEdital = "EDITAL NAO DEFINIDO"
    for linha in linhas:
        nomeEdital = unicode(linha[1])
    conn.close()
    return (nomeEdital)

#Gerar declaração do avaliador
@app.route("/declaracaoAvaliador", methods=['GET', 'POST'])
def getDeclaracaoAvaliador():
    if request.method == "GET":
        tokenAvaliacao = str(request.args.get('token'))
        consulta = "SELECT nome_avaliador FROM avaliacoes WHERE token=\"" + tokenAvaliacao + "\""
        linhas = consultar(consulta)
        nome_avaliador = "NAO INFORMADO"
        for linha in linhas:
            nome_avaliador = unicode(linha[0])
        data_agora = getData()
        #Recuperando descrição do edital
        consulta = "SELECT editais.id,editais.nome FROM editais,avaliacoes,editalProjeto WHERE avaliacoes.idProjeto=editalProjeto.id AND editalProjeto.tipo=editais.id AND avaliacoes.token=\"" + tokenAvaliacao + "\""
        linhas = consultar(consulta)
        for linha in linhas:
            descricaoEdital = unicode(linha[1])
        return(render_template('declaracao_avaliador.html',nome=nome_avaliador,data=data_agora,edital=descricaoEdital))
    else:
        return("OK")

def consultar(consulta):
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    cursor.execute(consulta)
    linhas = cursor.fetchall()
    conn.close()
    return (linhas)

@app.route("/recusarConvite", methods=['GET', 'POST'])
def recusarConvite():
    if request.method == "GET":
        tokenAvaliacao = str(request.args.get('token'))
        consulta = "UPDATE avaliacoes SET aceitou=0 WHERE token=\"" + tokenAvaliacao + "\""
        atualizar(consulta)
        #SELECT editalProjeto.titulo,editalProjeto.nome FROM editalProjeto,avaliacoes WHERE editalProjeto.id=avaliacoes.idProjeto AND avaliacoes.token="DL7tueygfszlgqVc2V6HTgN7fSaDjsIPq7O2LpWT"
        #body = "O avaliador de token " + tokenAvaliacao + " recusou o convite de avaliacao."
        #enviarEmail("pesquisa.prpi@ufca.edu.br","[PIICT - RECUSA] Recusa de convite para avaliacao",body)
        return("Avaliação cancelada com sucesso. Agradecemos a atenção.")
    else:
        return("OK")

@app.route("/avaliacoesNegadas", methods=['GET', 'POST'])
def avaliacoesNegadas():
    if request.method == "GET":
        conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
        conn.select_db('pesquisa')
        cursor  = conn.cursor()
        if 'edital' in request.args:
            codigoEdital = str(request.args.get('edital'))
            if 'id' in request.args:
                idProjeto = str(request.args.get('id'))
                consulta = "SELECT resumoGeralAvaliacoes.id,CONCAT(SUBSTRING(resumoGeralAvaliacoes.titulo,1,80),\" - (\",resumoGeralAvaliacoes.nome,\" )\"),(resumoGeralAvaliacoes.aceites+resumoGeralAvaliacoes.rejeicoes) as resultado,resumoGeralAvaliacoes.indefinido FROM resumoGeralAvaliacoes WHERE ((aceites+rejeicoes<2) OR (aceites=rejeicoes)) AND tipo=" + codigoEdital + " AND id = " + idProjeto +" ORDER BY aceites+rejeicoes, id"
            else:
                consulta = "SELECT resumoGeralAvaliacoes.id,CONCAT(SUBSTRING(resumoGeralAvaliacoes.titulo,1,80),\" - (\",resumoGeralAvaliacoes.nome,\" )\"),(resumoGeralAvaliacoes.aceites+resumoGeralAvaliacoes.rejeicoes) as resultado,resumoGeralAvaliacoes.indefinido FROM resumoGeralAvaliacoes WHERE ((aceites+rejeicoes<2) OR (aceites=rejeicoes)) AND tipo=" + codigoEdital + " ORDER BY aceites+rejeicoes, id"
            try:
                cursor.execute(consulta)
                linha = cursor.fetchall()
                total = cursor.rowcount
                conn.close()
                return(render_template('inserirAvaliador.html',listaProjetos=linha,totalDeLinhas=total,codigoEdital=codigoEdital))
            except:
                e = sys.exc_info()[0]
                logging.error(e)
                logging.error(consulta)
                conn.close()
                return(consulta)
        else:
            return ("OK")
    else:
        return("OK")

@app.route("/inserirAvaliador", methods=['GET', 'POST'])
def inserirAvaliador():
    if request.method == "POST":
        token = id_generator(40)
        idProjeto = int(request.form['txtProjeto'])
        avaliador1_email = str(request.form['txtEmail'])
        consulta = "INSERT INTO avaliacoes (aceitou,avaliador,token,idProjeto) VALUES (-1,\"" + avaliador1_email + "\", \"" + token + "\", " + str(idProjeto) + ")"
        atualizar(consulta)
        return("Avaliador cadastrado com sucesso.")
    else:
        return("OK")

#Retorna a quantidade de linhas da consulta
def quantidades(consulta):
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    cursor.execute(consulta)
    total = cursor.rowcount
    conn.close()
    return (total)

## TODO: Finalizar as estatisticas - Projetos aprovados devem ser vir da tabela editalProjeto
@app.route("/estatisticas", methods=['GET', 'POST'])
@auth.login_required
def estatisticas():
    if request.method == "GET":
        codigoEdital = str(request.args.get('edital'))
        #Resumo Geral
        consulta = "SELECT * FROM resumoGeralAvaliacoes WHERE tipo=" + codigoEdital + " ORDER BY ua, score DESC"
        conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
        conn.select_db('pesquisa')
        cursor  = conn.cursor()
        cursor.execute(consulta)
        resumoGeral = cursor.fetchall()
        consulta = "SELECT * FROM resumoGeralAvaliacoes WHERE aceites>=2 AND aceites>rejeicoes AND tipo=" + codigoEdital + " ORDER BY ua, score DESC"
        cursor.execute(consulta)
        aprovados = cursor.fetchall()
        consulta = "SELECT * FROM resumoGeralAvaliacoes WHERE ((aceites+rejeicoes<2) OR (aceites=rejeicoes)) AND tipo=" + codigoEdital + " ORDER BY ua, score DESC"
        #consulta = "SELECT e.id,e.titulo,e.resumo,a.avaliador,a.link,a.id,a.enviado,a.token,e.categoria,e.tipo FROM editalProjeto as e, avaliacoes as a WHERE e.id=a.idProjeto AND e.valendo=1 AND a.finalizado=0 AND a.aceitou!=0 AND e.categoria=1 AND e.tipo=1 AND a.idProjeto IN (SELECT id FROM resumoGeralAvaliacoes WHERE ((aceites+rejeicoes<2) OR (aceites=rejeicoes)) AND tipo=" + codigoEdital + ")"
        cursor.execute(consulta)
        pendentes = cursor.fetchall()
        consulta = "SELECT * FROM resumoGeralAvaliacoes WHERE rejeicoes>=2 AND rejeicoes>aceites AND tipo=" + codigoEdital + " ORDER BY ua, score DESC"
        cursor.execute(consulta)
        reprovados = cursor.fetchall()
        consulta = "SELECT nome FROM editais WHERE id=" + codigoEdital
        cursor.execute(consulta)
        nomeEdital = cursor.fetchall()
        edital = ""
        if cursor.rowcount==1:
            for linha in nomeEdital:
                edital = linha[0]
        else:
            edital=u"CÓDIGO DE EDITAL INVÁLIDO"
        conn.close()
        return(render_template('estatisticas.html',nomeEdital=edital,linhasResumo=resumoGeral,projetosAprovados=aprovados,projetosPendentes=pendentes,projetosReprovados=reprovados))
        #return(codigoEdital)
    else:
        return("OK")


def cotaEstourada(codigoEdital,siape):
    if (codigoEdital=='1'): #Situação particular do edital 01: Checar os que tem 2 bolsas no edital 02/2018/CNPQ/UFCA
        consulta = "SELECT ua,nome,siape FROM resumoGeralClassificacao WHERE tipo=" + codigoEdital + " AND bolsas>0 AND siape=" + siape + " AND siape IN (SELECT siape FROM edital02_2018 WHERE situacao=\"ATIVO\" and modalidade=\"PIBIC\" GROUP BY siape HAVING count(id)=2 ORDER BY orientador) ORDER BY nome"
        total = quantidades(consulta)
        if (total>0):
            return (True)
        else:
            return (False)
    else:
        return (False)

'''
demanda: Quantidade de bolsas por unidade academica
dados: projetos ordenados por Unidade Academica e Lattes
'''
def distribuir_bolsas(demanda,dados):
    ## TODO: Incluir condição de cruzamento de dados
    '''
    Lista de quem tem 2 bolsas PIBIC, e não pode ganhar mais nenhuma bolsa!
    SELECT tipo,id,titulo,ua,nome FROM resumoGeralClassificacao WHERE resumoGeralClassificacao.tipo=1 AND resumoGeralClassificacao.siape IN (SELECT siape FROM edital02_2018 WHERE situacao="ATIVO" and modalidade="PIBIC" GROUP BY siape HAVING count(id)=2 ORDER BY ua,orientador)

    BOLSAS PIBIC POR ORIENTADOR
    SELECT siape,orientador,count(id),situacao FROM edital02_2018 WHERE situacao="ATIVO" and modalidade="PIBIC" GROUP BY siape HAVING count(id)=2 ORDER BY orientador;

    QUEM TEM BOLSA CONCEDIDA, MAS NÃO PODE TER!
    SELECT id,ua,nome,siape FROM resumoGeralClassificacao WHERE tipo=1 AND bolsas_concedidas>=1 AND siape IN (SELECT siape FROM resumoGeralClassificacao WHERE resumoGeralClassificacao.tipo=1 AND resumoGeralClassificacao.siape IN (SELECT siape FROM edital02_2018 WHERE situacao="ATIVO" and modalidade="PIBIC" GROUP BY siape HAVING count(id)=2 ORDER BY ua,orientador)) ORDER BY ua,nome

    '''
    #Iniciando a distribuição
    continua = True
    while (continua):
        for linha in dados:
            ua = str(linha[3]) #Unidade Academica
            idProjeto = linha[1] #ID do projeto
            solicitadas = int(linha[10]) #Quantidade de bolsas solicitadas
            concedidas = int(linha[11]) #Quantidade de bolsas concedidas
            siape = str((linha[12]))  #Siape
            codigoEdital = str(linha[0]) #Codigo do Edital
            if (demanda[ua]>0): #Se a unidade ainda possui bolsas disponíveis
                if (solicitadas-concedidas)>0: #Se ainda existe demanda a ser atendida
                    if(not cotaEstourada(codigoEdital,siape)): #Se o orientador não estiver com a cota individual estourada
                        consulta = "UPDATE editalProjeto SET bolsas_concedidas=bolsas_concedidas+1 WHERE id=" + str(idProjeto)
                        atualizar(consulta)
                        demanda[ua] = demanda[ua] - 1
                        consulta = "UPDATE editalProjeto SET obs=\"BOLSA CONCEDIDA\" WHERE id=" + str(idProjeto)
                        atualizar(consulta)
                    else: #Se o orientador estiver com a cota estourada
                        consulta = "UPDATE editalProjeto SET obs=\"BOLSA NÃO CONCEDIDA. ORIENTADOR NÃO PODE ULTRASSAR A COTA DE 2 BOLSISTAS POR MODALIDADE (Anexo XIV da Res. 01/2014/CONSUP, Art. 7 Inciso I)\" WHERE id=" + str(idProjeto)
                        atualizar(consulta)
            else: # se a unidade não tem mais bolsas disponíveis em sua cota
                consulta = "UPDATE editalProjeto SET obs=\"BOLSA NÃO CONCEDIDA. COTA DA UNIDADE ZERADA (Anexo XIV da Res. 01/2014/CONSUP, Art. 7 Inciso II)\" WHERE id=" + str(idProjeto)
                atualizar(consulta)
        ## TODO: Ver abaixo
        #Verificar se ainda tem bolsas disponíveis para redistribuir dentro das unidades
        continua = False

def executarSelect(consulta):
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    try:
        cursor.execute(consulta)
        total = cursor.rowcount
        resultado = cursor.fetchall()
        conn.close()
        return (resultado,total)
    except:
        e = sys.exc_info()[0]
        logging.error(e)
        logging.error("ERRO Na função executarSelect. Ver consulta abaixo.")
        logging.error(consulta)
    finally:
        cursor.close()
        conn.close()


def avaliacoesEncerradas(codigoEdital):
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    consulta = "SELECT deadline_avaliacao,CURRENT_TIMESTAMP() FROM editais WHERE CURRENT_TIMESTAMP()<deadline_avaliacao AND id=" + codigoEdital
    cursor.execute(consulta)
    total = cursor.rowcount
    conn.close()
    if (total>0): #Edital com avaliacoes encerradas
        return(False)
    else: #Edital com avaliacoes em andamento
        return(True)


@app.route("/resultados", methods=['GET', 'POST'])
@auth.login_required
def resultados():
    if request.method == "GET":

        #Recuperando o código do edital
        codigoEdital = str(request.args.get('edital'))

        #Recuperando o Resumo Geral
        consulta = "SELECT * FROM resumoGeralClassificacao WHERE tipo=" + codigoEdital + " ORDER BY ua, score DESC"
        conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
        conn.select_db('pesquisa')
        cursor  = conn.cursor()
        cursor.execute(consulta)
        total = cursor.rowcount
        resumoGeral = cursor.fetchall()

        #Recuperando dados do edital
        consulta = "SELECT nome,deadline_avaliacao,quantidade_bolsas,mensagem,recursos,link FROM editais WHERE id=" + codigoEdital
        cursor.execute(consulta)
        nomeEdital = cursor.fetchall()
        edital = ""
        data_final_avaliacoes = ""
        qtde_bolsas = 0
        mensagem = ""
        recursos = ""
        link = ""
        if cursor.rowcount==1:
            for linha in nomeEdital:
                edital = str(linha[0])
                data_final_avaliacoes = str(linha[1])
                logging.debug(data_final_avaliacoes)
                qtde_bolsas = int(linha[2])
                mensagem = unicode(linha[3])
                recursos = str(linha[4])
                link = str(linha[5])
        else:
            edital=u"CÓDIGO DE EDITAL INVÁLIDO"
        qtde_bolsas = str(qtde_bolsas)

        #Recuperando total de projetos: total_projetos e calculando total de bolsas por unidade
        total_projetos = str(quantidades("SELECT id FROM resumoGeralClassificacao WHERE tipo=" + codigoEdital))
        bolsas_disponiveis = "round((count(id)/" + total_projetos + ")*" + qtde_bolsas + ") "

        #Recuperando a demanda e oferta de Bolsas
        consulta = "SELECT ua,count(id)," + bolsas_disponiveis +  "as total_bolsas FROM editalProjeto WHERE valendo=1 AND tipo=" + codigoEdital +  " GROUP BY ua"
        cursor.execute(consulta)
        demanda = cursor.fetchall()

        #ZERANDO as concessões
        consulta = "UPDATE editalProjeto SET bolsas_concedidas=0 WHERE tipo=" + codigoEdital
        atualizar(consulta)

        #Recalculando resumoGeral
        consulta = "SELECT * FROM resumoGeralClassificacao WHERE tipo=" + codigoEdital + " ORDER BY ua, score DESC"
        resumoGeral,total = executarSelect(consulta)

        #Distribuição de cota de bolsas
        unidades = {}
        for linha in demanda:
            unidades[str(linha[0])] = int(linha[2])
        distribuir_bolsas(unidades,resumoGeral)

        ## TODO: Redistribuir bolsas remanescentes baseado na classificação geral pelo lattes

        #Recalculando resumoGeral após distribuição
        consulta = "SELECT * FROM resumoGeralClassificacao WHERE tipo=" + codigoEdital + " ORDER BY ua, score DESC"
        resumoGeral,total = executarSelect(consulta)

        #Total de bolsas distribuídas por unidade academica
        consulta = "SELECT ua,sum(bolsas) as solicitadas, sum(bolsas_concedidas) as concedidas,(sum(bolsas_concedidas)/sum(bolsas))*100 as percentual FROM resumoGeralClassificacao WHERE tipo=" + codigoEdital + " GROUP BY ua ORDER BY ua"
        cursor.execute(consulta)
        somatorios = cursor.fetchall()

        #Verificando se as avaliacoes estão encerradas
        if avaliacoesEncerradas(codigoEdital):
            titulo = "Resultado Preliminar"
        else:
            titulo = "Resultado Parcial"

        #Calculando estatísticas de avaliações
        estatisticas = []
        consultaPorUnidade = "SELECT editalProjeto.ua,avg((TIMESTAMPDIFF(DAY,data_envio,data_avaliacao))) as media, min((TIMESTAMPDIFF(DAY,data_envio,data_avaliacao))) as minimo, max((TIMESTAMPDIFF(DAY,data_envio,data_avaliacao))) as maximo  FROM avaliacoes,editalProjeto WHERE editalProjeto.id=avaliacoes.idProjeto AND finalizado=1 AND editalProjeto.tipo=" + codigoEdital +  " GROUP BY editalProjeto.ua ORDER BY editalProjeto.ua"
        consultaPorTotal = "SELECT avg((TIMESTAMPDIFF(DAY,data_envio,data_avaliacao))) as media, min((TIMESTAMPDIFF(DAY,data_envio,data_avaliacao))) as minimo, max((TIMESTAMPDIFF(DAY,data_envio,data_avaliacao))) as maximo  FROM avaliacoes,editalProjeto WHERE editalProjeto.id=avaliacoes.idProjeto AND finalizado=1 AND editalProjeto.tipo=" + codigoEdital
        porUnidade,qtde = executarSelect(consultaPorUnidade)
        porTotal,qtde = executarSelect(consultaPorTotal)

        consultaAvaliacoesTotais = """SELECT
        (SELECT count(avaliacoes.id) FROM avaliacoes,editalProjeto WHERE finalizado=1 and editalProjeto.id=avaliacoes.idProjeto and editalProjeto.tipo=1) as finalizados,
        (SELECT count(avaliacoes.id) FROM avaliacoes,editalProjeto WHERE finalizado=0 and aceitou=1 and editalProjeto.id=avaliacoes.idProjeto and editalProjeto.tipo=1) as indefinidos,
        (SELECT count(avaliacoes.id) FROM avaliacoes,editalProjeto WHERE finalizado=0 and aceitou=0 and editalProjeto.id=avaliacoes.idProjeto and editalProjeto.tipo=1) as negadas,
        (SELECT count(avaliacoes.id) FROM avaliacoes,editalProjeto WHERE editalProjeto.id=avaliacoes.idProjeto and editalProjeto.tipo=1) as total
        FROM avaliacoes,editalProjeto WHERE editalProjeto.id=avaliacoes.idProjeto and editalProjeto.tipo=1 LIMIT 1"""
        consultaAvaliacoesTotais.replace(".tipo=1",".tipo=" + codigoEdital)
        avaliacoesTotais,qtde = executarSelect(consultaAvaliacoesTotais)
        retorno = (1,2,3,4)
        for avaliacoes in avaliacoesTotais:
            retorno = avaliacoes
        #Projetos novos e em andamento
        projetosNovos = quantidades("SELECT id FROM editalProjeto WHERE valendo=1 and categoria=1 AND tipo=" + codigoEdital)
        projetosEmAndamento = quantidades("SELECT id FROM editalProjeto WHERE valendo=1 and categoria=0 AND tipo=" + codigoEdital)
        #Finalizando...
        conn.close()
        data_agora = getData()
        return(render_template('resultados.html',projetosNovos=projetosNovos,projetosEmAndamento=projetosEmAndamento,avaliacoes=retorno,porUnidade=porUnidade,porTotal=porTotal,link=link,mensagem=mensagem,recursos=recursos,nomeEdital=edital,linhasResumo=resumoGeral,totalGeral=total,demanda=demanda,bolsas=qtde_bolsas,somatorios=somatorios,titulo=titulo,data=data_agora))
    else:
        return("OK")

'''
Retorna uma coluna de uma linha única dado uma chave primária
'''
def obterColunaUnica(tabela,coluna,colunaId,valorId):
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    consulta = "SELECT " + coluna + " FROM " + tabela + " WHERE " + colunaId + "=" + valorId
    resultado = "0"
    try:
        cursor.execute(consulta)
        linhas = cursor.fetchall()
        for linha in linhas:
            resultado = unicode(linha[0])
        return(resultado)
    except:
        e = sys.exc_info()[0]
        logging.error(e)
        logging.error("ERRO Na função obtercolunaUnica. Ver consulta abaixo.")
        logging.error(consulta)
    finally:
        cursor.close()
        conn.close()

def gerarGraficos(demandas,grafico1,grafico2,rotacao=0):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    unidades = []
    fatias = []
    for linha in demandas:
        unidades.append(unicode(linha[0]))
        fatias.append(float(linha[1]))

    fig1,ax1 = plt.subplots()
    ax1.pie(fatias,labels=unidades,autopct='%1.1f%%',shadow=True,startangle=90)
    ax1.axis('equal')
    plt.savefig(PLOTS_DIR + grafico1)

    plt.clf()
    y_pos = np.arange(len(unidades))
    bars = plt.bar(y_pos, fatias)
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x(), yval + .005, int(yval),fontweight='bold')
    plt.xticks(y_pos, unidades,rotation=rotacao)
    plt.savefig(PLOTS_DIR + grafico2, bbox_inches = "tight")
    plt.close('all')

@app.route("/editalProjeto", methods=['GET', 'POST'])
@auth.login_required
def editalProjeto():
    #SELECT editalProjeto.id,editalProjeto.nome,GROUP_CONCAT(avaliacoes.avaliador,"(",avaliacoes.finalizado,")") as avaliadores FROM editalProjeto,avaliacoes WHERE tipo=3 and categoria=1 and valendo=1 and editalProjeto.id=avaliacoes.idProjeto GROUP BY editalProjeto.id
    #SELECT editalProjeto.id,editalProjeto.nome,GROUP_CONCAT(avaliacoes.avaliador ORDER BY avaliador SEPARATOR '\n') as avaliadores,GROUP_CONCAT(avaliacoes.recomendacao ORDER BY avaliador SEPARATOR '\n') as recomendacoes FROM editalProjeto,avaliacoes WHERE tipo=3 and categoria=1 and valendo=1 and editalProjeto.id=avaliacoes.idProjeto GROUP BY editalProjeto.id ORDER BY editalProjeto.id
    '''
    SELECT editalProjeto.id,editalProjeto.nome, sum(avaliacoes.recomendacao),
    GROUP_CONCAT(avaliacoes.avaliador ORDER BY avaliador SEPARATOR '\n') as avaliadores,
    GROUP_CONCAT(avaliacoes.recomendacao ORDER BY avaliador SEPARATOR '\n') as recomendacoes,
    GROUP_CONCAT(avaliacoes.enviado ORDER BY avaliador SEPARATOR '\n') as enviado
    FROM editalProjeto,avaliacoes
    WHERE tipo=3 and categoria=1 and valendo=1 and editalProjeto.id=avaliacoes.idProjeto
    GROUP BY editalProjeto.id
    ORDER BY editalProjeto.id
    '''
    if request.method == "GET":
        #Recuperando o código do edital
        if 'edital' in request.args:
            codigoEdital = str(request.args.get('edital'))
            conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
            conn.select_db('pesquisa')
            cursor  = conn.cursor()
            tipo_classificacao = int(obterColunaUnica("editais","classificacao","id",codigoEdital))
            #ORDENA DE ACORDO COM O TIPO DE CLASSIFICAÇÃO: 1 - POR UA; 2 - POR LATTES
            if (tipo_classificacao==1):
                consulta = "SELECT id,tipo,categoria,nome,email,ua,scorelattes,titulo,arquivo_projeto,arquivo_plano1,arquivo_plano2,arquivo_lattes_pdf,arquivo_comprovantes,DATE_FORMAT(data,\"%d/%m/%Y - %H:%i\") as data,DATE_FORMAT(inicio,\"%d/%m/%Y\") as inicio,DATE_FORMAT(fim,\"%d/%m/%Y\") as fim,if(produtividade=0,\"PROD. CNPq\",if(produtividade=1,\"BPI FUNCAP\",\"NORMAL\")) as prioridade FROM editalProjeto WHERE tipo=" + codigoEdital + " AND valendo=1 ORDER BY ua,produtividade,scorelattes DESC"
            else:
                consulta = "SELECT id,tipo,categoria,nome,email,ua,scorelattes,titulo,arquivo_projeto,arquivo_plano1,arquivo_plano2,arquivo_lattes_pdf,arquivo_comprovantes,DATE_FORMAT(data,\"%d/%m/%Y - %H:%i\") as data,DATE_FORMAT(inicio,\"%d/%m/%Y\") as inicio,DATE_FORMAT(fim,\"%d/%m/%Y\") as fim,if(produtividade=0,\"PROD. CNPq\",if(produtividade=1,\"BPI FUNCAP\",\"NORMAL\")) as prioridade FROM editalProjeto WHERE tipo=" + codigoEdital + " AND valendo=1 ORDER BY produtividade,scorelattes DESC"
            consulta_novos = """SELECT editalProjeto.id,nome,ua,titulo,arquivo_projeto,
            GROUP_CONCAT(avaliacoes.avaliador ORDER BY avaliador SEPARATOR '<BR>') as avaliadores,GROUP_CONCAT(avaliacoes.recomendacao ORDER BY avaliador SEPARATOR '<BR>') as recomendacoes,GROUP_CONCAT(avaliacoes.enviado ORDER BY avaliador SEPARATOR '<BR>') as enviado,GROUP_CONCAT(avaliacoes.aceitou ORDER BY avaliador SEPARATOR '<BR>') as aceitou,
            sum(avaliacoes.finalizado) as finalizados,sum(if(recomendacao=-1,1,0)), sum(if(recomendacao=0,1,0)),sum(if(recomendacao=1,1,0)),palavras"""
            consulta_novos = consulta_novos + """ FROM editalProjeto,avaliacoes WHERE tipo=""" + codigoEdital + """ AND valendo=1 AND categoria=1
            AND editalProjeto.id=avaliacoes.idProjeto GROUP BY editalProjeto.id ORDER BY finalizados,editalProjeto.ua,editalProjeto.id"""
            demanda = """SELECT ua,count(id) FROM editalProjeto WHERE valendo=1 and tipo=""" + codigoEdital + """ GROUP BY ua ORDER BY ua"""
            demanda_bolsas = """SELECT ua,sum(bolsas) FROM editalProjeto WHERE valendo=1 and tipo=""" + codigoEdital + """ GROUP BY ua ORDER BY ua"""
            bolsas_ufca = int(obterColunaUnica("editais","quantidade_bolsas","id",codigoEdital))
            bolsas_cnpq = int(obterColunaUnica("editais","quantidade_bolsas_cnpq","id",codigoEdital))
            situacaoProjetosNovos = """SELECT if(situacao=1,"APROVADO",if(situacao=-1,"INDEFINIDO","NÃO APROVADO")) as situacaoD,count(id) FROM resumoProjetosNovos WHERE
            tipo=""" + codigoEdital + """ GROUP BY situacao ORDER BY situacao"""
            respostaAvaliadores = """ SELECT if(aceitou=1,"ACEITOU AVALIAR",if(aceitou=-1,"NÃO RESPONDEU","NÃO ACEITOU AVALIAR")) as resposta,count(avaliacoes.id) FROM avaliacoes,editalProjeto WHERE editalProjeto.id=avaliacoes.idProjeto AND
            tipo=""" + codigoEdital + """ AND valendo=1 AND categoria=1 GROUP BY aceitou"""
            dadosAvaliacoes = """SELECT if(finalizado=1,"FINALIZADO","EM AVALIAÇÃO/NÃO SINALIZOU") as finalizados,count(avaliacoes.id) FROM avaliacoes,editalProjeto WHERE editalProjeto.id=avaliacoes.idProjeto AND
            tipo=""" + codigoEdital + """ AND valendo=1 and categoria=1 AND aceitou!=0 GROUP BY finalizado"""
            dadosScoreLattes = """SELECT ua, ROUND(AVG(scorelattes)) as media FROM editalProjeto WHERE valendo=1 AND
            tipo=""" + codigoEdital + """ GROUP BY ua ORDER BY media"""
            dadosScoreLattesArea = """SELECT SUBSTRING(area_capes,1,30) as area, ROUND(AVG(scorelattes)) as media FROM editalProjeto WHERE valendo=1 AND
            tipo=""" + codigoEdital + """ GROUP BY area_capes ORDER BY area"""
            tempoAvaliacao = """SELECT TIMESTAMPDIFF(DAY,data_envio,data_avaliacao) as tempo,count(avaliacoes.id) total FROM avaliacoes,editalProjeto WHERE editalProjeto.id=avaliacoes.idProjeto AND valendo=1 and
            tipo=""" + codigoEdital + """ and finalizado=1 GROUP BY TIMESTAMPDIFF(DAY,data_envio,data_avaliacao)"""
            oferta_demanda = """(select "OFERTA", sum(quantidade_bolsas)+sum(quantidade_bolsas_cnpq) AS C2 FROM editais WHERE
            id=""" + codigoEdital + """) UNION (SELECT "DEMANDA", sum(bolsas) FROM editalProjeto WHERE valendo=1 and tipo=""" + codigoEdital + """)"""
            try:
                cursor.execute(consulta)
                total = cursor.rowcount
                linhas = cursor.fetchall()
                descricao = descricaoEdital(codigoEdital)
                cursor.execute(consulta_novos)
                total_novos = cursor.rowcount
                linhas_novos = cursor.fetchall()
                cursor.execute(demanda)
                linhas_demanda = cursor.fetchall()
                cursor.execute(demanda_bolsas)
                linhas_demanda_bolsas = cursor.fetchall()
                cursor.execute(situacaoProjetosNovos)
                dadosProjetosNovos = cursor.fetchall()
                cursor.execute(respostaAvaliadores)
                linhasRespostasAvaliadores = cursor.fetchall()
                cursor.execute(dadosAvaliacoes)
                linhasAvaliacoes = cursor.fetchall()
                cursor.execute(dadosScoreLattes)
                linhasScoreLattes = cursor.fetchall()
                cursor.execute(dadosScoreLattesArea)
                linhasScoreLattesArea = cursor.fetchall()
                cursor.execute(tempoAvaliacao)
                linhasTempoAvaliacao = cursor.fetchall()
                cursor.execute(oferta_demanda)
                linhas_oferta_demanda = cursor.fetchall()
                gerarGraficos(linhas_demanda,"grafico-demanda.png","grafico-demanda-2.png")
                gerarGraficos(linhas_oferta_demanda,"grafico-oferta-demanda.png","grafico-oferta-demanda-2.png")
                gerarGraficos(linhas_demanda_bolsas,"grafico-demanda-bolsas-1.png","grafico-demanda-bolsas-2.png")
                gerarGraficos(dadosProjetosNovos,"grafico-novos1.png","grafico-novos2.png")
                gerarGraficos(linhasRespostasAvaliadores,"grafico-avaliadores1.png","grafico-avaliadores2.png")
                gerarGraficos(linhasAvaliacoes,"grafico-avaliacoes1.png","grafico-avaliacoes2.png")
                gerarGraficos(linhasScoreLattes,"grafico-score1.png","grafico-score2.png")
                gerarGraficos(linhasScoreLattesArea,"grafico-scoreArea1.png","grafico-scoreArea2.png",90)
                gerarGraficos(linhasTempoAvaliacao,"grafico-tempoAvaliacao1.png","grafico-tempoAvaliacao2.png")
                return(render_template('editalProjeto.html',listaProjetos=linhas,descricao=descricao,total=total,novos=linhas_novos,total_novos=total_novos,linhas_demanda=linhas_demanda,bolsas_ufca=bolsas_ufca,bolsas_cnpq=bolsas_cnpq,codigoEdital=codigoEdital))
            except:
                e = sys.exc_info()[0]
                logging.error(e)
                logging.error("ERRO Na função /editalProjeto. Ver consulta abaixo.")
                logging.error(consulta)
                return("ERRO!")
            finally:
                cursor.close()
                conn.close()

        else:
            return ("OK")

@app.route("/lattesDetalhado", methods=['GET', 'POST'])
def lattesDetalhado():
    if request.method == "GET":
        #Recuperando o código do edital
        if 'id' in request.args:
            idProjeto = str(request.args.get('id'))
            conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
            conn.select_db('pesquisa')
            cursor  = conn.cursor()
            consulta = "SELECT id,scorelattes_detalhado FROM editalProjeto WHERE id=" + idProjeto + " AND valendo=1"
            cursor.execute(consulta)
            linhas = cursor.fetchall()
            texto = "INDISPONIVEL"
            for linha in linhas:
                lattes_detalhado = unicode(linha[1])
                if lattes_detalhado!="":
                    texto = lattes_detalhado
            conn.close()
            return(texto)
        else:
            return ("OK")


@app.route("/declaracoesPorServidor", methods=['GET', 'POST'])
def declaracoesServidor():
    if request.method == "POST":
        if 'txtSiape' in request.form:
            siape = str(request.form['txtSiape'])
            consulta = ""
            try:
                consulta = "SELECT id,nome,evento,modalidade FROM declaracoes WHERE siape=" + siape
                declaracoes,total = executarSelect(consulta)
                return(render_template('declaracoes_servidor.html',listaDeclaracoes=declaracoes))
            except:
                e = sys.exc_info()[0]
                logging.error(e)
                logging.error("ERRO Na função /declaracoesPorServidor. Ver consulta abaixo.")
                logging.error(consulta)
                return("ERRO!")
        else:
            return("OK")
    else:
        return("OK")

@app.route("/declaracaoEvento", methods=['GET', 'POST'])
def declaracaoEvento():
    if request.method == "GET":
        #Recuperando o código da declaração
        if 'id' in request.args:
            idDeclaracao = str(request.args.get('id'))
            consulta = "SELECT nome,siape,participacao,evento,modalidade,periodo,local FROM declaracoes WHERE id=" + idDeclaracao
            linhas,total = executarSelect(consulta)
            if (total>0):
                texto = linhas[0]
                data_agora = getData()
                return(render_template('declaracao_evento.html',texto=texto,data=data_agora,identificador=idDeclaracao))
            else:
                return(u"Nenhuma declaração encontrada.")
        else:
            return ("OK")

if __name__ == "__main__":
    app.run()
