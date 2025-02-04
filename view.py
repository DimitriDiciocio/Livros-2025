from flask import Flask, jsonify, request
from main import app, con


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


@app.route('/livro', methods=["POST"])
def livro_post():
    data = request.get_json()
    titulo = data.get('titulo')
    autor = data.get('autor')
    ano_publicado = data.get('ano_publicado')

    cur = con.cursor()

    cur.execute("SELECT 1 from livros where titulo = ?", (titulo,))
    if cur.fetchone():
        return jsonify("Livro já cadastrado")

    cur.execute("insert into livros(titulo,autor,ano_publicado) values (?,?,?)", (titulo, autor, ano_publicado))
    con.commit()
    cur.close()
    return jsonify({
        'message': 'Livro cadastrado com sucesso!',
        'livro': {
            'titulo': titulo,
            'autor': autor,
            'ano_publicado': ano_publicado
        }
    })




@app.route('/livro/<int:id>', methods=['put'])
def livro_put(id):
    cur = con.cursor()
    cur.execute("select id_livro, titulo, autor, ano_publicado from livros where id_livro = ?", (id,))
    livro_data = cur.fetchone()
    if not livro_data:
        cur.close()
        return jsonify({"message":"Livro não foi encontrado"})
    data = request.get_json()
    titulo = data.get('titulo')
    autor = data.get('autor')
    ano_publicado = data.get('ano_publicado')

    cur.execute("update livros set titulo = ?, autor = ?, ano_publicado = ? where id_livro = ?", (titulo, autor, ano_publicado, id))
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