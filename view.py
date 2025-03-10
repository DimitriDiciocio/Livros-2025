from flask import Flask, jsonify, request, send_file
from main import app, con
from flask_bcrypt import generate_password_hash, check_password_hash
import jwt
from fpdf import FPDF
import os

senha_secreta = app.config['SECRET_KEY']


def generate_token(user_id):
    payload = {'id_usuario': user_id}
    token = jwt.encode(payload, senha_secreta, algorithm='HS256')
    return token


def remover_bearer(token):
    if token.startswith('Bearer '):
        return token[len('Bearer '):]
    else:
        return token


@app.route('/livro', methods=['GET'])
def livro():
    cur = con.cursor()
    cur.execute('SELECT id_livro, titulo, autor, ano_publicado FROM LIVROS')
    livros = cur.fetchall()
    livros_dic = []
    for livro in livros:
        livros_dic.append({
            'id_livro': livro[0],
            'titulo': livro[1],
            'autor': livro[2],
            'ano_publicado': livro[3]
        })
    return jsonify(mensagem="Lista de Livros", livros=livros_dic)


@app.route('/livros/relatorio', methods=['GET'])
def gerar_relatorio():
    cursor = con.cursor()
    cursor.execute("SELECT id_livro, titulo, autor, ano_publicado FROM livros")
    livros = cursor.fetchall()
    cursor.close()
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=16)
    pdf.cell(200, 10, "Relatorio de Livros", ln=True, align='C')
    pdf.ln(5)  # Espaço entre o título e a linha
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())  # Linha abaixo do título
    pdf.ln(5)  # Espaço após a linha
    pdf.set_font("Arial", size=12)
    for livro in livros:
        pdf.cell(200, 10, f"ID: {livro[0]} - {livro[1]} - {livro[2]} - {livro[3]}", ln=True)
    contador_livros = len(livros)
    pdf.ln(10)  # Espaço antes do contador
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(200, 10, f"Total de livros cadastrados: {contador_livros}", ln=True, align='C')
    pdf_path = "relatorio_livros.pdf"
    pdf.output(pdf_path)
    return send_file(pdf_path, as_attachment=True, mimetype='application/pdf')


