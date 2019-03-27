# -*- coding: utf-8 -*-
#https://stackoverflow.com/questions/89228/calling-an-external-command-in-python
#SELECT sec_to_time(TIMESTAMPDIFF(SECOND,avaliacoes.data_envio,avaliacoes.data_avaliacao)) as tempoAvaliacao FROM avaliacoes;
#SELECT TIMESTAMPDIFF(DAY,avaliacoes.data_envio,avaliacoes.data_avaliacao) as dias FROM avaliacoes;
#SELECT avaliacoes.idProjeto,sum(avaliacoes.finalizado),editalProjeto.titulo FROM avaliacoes,editalProjeto WHERE editalProjeto.tipo=1 and editalProjeto.id=avaliacoes.idProjeto GROUP BY idProjeto;
#SELECT editalProjeto.titulo, (SELECT sum(avaliacoes.finalizado) FROM avaliacoes WHERE avaliacoes.idProjeto=editalProjeto.id) as soma FROM editalProjeto WHERE id=25;
from flask import Flask
from flask import render_template
from flask import request,url_for,send_file,send_from_directory,redirect,flash,Markup
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

UPLOAD_FOLDER = '/home/perazzo/pesquisa/static/files'
ALLOWED_EXTENSIONS = set(['pdf','xml'])
WORKING_DIR='/home/perazzo/pesquisa/'
CURRICULOS_DIR='/home/perazzo/pesquisa/static/files/'
SITE = "https://yoko.pet/pesquisa/static/files/"

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CURRICULOS_FOLDER'] = CURRICULOS_DIR
## TODO: Preparar o log geral
logging.basicConfig(filename=WORKING_DIR + 'app.log', filemode='w', format='%(asctime)s %(name)s - %(levelname)s - %(message)s',level=logging.DEBUG)

#Obtendo senhas
lines = [line.rstrip('\n') for line in open(WORKING_DIR + 'senhas.pass')]
PASSWORD = lines[0]
GMAIL_PASSWORD = lines[1]

def removerAspas(texto):
    resultado = texto.replace('"',' ')
    resultado = resultado.replace("'"," ")
    return(resultado)

def calcularScoreLattes(tipo,area,since,until,arquivo):
    #Tipo = 0: Apenas pontuacao; Tipo = 1: Sumário
    pasta = "/home/perazzo/flask/projetos/pesquisa/modules/"
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

def getEditaisAbertos():
    conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
    conn.select_db('pesquisa')
    cursor  = conn.cursor()
    consulta = "SELECT id,nome,deadline FROM editais WHERE now()<deadline ORDER BY id DESC"
    cursor.execute(consulta)
    linhas = cursor.fetchall()
    conn.close()
    return(linhas)


@app.route("/")
def home():
    editaisAbertos = getEditaisAbertos()
    return (render_template('cadastrarProjeto.html',abertos=editaisAbertos))

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
    consulta = "UPDATE editalProjeto SET titulo=\"" + titulo + "\", validade=" + str(validade) + ", palavras=\"" + palavras_chave + "\", resumo=\"" + descricao_resumida + "\", bolsas=" + str(bolsas) + " WHERE id=" + str(ultimo_id)
    logging.debug("Preparando para atualizar dados do projeto.")
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

#Gerar pagina de avaliacao para o avaliador
@app.route("/avaliacao", methods=['GET', 'POST'])
def getPaginaAvaliacao():
    if request.method == "GET":
        idProjeto = str(request.args.get('id'))
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

#Gravar avaliacao gerada pelo avaliador
@app.route("/avaliar", methods=['GET', 'POST'])
def enviarAvaliacao():
    if request.method == "POST":
        comentarios = unicode(request.form['txtComentarios'])
        recomendacao = str(request.form['txtRecomendacao'])
        nome_avaliador = unicode(request.form['txtNome'])
        token = str(request.form['token'])
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
        except:
            e = sys.exc_info()[0]
            logging.error(e)
            logging.error("[AVALIACAO] ERRO ao gravar a avaliação: " + token)
            return("Não foi possível gravar a avaliação. Favor entrar contactar pesquisa.prpi@ufca.edu.br.")
        data_agora = getData()
        return(render_template('declaracao_avaliador.html',nome=nome_avaliador,data=data_agora))
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
        codigoEdital = str(request.args.get('edital'))
        #consulta = "SELECT editalProjeto.id,CONCAT(SUBSTRING(editalProjeto.titulo,1,80),\" - (\",editalProjeto.nome,\" )\"),sum(avaliacoes.finalizado) as soma FROM editalProjeto,avaliacoes WHERE editalProjeto.id=avaliacoes.idProjeto AND editalProjeto.categoria=1 AND editalProjeto.valendo=1 AND editalProjeto.tipo=" + codigoEdital + " GROUP by avaliacoes.idProjeto order by soma"
        #consulta = "SELECT resumoGeralAvaliacoes.id,CONCAT(SUBSTRING(resumoGeralAvaliacoes.titulo,1,80),\" - (\",resumoGeralAvaliacoes.nome,\" )\"),(resumoGeralAvaliacoes.aceites+resumoGeralAvaliacoes.rejeicoes) as resultado,resumoGeralAvaliacoes.indefinido FROM resumoGeralAvaliacoes WHERE (resumoGeralAvaliacoes.aceites+resumoGeralAvaliacoes.rejeicoes)<2 AND resumoGeralAvaliacoes.tipo=" + codigoEdital + " order by resultado"
        consulta = "SELECT resumoGeralAvaliacoes.id,CONCAT(SUBSTRING(resumoGeralAvaliacoes.titulo,1,80),\" - (\",resumoGeralAvaliacoes.nome,\" )\"),(resumoGeralAvaliacoes.aceites+resumoGeralAvaliacoes.rejeicoes) as resultado,resumoGeralAvaliacoes.indefinido FROM resumoGeralAvaliacoes WHERE ((aceites+rejeicoes<2) OR (aceites=rejeicoes)) AND tipo=" + codigoEdital + " ORDER BY resultado"
        try:
            cursor.execute(consulta)
            linha = cursor.fetchall()
            total = cursor.rowcount
            conn.close()
            return(render_template('inserirAvaliador.html',listaProjetos=linha,totalDeLinhas=total))
        except:
            e = sys.exc_info()[0]
            logging.error(e)
            logging.error(consulta)
            conn.close()
            return(consulta)
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

