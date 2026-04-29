usuarios = []
_counter = 1

def criar_usuario(data):
    global _counter
    usuario = {
        "id": _counter,
        "nome": data.nome,
        "email": data.email
    }
    usuarios.append(usuario)
    _counter += 1
    return usuario