@app.route('/livro', methods=["POST"])
def livro_post():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({'message': 'token de autenticação necessário'}), 401
    token = remover_bearer(token)
    try:
        payload = jwt.decode(token, senha_secreta, algorithms=['HS256'])
        id_usuario = payload["id_usuario"]
    except jwt.ExpiredSignatureError:
        return jsonify({"message": 'Token expirado'}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Token inválida"}), 401

    data = request.form
    titulo = data.get('titulo')
    autor = data.get('autor')
    ano_publicado = data.get('ano_publicado')
    imagem = request.files.get('imagem')

    cur = con.cursor()

    cur.execute("SELECT 1 from livros where titulo = ?", (titulo,))
    if cur.fetchone():
        return jsonify("Livro já cadastrado")

    cur.execute(
        "INSERT INTO livros (TITULO, AUTOR, ANO_PUBLICADO) VALUES (?, ?, ?) RETURNING ID_livro",
        (titulo, autor, ano_publicado)
    )
    livro_id = cur.fetchone()[0]
    con.commit()
    if imagem:
        nome_imagem = f"{livro_id}.jpeg"
        pasta_destino = os.path.join(app.config['UPLOAD_FOLDER'], "Livros")
        os.makedirs(pasta_destino, exist_ok=True)
        imagem_path = os.path.join(pasta_destino, nome_imagem)
        imagem.save(imagem_path)
    cur.close()
    return jsonify({
        'message': 'Livro cadastrado com sucesso!',
        'livro': {
            'titulo': titulo,
            'autor': autor,
            'ano_publicado': ano_publicado,
            'imagem_path': imagem_path
        }
    })


@app.route('/livro/<int:id>', methods=['put'])
def livro_put(id):
    cur = con.cursor()
    cur.execute("select id_livro, titulo, autor, ano_publicado from livros where id_livro = ?", (id,))
    livro_data = cur.fetchone()
    if not livro_data:
        cur.close()
        return jsonify({"message": "Livro não foi encontrado"})
    data = request.get_json()
    titulo = data.get('titulo')
    autor = data.get('autor')
    ano_publicado = data.get('ano_publicado')

    cur.execute("update livros set titulo = ?, autor = ?, ano_publicado = ? where id_livro = ?",
                (titulo, autor, ano_publicado, id))
    con.commit()
    cur.close()
    return jsonify({
        'message': 'Livro atualizado com sucesso!',
        'livro': {
            'id_livro': id,
            'titulo': titulo,
            'autor': autor,
            'ano_publicado': ano_publicado
        }
    })


@app.route('/livro/<int:id>', methods=['DELETE'])
def deletar_livro(id):
    cursor = con.cursor()

    # Verificar se o livro existe
    cursor.execute("SELECT 1 FROM livros WHERE ID_LIVRO = ?", (id,))
    if not cursor.fetchone():
        cursor.close()
        return jsonify({"error": "Livro não encontrado"}), 404

    # Excluir o livro
    cursor.execute("DELETE FROM livros WHERE ID_LIVRO = ?", (id,))
    con.commit()
    cursor.close()

    return jsonify({
        'message': "Livro excluído com sucesso!",
        'id_livro': id
    })


@app.route('/usuario', methods=['GET'])
def usuario():
    cur = con.cursor()
    cur.execute('SELECT id_usuario, nome, email, senha FROM usuarios')
    usuarios = cur.fetchall()
    usuarios_dic = []
    for usuario in usuarios:
        usuarios_dic.append({
            'id_usuario': usuario[0],
            'nome': usuario[1],
            'email': usuario[2],
            'senha': usuario[3]
        })
    return jsonify(mensagem="Lista de Usuarios", usuarios=usuarios_dic)


@app.route('/usuario', methods=["POST"])
def usuario_post():
    data = request.get_json()
    nome = data.get('nome')
    email = data.get('email')
    senha = data.get('senha')

    if len(senha) < 8:
        return jsonify("Sua senha deve conter pelo menos 8 caracteres")

    tem_maiuscula = False
    tem_minuscula = False
    tem_numero = False
    tem_caract_especial = False
    caracteres_especiais = "!@#$%^&*(),.?\":{}|<>"

    # Verifica cada caractere da senha
    for char in senha:
        if char.isupper():
            tem_maiuscula = True
        elif char.islower():
            tem_minuscula = True
        elif char.isdigit():
            tem_numero = True
        elif char in caracteres_especiais:
            tem_caract_especial = True

    # Verifica se todos os critérios foram atendidos
    if not tem_maiuscula:
        return jsonify("A senha deve conter pelo menos uma letra maiúscula.")
    if not tem_minuscula:
        return jsonify("A senha deve conter pelo menos uma letra minúscula.")
    if not tem_numero:
        return jsonify("A senha deve conter pelo menos um número.")
    if not tem_caract_especial:
        return jsonify("A senha deve conter pelo menos um caractere especial.")

    cur = con.cursor()

    cur.execute("SELECT 1 from usuarios where email = ?", (email,))
    if cur.fetchone():
        return jsonify("Email já cadastrado")

    senha = generate_password_hash(senha).decode('utf-8')

    cur.execute("insert into usuarios(nome,email,senha) values (?,?,?)", (nome, email, senha))
    con.commit()
    cur.close()
    return jsonify({
        'message': 'Usuario cadastrado com sucesso!',
        'usuario': {
            'nome': nome,
            'email': email,
            'senha': senha
        }
    })


@app.route('/usuario/<int:id>', methods=['put'])
def usuario_put(id):
    cur = con.cursor()
    cur.execute("select id_usuario, nome, email, senha from usuarios where id_usuario = ?", (id,))
    usuario_data = cur.fetchone()
    if not usuario_data:
        cur.close()
        return jsonify({"message": "Usuario não foi encontrado"})
    data = request.get_json()
    nome = data.get('nome')
    email = data.get('email')
    senha = data.get('senha')

    email = email.lower()

    if len(senha) < 8:
        return jsonify("Sua senha deve conter pelo menos 8 caracteres")

    tem_maiuscula = False
    tem_minuscula = False
    tem_numero = False
    tem_caract_especial = False
    caracteres_especiais = "!@#$%^&*(),.?\":{}|<>"

    # Verifica cada caractere da senha
    for char in senha:
        if char.isupper():
            tem_maiuscula = True
        elif char.islower():
            tem_minuscula = True
        elif char.isdigit():
            tem_numero = True
        elif char in caracteres_especiais:
            tem_caract_especial = True

    # Verifica se todos os critérios foram atendidos
    if not tem_maiuscula:
        return jsonify("A senha deve conter pelo menos uma letra maiúscula.")
    if not tem_minuscula:
        return jsonify("A senha deve conter pelo menos uma letra minúscula.")
    if not tem_numero:
        return jsonify("A senha deve conter pelo menos um número.")
    if not tem_caract_especial:
        return jsonify("A senha deve conter pelo menos um caractere especial.")

    cur.execute("SELECT email from usuarios where id_usuario = ?", (id,))
    emailvelho = cur.fetchone()
    emailvelho = emailvelho[0].lower()
    if emailvelho != email:
        cur.execute("SELECT 1 from usuarios where email = ?", (email,))
        if cur.fetchone():
            return jsonify("Email já cadastrado")

    senha = generate_password_hash(senha).decode('utf-8')

    cur.execute("update usuarios set nome = ?, email = ?, senha = ? where id_usuario = ?", (nome, email, senha, id))
    con.commit()
    cur.close()
    return jsonify({
        'message': 'Usuario atualizado com sucesso!',
        'usuario': {
            'id_usuario': id,
            'nome': nome,
            'email': email,
            'senha': senha
        }
    })


@app.route('/login', methods=["POST"])
def login():
    data = request.get_json()
    email = data.get('email')
    senha = data.get('senha')
    email = email.lower()

    cur = con.cursor()

    cur.execute("SELECT senha, id_usuario FROM USUARIOS WHERE email = ?", (email,))
    senha_hash = cur.fetchone()
    if not senha_hash:
        return jsonify({"message": "Usuário não encontrado"}), 404
    id_usuario = senha_hash[1]
    senha_hash = senha_hash[0]
    if check_password_hash(senha_hash, senha):
        token = generate_token(id_usuario)
        return jsonify({'message': 'Usuário entrou com sucesso',
                        'token': token
                        }), 200
    else:
        return jsonify("Credenciais invalidas"), 401