'''
demanda: Quantidade de bolsas por unidade academica
dados: projetos ordenados por Unidade Academica e Lattes
'''
def distribuir_bolsas(demanda,dados):
    a = 1
    #ZERANDO as concessões
    consulta = "UPDATE editalProjeto SET bolsas_concedidas=0"
    atualizar(consulta)
    #Iniciando a distribuição
    continua = True
    while (continua):
        for linha in dados:
            ua = str(linha[3]) #Unidade Academica
            idProjeto = linha[1] #ID do projeto
            solicitadas = int(linha[10]) #Quantidade de bolsas solicitadas
            concedidas = int(linha[11])
            if (demanda[ua]>0): #Se a unidade ainda possui bolsas disponíveis
                if (solicitadas-concedidas)>0: #Se ainda existe demanda a ser atendida
                    consulta = "UPDATE editalProjeto SET bolsas_concedidas=bolsas_concedidas+1 WHERE id=" + str(idProjeto)
                    logging.debug(consulta)
                    atualizar(consulta)
                    demanda[ua] = demanda[ua] - 1
        #Verificar se ainda tem bolsas disponíveis
        continua = False

@app.route("/resultados", methods=['GET', 'POST'])
def resultados():
    if request.method == "GET":
        codigoEdital = str(request.args.get('edital'))
        #Resumo Geral
        consulta = "SELECT * FROM resumoGeralClassificacao WHERE tipo=" + codigoEdital + " ORDER BY ua, score DESC"
        conn = MySQLdb.connect(host="localhost", user="pesquisa", passwd=PASSWORD, db="pesquisa", charset="utf8", use_unicode=True)
        conn.select_db('pesquisa')
        cursor  = conn.cursor()
        cursor.execute(consulta)
        total = cursor.rowcount
        resumoGeral = cursor.fetchall()
        consulta = "SELECT nome,deadline_avaliacao FROM editais WHERE id=" + codigoEdital
        cursor.execute(consulta)
        nomeEdital = cursor.fetchall()
        edital = ""
        data_final_avaliacoes = ""
        if cursor.rowcount==1:
            for linha in nomeEdital:
                edital = linha[0]
                data_final_avaliacoes = str(linha[1])
        else:
            edital=u"CÓDIGO DE EDITAL INVÁLIDO"

        #Recuperando a quantidade de bolsas do edital: qtde_bolsas
        consulta = "SELECT quantidade_bolsas FROM editais WHERE id=" + codigoEdital
        cursor.execute(consulta)
        info_edital = cursor.fetchall()
        if cursor.rowcount==1:
            for linha in info_edital:
                qtde_bolsas = linha[0]
        else:
            qtde_bolsas=0
        qtde_bolsas = str(qtde_bolsas)
        #Recuperando total de projetos concorrento no editalProjeto: total_projetos
        total_projetos = str(quantidades("SELECT id FROM editalProjeto WHERE valendo=1 and tipo=" + codigoEdital))
        bolsas_disponiveis = "round((count(id)/" + total_projetos + ")*" + qtde_bolsas + ") "
        #Recuperando a demanda e oferta de Bolsas
        consulta = "SELECT ua,count(id)," + bolsas_disponiveis +  "as total_bolsas FROM editalProjeto WHERE valendo=1 AND tipo=" + codigoEdital +  " GROUP BY ua"
        cursor.execute(consulta)
        demanda = cursor.fetchall()
        #Distribuição de cota de bolsas
        unidades = {}
        for linha in demanda:
            unidades[str(linha[0])] = int(linha[2])
        distribuir_bolsas(unidades,resumoGeral)
        #Finalizando...
        conn.close()
        return(render_template('resultados.html',nomeEdital=edital,linhasResumo=resumoGeral,totalGeral=total,demanda=demanda,bolsas=qtde_bolsas))
        #return(codigoEdital)
    else:
        return("OK")


if __name__ == "__main__":
    app.run()
