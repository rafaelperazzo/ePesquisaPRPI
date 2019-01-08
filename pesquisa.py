# -*- coding: utf-8 -*-
from flask import Flask
from flask import render_template
from flask import request,url_for,send_file,send_from_directory,redirect,flash
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
import logging

UPLOAD_FOLDER = '/home/perazzo/flask/projetos/pesquisa/static/files'
ALLOWED_EXTENSIONS = set(['pdf','xml'])

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
## TODO: Preparar o log geral
logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s',level=logging.DEBUG)

#Obtendo senhas
lines = [line.rstrip('\n') for line in open('senhas.pass')]
PASSWORD = lines[0]
GMAIL_PASSWORD = lines[1]

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
        return (True)
    except:
        return (False)

def atualizar(consulta):
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.autocommit(False)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    try:
        cursor.execute(consulta)
        conn.commit()
    except MySQLdb.Error, e:
        conn.rollback()
    finally:
        conn.close()


def id_generator(size=20, chars=string.ascii_uppercase + string.digits + string.ascii_lowercase):
        return ''.join(random.choice(chars) for _ in range(size))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def getData():
    Meses=('janeiro','fevereiro','mar','abril','maio','junho',
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
    consulta = "SELECT nome,cpf,modalidade,orientador,projeto,inicio,fim,id FROM alunos WHERE id=" + str(identificador)
    cursor.execute(consulta)
    linha = cursor.fetchone()

    #RECUPERANDO DADOS
    nome = linha[0]
    cpf = linha[1]
    modalidade = linha[2]
    orientador = linha[3]
    projeto = linha[4]
    ch = "12 horas"
    vigencia_inicio = linha[5]
    vigencia_fim = linha[6]
    id_projeto = linha[7]

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

@app.route("/")
def home():
    return ("OK")

@app.route("/declaracao", methods=['GET', 'POST'])
def declaracao():
    #texto_declaracao = gerarDeclaracao(str(request.form['txtCPF']))
    texto_declaracao = gerarDeclaracao(str(request.args['idProjeto']))
    data_agora = getData()
    return render_template('a4.html',texto=texto_declaracao,data=data_agora,identificador=texto_declaracao[7])

@app.route("/projetosAluno", methods=['GET', 'POST'])
def projetos():
    projetosAluno = gerarProjetosPorAluno(str(request.form['txtNome']))
    return render_template('alunos.html',listaProjetos=projetosAluno)

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

    #CADASTRAR DADOS DO PROJETO

    titulo = unicode(request.form['titulo'])
    validade = int(request.form['validade'])
    palavras_chave = unicode(request.form['palavras_chave'])
    descricao_resumida = unicode(request.form['descricao_resumida'])
    bolsas = int(request.form['numero_bolsas'])
    consulta = "UPDATE editalProjeto SET titulo=\"" + titulo + "\", validade=" + str(validade) + ", palavras=\"" + palavras_chave + "\", resumo=\"" + descricao_resumida + "\", bolsas=" + str(bolsas) + " WHERE id=" + str(ultimo_id)
    atualizar(consulta)
    codigo = id_generator()
    if ('arquivo_projeto' in request.files):
        arquivo_projeto = request.files['arquivo_projeto']
        if arquivo_projeto and allowed_file(arquivo_projeto.filename) :

            arquivo_projeto.filename = "projeto_" + ultimo_id_str + "_" + str(siape) + "_" + codigo + ".pdf"
            filename = secure_filename(arquivo_projeto.filename)
            arquivo_projeto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            caminho = str(app.config['UPLOAD_FOLDER'] + "/" + filename)
            consulta = "UPDATE editalProjeto SET arquivo_projeto=\"" + filename + "\" WHERE id=" + str(ultimo_id)
            atualizar(consulta)
        elif not allowed_file(arquivo_projeto.filename):
    		return ("Arquivo de projeto não permitido")
    if ('arquivo_plano1' in request.files):

        arquivo_plano1 = request.files['arquivo_plano1']
        if arquivo_plano1 and allowed_file(arquivo_plano1.filename):
            arquivo_plano1.filename = "plano1_" + ultimo_id_str + "_" + str(siape) + "_" + codigo + ".pdf"
            filename = secure_filename(arquivo_plano1.filename)
            arquivo_plano1.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            caminho = str(app.config['UPLOAD_FOLDER'] + "/" + filename)
            consulta = "UPDATE editalProjeto SET arquivo_plano1=\"" + filename + "\" WHERE id=" + str(ultimo_id)
            atualizar(consulta)
        elif not allowed_file(arquivo_plano1.filename):
    		return ("Arquivo de plano 1 de trabalho não permitido")

    if ('arquivo_plano2' in request.files):
        arquivo_plano2 = request.files['arquivo_plano2']
        if arquivo_plano2 and allowed_file(arquivo_plano2.filename):
            arquivo_plano2.filename = "plano2_" + ultimo_id_str + "_" + str(siape) + "_" + codigo + ".pdf"
            filename = secure_filename(arquivo_plano2.filename)
            arquivo_plano2.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            caminho = str(app.config['UPLOAD_FOLDER'] + "/" + filename)
            consulta = "UPDATE editalProjeto SET arquivo_plano2=\"" + filename + "\" WHERE id=" + str(ultimo_id)
            atualizar(consulta)
        elif not allowed_file(arquivo_plano2.filename):
    		return ("Arquivo de plano 2 de trabalho não permitido")

    if ('arquivo_lattes' in request.files):
        arquivo_lattes = request.files['arquivo_lattes']
        if arquivo_lattes and allowed_file(arquivo_lattes.filename):
            arquivo_lattes.filename = str(siape) + "_" + codigo + ".xml"
            filename = secure_filename(arquivo_lattes.filename)
            arquivo_lattes.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            caminho = str(app.config['UPLOAD_FOLDER'] + "/" + filename)
            consulta = "UPDATE editalProjeto SET arquivo_lattes=\"" + filename + "\" WHERE id=" + str(ultimo_id)
            atualizar(consulta)
        elif not allowed_file(arquivo_lattes.filename):
    		return ("Arquivo de curriculo lattes não permitido")

    #CADASTRAR AVALIADORES SUGERIDOS
    avaliador1_email = unicode(request.form['avaliador1_email'])
    if avaliador1_email!='':
        token = id_generator(40)
        consulta = "INSERT INTO avaliacoes (avaliador,token,idProjeto) VALUES (\"" + avaliador1_email + "\", \"" + token + "\", " + str(ultimo_id) + ")"
        atualizar(consulta)

    avaliador2_email = unicode(request.form['avaliador2_email'])
    if avaliador2_email!='':
        token = id_generator(40)
        consulta = "INSERT INTO avaliacoes (avaliador,token,idProjeto) VALUES (\"" + avaliador2_email + "\", \"" + token + "\", " + str(ultimo_id) + ")"
        atualizar(consulta)

    avaliador3_email = unicode(request.form['avaliador3_email'])
    if avaliador3_email!='':
        token = id_generator(40)
        consulta = "INSERT INTO avaliacoes (avaliador,token,idProjeto) VALUES (\"" + avaliador3_email + "\", \"" + token + "\", " + str(ultimo_id) + ")"
        atualizar(consulta)
    #ENVIAR E-MAIL DE CONFIRMAÇÃO
    if enviarEmail(email,u"[CONFIRMACAO] - Cadastro de Projeto de Pesquisa","Seu projeto foi cadastrado com sucesso. IDentificador: " + str(ultimo_id)):
        return ("E-mail de confirmação enviado com sucesso.<BR>ID do seu projeto: " + str(ultimo_id))
    else:
        return("Não foi possível enviar o e-mail de confirmação. Anote o ID de seu projeto: " + str(ultimo_id))

    conn.close()


if __name__ == "__main__":
    app.run()
