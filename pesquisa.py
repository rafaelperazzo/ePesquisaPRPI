# -*- coding: utf-8 -*-
from flask import Flask
from flask import render_template
from flask import request,url_for,send_file,send_from_directory,redirect,flash
import datetime
import sqlite3
import MySQLdb
from werkzeug.utils import secure_filename
import os

UPLOAD_FOLDER = '/home/perazzo/flask/projetos/pesquisa/static/files'
ALLOWED_EXTENSIONS = set(['pdf'])
PASSWORD = ""

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
    pass
    #CADASTRAR DADOS DO PROPONENTE
    tipo = unicode(request.form['tipo'])
    nome = unicode(request.form['nome'])
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
    consulta = "INSERT INTO editalProjeto (tipo,nome,siape,email,ua,area_capes,grande_area,grupo,data) VALUES (" + "\"" + tipo + "\"," +  "\"" + nome + "\"," + str(siape) + "," + "\"" + email + "\"," + "\"" + ua + "\"," + "\"" + area_capes + "\"," + "\"" + grande_area + "\"," + "\"" + grupo + "\"," + "CURRENT_TIMESTAMP())"
    cursor.execute(consulta)
    conn.commit()
    getID = "SELECT LAST_INSERT_ID()"
    cursor.execute(getID)
    ultimo_id = int(cursor.fetchone()[0])
    
    
    #TODO: CADASTRAR DADOS DO PROJETO
    '''  
    arquivo_projeto = request.files['arquivo_projeto']
    if arquivo_projeto and allowed_file(arquivo_projeto.filename):
        filename = secure_filename(arquivo_projeto.filename)
        arquivo_projeto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    elif not allowed_file(arquivo_projeto.filename):
		return ("Arquivo não permitido")
    
    #CADASTRAR AVALIADORES SUGERIDOS
    '''
    conn.close()
    return (consulta + "<BR>ID: " + str(ultimo_id) + "<BR>" + str(filename))
    
if __name__ == "__main__":
    app.run()
