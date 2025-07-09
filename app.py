# app.py - VERSÃO COMPLETA E CORRIGIDA

import os
import re
import pytz
import pdfplumber
import pandas as pd
from io import BytesIO
from flask import Flask, jsonify, request, render_template, send_file, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy import func, cast, Date
import traceback
from werkzeug.security import generate_password_hash, check_password_hash
import unicodedata
from itertools import groupby 


# --- FUNÇÃO HELPER PARA NORMALIZAR TEXTO ---
def normalize_text(text):
    """Remove acentos de uma string para uso como chave interna."""
    # Transforma 'Atenção' -> 'atencao', 'Crítico' -> 'critico'
    if not text:
        return ""
    text = text.lower()
    return "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')



# --- CONFIGURAÇÃO INICIAL ---
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder='templates', static_folder='static')

# --- NOVA CONFIGURAÇÃO DE CHAVE SECRETA ---

app.config['SECRET_KEY'] = '4765063-Funeral-##' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'insumos.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# --- MODELOS (Estrutura do Banco de Dados REVISADA) ---

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(80), nullable=False, default='user') # Ex: 'user', 'admin'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Fornecedor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ativo = db.Column(db.Boolean, default=True)
    razao_social = db.Column(db.String(200), nullable=False)
    nome_fantasia = db.Column(db.String(200))
    cnpj = db.Column(db.String(20), unique=True, nullable=False)
    inscricao_estadual = db.Column(db.String(20))
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    website = db.Column(db.String(120))
    categoria = db.Column(db.String(100))
    cep = db.Column(db.String(10))
    logradouro = db.Column(db.String(200))
    numero = db.Column(db.String(20))
    complemento = db.Column(db.String(100))
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(2))
    contato_principal_nome = db.Column(db.String(100))
    contato_principal_cargo = db.Column(db.String(100))
    contato_principal_telefone = db.Column(db.String(20))
    contato_principal_email = db.Column(db.String(120))
    observacoes = db.Column(db.Text)
    
    nao_conformidades = db.relationship('NaoConformidade', back_populates='fornecedor', cascade="all, delete-orphan")
    recebimentos = db.relationship('Recebimento', back_populates='fornecedor')

class Insumo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    descricao = db.Column(db.String(200), nullable=False, index=True)
    categoria = db.Column(db.String(100), default='Geral')
    unidade_medida = db.Column(db.String(20), nullable=False, default='UN')
    valor_unitario = db.Column(db.Float, default=0.0)
    estoque_minimo = db.Column(db.Integer, default=0)
    
    posicoes_estoque = db.relationship('Estoque', back_populates='insumo', cascade="all, delete-orphan")
    nao_conformidades = db.relationship('NaoConformidade', back_populates='insumo')
    itens_recebidos = db.relationship('ItemRecebido', back_populates='insumo')
    movimentacoes = db.relationship('Movimentacao', back_populates='insumo')

    def to_dict(self):
        return {
            'id': self.id,
            'sku': self.sku,
            'descricao': self.descricao,
            'categoria': self.categoria,
            'unidade_medida': str(self.unidade_medida or ''),
            'valor_unitario': self.valor_unitario,
            'estoque_minimo': self.estoque_minimo
        }

class Estoque(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    insumo_id = db.Column(db.Integer, db.ForeignKey('insumo.id'), nullable=False)
    posicao = db.Column(db.String(100), nullable=False, index=True)
    quantidade = db.Column(db.Float, nullable=False, default=0)
    
    insumo = db.relationship('Insumo', back_populates='posicoes_estoque')

class Movimentacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    insumo_id = db.Column(db.Integer, db.ForeignKey('insumo.id'), nullable=False)
    setor_id = db.Column(db.Integer, db.ForeignKey('setor.id'), nullable=True)
    tipo = db.Column(db.String(20), nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    data_hora = db.Column(db.DateTime, default=datetime.utcnow)
    posicao_origem = db.Column(db.String(100))
    posicao_destino = db.Column(db.String(100))
    turno = db.Column(db.String(20))
    usuario = db.Column(db.String(100)) # <-- ADICIONE ESTA LINHA
    
    insumo = db.relationship('Insumo', back_populates='movimentacoes')
    setor = db.relationship('Setor', back_populates='movimentacoes')

class Setor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    
    movimentacoes = db.relationship('Movimentacao', back_populates='setor')

class NaoConformidade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedor.id'), nullable=False)
    insumo_id = db.Column(db.Integer, db.ForeignKey('insumo.id'), nullable=True)
    descricao = db.Column(db.Text, nullable=False)
    data_ocorrido = db.Column(db.DateTime, default=datetime.utcnow)
    acao_tomada = db.Column(db.String(200))
    
    fornecedor = db.relationship('Fornecedor', back_populates='nao_conformidades')
    insumo = db.relationship('Insumo', back_populates='nao_conformidades')

class Recebimento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedor.id'), nullable=False)
    tipo_documento = db.Column(db.String(50), nullable=False)
    numero_documento = db.Column(db.String(100))
    data_recebimento = db.Column(db.Date, nullable=False)
    observacoes = db.Column(db.Text)
    valor_total_documento = db.Column(db.Float, default=0.0)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    usuario = db.Column(db.String(100))

    
    fornecedor = db.relationship('Fornecedor', back_populates='recebimentos')
    itens = db.relationship('ItemRecebido', back_populates='recebimento', cascade="all, delete-orphan")

class ItemRecebido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recebimento_id = db.Column(db.Integer, db.ForeignKey('recebimento.id'), nullable=False)
    insumo_id = db.Column(db.Integer, db.ForeignKey('insumo.id'), nullable=False)
    quantidade_documento = db.Column(db.Float, nullable=False)
    quantidade_conferida = db.Column(db.Float, nullable=False)
    valor_unitario = db.Column(db.Float, nullable=False)
    posicao_destino = db.Column(db.String(50), nullable=False)
    status_conferencia = db.Column(db.String(20), default='PENDENTE')
    
    recebimento = db.relationship('Recebimento', back_populates='itens')
    insumo = db.relationship('Insumo', back_populates='itens_recebidos')



class AjusteInventario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    estoque_id = db.Column(db.Integer, db.ForeignKey('estoque.id'), nullable=False)
    quantidade_anterior = db.Column(db.Float, nullable=False)
    quantidade_nova = db.Column(db.Float, nullable=False)
    diferenca = db.Column(db.Float, nullable=False)
    data_ajuste = db.Column(db.DateTime, default=datetime.utcnow)
    usuario = db.Column(db.String(100)) # Provisório, será usado com o login
    observacao = db.Column(db.String(255))

    estoque = db.relationship('Estoque')
# --- FUNÇÃO PARA GERAR NOVO SKU ---
def gerar_novo_sku():
    # Esta função gera um novo SKU sequencial caso um insumo não tenha um código definido.
    ultimo_insumo_num = Insumo.query.filter(Insumo.sku.like('3%')).order_by(Insumo.sku.desc()).first()
    if ultimo_insumo_num and ultimo_insumo_num.sku.isdigit():
        novo_numero = int(ultimo_insumo_num.sku) + 1
    else:
        # Fallback para caso o último SKU não seja um número puro
        # ou não existam SKUs começando com '3'.
        all_skus = [int(i.sku) for i in Insumo.query.all() if i.sku and i.sku.isdigit()]
        if all_skus:
            novo_numero = max(all_skus) + 1
        else:
            novo_numero = 30000000 # Valor inicial
    return str(novo_numero)


# app.py -> Adicionar estas duas classes junto com os outros modelos

class OrdemDeCompra(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_ordem = db.Column(db.String(50), unique=True, nullable=False)
    data_compra = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    data_entrega_prevista = db.Column(db.Date)
    tipo_compra = db.Column(db.String(50))
    metodo_pagamento = db.Column(db.String(50))
    departamento_solicitante = db.Column(db.String(100))
    
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedor.id'), nullable=False)
    fornecedor = db.relationship('Fornecedor')
    
    subtotal = db.Column(db.Float, default=0.0)
    frete = db.Column(db.Float, default=0.0)
    impostos_percentual = db.Column(db.Float, default=0.0)
    valor_total = db.Column(db.Float, default=0.0)
    observacoes = db.Column(db.Text)
    
    solicitado_por = db.Column(db.String(100))
    aprovado_por = db.Column(db.String(100))
    status_aprovacao = db.Column(db.String(20), default='Pendente') # Ex: Pendente, Aprovado, Rascunho
    
    itens = db.relationship('ItemDaOrdem', back_populates='ordem_de_compra', cascade="all, delete-orphan")
    aprovado_por = db.Column(db.String(100))
    status_aprovacao = db.Column(db.String(20), default='Pendente')
    
    # NOVO CAMPO PARA A DATA DE CHEGADA
    data_chegada_real = db.Column(db.Date, nullable=True)
    
itens = db.relationship('ItemDaOrdem', back_populates='ordem_de_compra', cascade="all, delete-orphan")
class ItemDaOrdem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ordem_de_compra_id = db.Column(db.Integer, db.ForeignKey('ordem_de_compra.id'), nullable=False)
    insumo_id = db.Column(db.Integer, db.ForeignKey('insumo.id'), nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)
    
    ordem_de_compra = db.relationship('OrdemDeCompra', back_populates='itens')
    insumo = db.relationship('Insumo')


# --- INICIALIZAÇÃO DA BASE DE DADOS ---
# Este bloco irá garantir que a base de dados e as tabelas sejam criadas
# sempre que a aplicação iniciar, seja com Gunicorn no OnRender ou localmente.
with app.app_context():
    db.create_all()
    
# --- ROTA PRINCIPAL E CARGA DE DADOS INICIAL ---
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))   
    
    with app.app_context():
        # Executa a carga inicial apenas se a tabela de Insumos estiver vazia
        if not Insumo.query.first():
            print(">>> Base de dados vazia. A iniciar o carregamento inicial de dados...")
            try:
                # --- PASSO 1: Carregar o ficheiro de SKUs (CORRIGIDO PARA LER CSV) ---
                # Usando os nomes exatos dos ficheiros que você enviou
                df_sku = pd.read_excel('Dados limpos Insumos - SKU.xlsx')
                mapa_insumos = {}
                
                print(">>> A processar o ficheiro de SKUs...")
                for _, row in df_sku.iterrows():
                    descricao = str(row.get('Material', '')).strip()
                    if not descricao: continue

                    sku_val = row.get('SKU')
                    sku = None
                    if pd.notna(sku_val) and str(sku_val).strip():
                        try:
                            sku = str(int(float(sku_val)))
                        except (ValueError, TypeError):
                            sku = str(sku_val).strip()

                    estoque_minimo = pd.to_numeric(row.get('estoque_minimo'), errors='coerce')
                    valor_unitario = pd.to_numeric(row.get('Valor Unit.'), errors='coerce')

                    mapa_insumos[descricao.upper()] = {
                        'sku': sku,
                        'estoque_minimo': 0 if pd.isna(estoque_minimo) else int(estoque_minimo),
                        'valor_unitario': 0.0 if pd.isna(valor_unitario) else float(valor_unitario)
                    }

                # --- PASSO 2: Criar todos os Insumos na base de dados ---
                print(f">>> {len(mapa_insumos)} materiais únicos encontrados. A criar registos de Insumos...")
                for desc_mapa, dados in mapa_insumos.items():
                    if not dados['sku']:
                        dados['sku'] = gerar_novo_sku()
                        print(f"      - Material '{desc_mapa}' sem SKU. Gerado novo SKU: {dados['sku']}")

                    insumo_existente = Insumo.query.filter_by(sku=dados['sku']).first()
                    if not insumo_existente:
                        novo_insumo = Insumo(
                            descricao=desc_mapa.title(),
                            sku=dados['sku'],
                            valor_unitario=dados['valor_unitario'],
                            estoque_minimo=dados['estoque_minimo'],
                            unidade_medida='UN'
                        )
                        db.session.add(novo_insumo)
                
                db.session.commit()
                print(">>> Insumos criados com sucesso!")

                # --- PASSO 3: Carregar o ficheiro de Estoque (CORRIGIDO PARA LER CSV) ---
                print(">>> A processar o ficheiro de Estoque...")
                df_estoque = pd.read_excel('Dados limpos Insumos - ESTOQUE.xlsx')
                posicoes_adicionadas = 0
                for _, row in df_estoque.iterrows():
                    descricao_estoque = str(row.get('Material')).strip().upper()
                    if not descricao_estoque or descricao_estoque.lower() == 'nan': continue
                    
                    dados_mapa = mapa_insumos.get(descricao_estoque)
                    if dados_mapa and dados_mapa.get('sku'):
                        insumo_db = Insumo.query.filter_by(sku=dados_mapa['sku']).first()
                        if insumo_db:
                            quantidade = pd.to_numeric(row.get('Quantidade'), errors='coerce')
                            if pd.notna(quantidade) and quantidade > 0:
                                posicao_limpa = re.sub(r'\\s+', '', str(row.get('Posição', 'N/D')))
                                novo_estoque = Estoque(
                                    insumo_id=insumo_db.id,
                                    posicao=posicao_limpa,
                                    quantidade=float(quantidade)
                                )
                                db.session.add(novo_estoque)
                                posicoes_adicionadas += 1
                    else:
                        print(f"      - AVISO: Material '{row.get('Material')}' do ficheiro de estoque não encontrado no mapa de SKUs. Posição ignorada.")

                db.session.commit()
                print(f">>> {posicoes_adicionadas} posições de estoque adicionadas com sucesso!")
                print("\\n>>> CARGA DE DADOS INICIAL CONCLUÍDA! <<<\\n")

            except FileNotFoundError:
                print("\\nERRO CRÍTICO: Os ficheiros CSV de dados não foram encontrados.")
            except Exception as e:
                print(f"\\n>>> ERRO CRÍTICO DURANTE O CARREGAMENTO INICIAL: {e}")
                traceback.print_exc()
                db.session.rollback()

    # --- Bloco 2: Popula os Setores ---
    if not Setor.query.first():
            print(">>> Base de dados de Setores vazia. A popular com dados iniciais...")
            try:
                setores_iniciais = ['Recebimento', 'Controle de Estoque', 'Reabastecimento', 'Picking', 'Expedição', 'Abastecimento de Lojas', 'ADM']
                for nome_setor in setores_iniciais:
                    db.session.add(Setor(nome=nome_setor))
                db.session.commit()
                print(">>> Setores cadastrados com sucesso!")
            except Exception as e:
                 print(f"\\n>>> ERRO AO CADASTRAR SETORES: {e}")
                 db.session.rollback()
    
    return render_template('index.html', username=session.get('username'))



@app.route('/api/estoque/posicao_geral', methods=['GET'])
def get_posicao_estoque():
    """
    Busca e filtra a posição geral do estoque.
    VERSÃO FINAL: Ignora todos os espaços na busca por posição.
    """
    query_insumo = request.args.get('insumo', '').strip()
    query_posicao_raw = request.args.get('posicao', '').strip()
    
    base_query = db.session.query(Estoque, Insumo).join(Insumo, Estoque.insumo_id == Insumo.id)
    
    if query_insumo:
        base_query = base_query.filter(
            Insumo.descricao.ilike(f'%{query_insumo}%') | 
            Insumo.sku.ilike(f'%{query_insumo}%')
        )
        
    if query_posicao_raw:
        # Remove todos os espaços da busca do utilizador
        query_posicao_limpa = re.sub(r'\s+', '', query_posicao_raw)
        # Como os dados no DB já estão limpos, a busca agora será exata
        base_query = base_query.filter(Estoque.posicao.ilike(f'%{query_posicao_limpa}%'))
    
    itens = base_query.order_by(Insumo.descricao, Estoque.posicao).all()
    
    # Ordena os resultados para uma visualização consistente
    itens = base_query.order_by(Insumo.descricao, Estoque.posicao).all()
    
    lista_estoque = []
    for estoque, insumo in itens:
        valor_total = estoque.quantidade * (insumo.valor_unitario or 0.0)
        lista_estoque.append({
            'estoque_id': estoque.id, 
            'sku': insumo.sku, 
            'descricao': insumo.descricao, 
            'posicao': estoque.posicao, 
            'quantidade': estoque.quantidade, 
            'unidade_medida': insumo.unidade_medida,
            'valor_unitario': f"R$ {insumo.valor_unitario or 0.0:.2f}", 
            'valor_total': f"R$ {valor_total:.2f}"
        })
    return jsonify(lista_estoque)

@app.route('/api/transferencias', methods=['POST'])
def transferir_insumo():
    """
    Rota para transferir insumos entre posições ou para um setor (saída).
    VERSÃO CORRIGIDA: Associa a movimentação de saída ao ID do setor.
    """
    data = request.get_json()
    sku = data.get('sku')
    posicao_origem_str = data.get('posicao_origem')
    quantidade_transferir = float(data.get('qtd', 0))
    posicao_destino = data.get('destino', '').strip().upper()
    usuario = session.get('username', 'Sistema')
    

    if not all([sku, posicao_origem_str, quantidade_transferir > 0, posicao_destino]):
        return jsonify({'error': 'Todos os campos são obrigatórios.'}), 400

    estoque_origem = db.session.query(Estoque).join(Insumo).filter(
        Insumo.sku == sku,
        Estoque.posicao == posicao_origem_str
    ).first()

    if not estoque_origem:
        return jsonify({'error': f'Item com SKU {sku} na posição {posicao_origem_str} não encontrado.'}), 404
    
    if quantidade_transferir > estoque_origem.quantidade:
        return jsonify({'error': 'Quantidade a transferir é maior que o disponível.'}), 400

    insumo_id = estoque_origem.insumo_id
    setor_id_associado = None  # Variável para guardar o ID do setor

    if posicao_destino.upper().startswith('SETOR-'):
        nome_setor = posicao_destino.split('-', 1)[1]
        setor = Setor.query.filter(func.lower(Setor.nome) == func.lower(nome_setor)).first()
        
        if not setor:
            # Se o setor não existe, criamos um novo para evitar erros
            setor = Setor(nome=nome_setor.capitalize())
            db.session.add(setor)
            db.session.flush() # Para obter o ID do novo setor imediatamente
        
        setor_id_associado = setor.id
        estoque_origem.quantidade -= quantidade_transferir
        tipo_movimentacao = 'SAIDA'
        mensagem = f'Saída de {quantidade_transferir} do insumo {sku} para o setor {nome_setor} registada com sucesso.'
    else:
        estoque_destino = Estoque.query.filter_by(insumo_id=insumo_id, posicao=posicao_destino).first()
        if not estoque_destino:
            estoque_destino = Estoque(insumo_id=insumo_id, posicao=posicao_destino, quantidade=0)
            db.session.add(estoque_destino)
        
        estoque_origem.quantidade -= quantidade_transferir
        estoque_destino.quantidade += quantidade_transferir
        tipo_movimentacao = 'TRANSFERENCIA'
        mensagem = f'Transferência de {quantidade_transferir} do insumo {sku} de {posicao_origem_str} para {posicao_destino} realizada.'

    if estoque_origem.quantidade <= 0:
        db.session.delete(estoque_origem)

    mov = Movimentacao(
        insumo_id=insumo_id,
        setor_id=setor_id_associado, # <-- PONTO-CHAVE: Guardamos o ID do setor aqui!
        quantidade=quantidade_transferir,
        tipo=tipo_movimentacao,
        posicao_origem=posicao_origem_str,
        posicao_destino=posicao_destino,
        usuario=usuario,
        data_hora=datetime.utcnow()
        
    )
    db.session.add(mov)

    try:
        db.session.commit()
        return jsonify({'message': mensagem})
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': f'Erro ao salvar a transferência: {e}'}), 500


@app.route('/api/insumos/sku/<sku>')
def get_insumo_by_sku(sku):
    sku = sku.strip()
    insumo = Insumo.query.filter(Insumo.sku.ilike(sku)).first()
    if not insumo:
        return jsonify({'error': 'Insumo não encontrado'}), 404
    return jsonify(insumo.to_dict())

@app.route('/api/estoque/posicoes/<sku>')
def get_posicoes_por_sku(sku):
    """
    Retorna todas as posições e quantidades de um determinado SKU.
    CORRIGIDO para buscar pelo SKU do insumo relacionado.
    """
    insumo = Insumo.query.filter(Insumo.sku.ilike(sku.strip())).first()
    if not insumo:
        return jsonify([]), 404 # Retorna lista vazia se o insumo não existe

    posicoes = Estoque.query.filter_by(insumo_id=insumo.id).all()
    
    return jsonify([
        {
            'posicao': p.posicao,
            'quantidade': p.quantidade,
            'unidade': insumo.unidade_medida
        } for p in posicoes
    ])
    

@app.route('/api/estoque/item/<int:estoque_id>', methods=['GET'])
def get_raw_item_estoque(estoque_id):
    """
    Busca os detalhes de um item de estoque específico pelo seu ID.
    VERSÃO FINAL E SEGURA: Usa uma consulta direta e trata todos os valores nulos.
    """
    try:
        # 1. Busca o item de estoque diretamente pelo seu ID (mais seguro)
        estoque = Estoque.query.get(estoque_id)

        if not estoque:
            return jsonify({'error': 'Item de estoque com o ID fornecido não foi encontrado.'}), 404

        # 2. Acede ao insumo relacionado de forma segura
        insumo = estoque.insumo
        if not insumo:
             return jsonify({'error': 'Insumo relacionado a este item de estoque não foi encontrado.'}), 404

        # 3. Busca a última movimentação
        ultima_mov = Movimentacao.query.filter(
            (Movimentacao.posicao_origem == estoque.posicao) | (Movimentacao.posicao_destino == estoque.posicao),
            Movimentacao.insumo_id == insumo.id
        ).order_by(Movimentacao.data_hora.desc()).first()

        ultima_mov_local_str = "Nenhuma movimentação registrada"
        usuario_ultima_mov = "N/A"

        if ultima_mov and ultima_mov.data_hora:
            utc_tz = pytz.utc
            sao_paulo_tz = pytz.timezone('America/Sao_Paulo')
            utc_time = utc_tz.localize(ultima_mov.data_hora) if ultima_mov.data_hora.tzinfo is None else ultima_mov.data_hora
            sao_paulo_time = utc_time.astimezone(sao_paulo_tz)
            ultima_mov_local_str = sao_paulo_time.strftime('%d/%m/%Y às %H:%M')
            usuario_ultima_mov = ultima_mov.usuario or "Sistema" 

        # 4. Calcula o valor total de forma segura
        valor_unitario_seguro = insumo.valor_unitario or 0.0
        valor_total_calculado = estoque.quantidade * valor_unitario_seguro

        # 5. Retorna a resposta JSON completa
        return jsonify({
            'estoque_id': estoque.id,
            'sku': insumo.sku,
            'descricao': insumo.descricao,
            'posicao': estoque.posicao,
            'quantidade': estoque.quantidade,
            'unidade_medida': insumo.unidade_medida,
            'valor_unitario': valor_unitario_seguro,
            'estoque_minimo': insumo.estoque_minimo,
            'valor_total': valor_total_calculado,
            'ultima_movimentacao': ultima_mov_local_str,
            'usuario_movimentacao': usuario_ultima_mov
        })

    except Exception as e:
        print(f"ERRO AO BUSCAR DETALHES DO ITEM {estoque_id}: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Ocorreu um erro interno no servidor ao buscar detalhes do item.'}), 500



@app.route('/api/fornecedores', methods=['GET', 'POST'])
def api_fornecedores():
    """
    Rota para listar todos os fornecedores (GET) ou
    criar um novo fornecedor (POST).
    VERSÃO CORRIGIDA: Trata o campo 'ativo' como um booleano corretamente.
    """
    if request.method == 'GET':
        fornecedores = Fornecedor.query.order_by(Fornecedor.razao_social).all()
        return jsonify([{'id': f.id, 'razao_social': f.razao_social, 'cnpj': f.cnpj, 'ativo': f.ativo} for f in fornecedores])
    
    if request.method == 'POST':
        data = request.json
        if not data or not data.get('razao_social') or not data.get('cnpj'):
            return jsonify({'error': 'Razão Social e CNPJ são obrigatórios'}), 400
        
        cnpj_limpo = re.sub(r'[./-]', '', data['cnpj'])
        if Fornecedor.query.filter_by(cnpj=cnpj_limpo).first():
            return jsonify({'error': f'O CNPJ "{data["cnpj"]}" já está cadastrado.'}), 409
        
        novo_fornecedor = Fornecedor()
        for key, value in data.items():
            if hasattr(novo_fornecedor, key):
                # A conversão para booleano já é feita pelo JSON, não precisamos de tratamento extra.
                # A linha incorreta foi removida daqui.
                setattr(novo_fornecedor, key, value)
        
        novo_fornecedor.cnpj = cnpj_limpo

        try:
            db.session.add(novo_fornecedor)
            db.session.commit()
            return jsonify({'message': 'Fornecedor cadastrado com sucesso!', 'fornecedor': {'id': novo_fornecedor.id, 'razao_social': novo_fornecedor.razao_social}}), 201
        except Exception as e:
            db.session.rollback()
            traceback.print_exc()
            return jsonify({'error': f'Ocorreu um erro interno: {e}'}), 500
        

# app.py -> Substituir a função api_fornecedor_detalhe

@app.route('/api/fornecedores/<int:id>', methods=['GET', 'PUT'])
def api_fornecedor_detalhe(id):
    """ 
    Rota para obter os detalhes (GET) ou atualizar (PUT) um fornecedor.
    VERSÃO CORRIGIDA: Trata o campo 'ativo' como um booleano corretamente.
    """
    fornecedor_a_editar = Fornecedor.query.get_or_404(id)

    if request.method == 'GET':
        dados = {c.name: getattr(fornecedor_a_editar, c.name) for c in fornecedor_a_editar.__table__.columns}
        return jsonify(dados)

    if request.method == 'PUT':
        data = request.json
        if not data:
            return jsonify({'error': 'Nenhum dado enviado para atualização'}), 400

        if 'cnpj' in data and data['cnpj']:
            cnpj_limpo = re.sub(r'[./-]', '', data['cnpj'])
            outro_fornecedor = Fornecedor.query.filter(Fornecedor.cnpj == cnpj_limpo, Fornecedor.id != id).first()
            if outro_fornecedor:
                return jsonify({'error': f'O CNPJ "{data["cnpj"]}" já pertence ao fornecedor "{outro_fornecedor.razao_social}".'}), 409
        
        for key, value in data.items():
            if key == 'id': continue
            if hasattr(fornecedor_a_editar, key):
                 # A conversão para booleano já é feita pelo JSON, não precisamos de tratamento extra.
                 # A linha incorreta foi removida daqui.
                if key == 'cnpj':
                    value = re.sub(r'[./-]', '', value)
                setattr(fornecedor_a_editar, key, value)
        
        try:
            db.session.commit()
            return jsonify({'message': 'Fornecedor atualizado com sucesso!'})
        except Exception as e:
            db.session.rollback()
            traceback.print_exc()
            return jsonify({'error': f'Ocorreu um erro interno ao atualizar: {e}'}), 500
        
@app.route('/api/fornecedores/<int:id>/ncs', methods=['GET', 'POST'])
def api_fornecedor_ncs(id):
    """ Rota para listar (GET) ou adicionar (POST) não conformidades a um fornecedor. """
    fornecedor = Fornecedor.query.get_or_404(id)
    
    if request.method == 'GET':
        ncs = fornecedor.nao_conformidades # Acessa a relação definida no modelo
        lista_ncs = []
        for nc in ncs:
            lista_ncs.append({
                'id': nc.id,
                'descricao': nc.descricao,
                'data_ocorrido': nc.data_ocorrido.strftime('%d/%m/%Y'),
                'acao_tomada': nc.acao_tomada,
            })
        return jsonify(lista_ncs)

    if request.method == 'POST':
        data = request.json
        if not data or not data.get('descricao'):
            return jsonify({'error': 'A descrição da não conformidade é obrigatória.'}), 400
        
        nova_nc = NaoConformidade(
            fornecedor_id=id,
            descricao=data['descricao'],
            acao_tomada=data.get('acao_tomada', ''),
            data_ocorrido=datetime.utcnow()
        )
        db.session.add(nova_nc)
        db.session.commit()
        return jsonify({'message': 'Não conformidade registrada com sucesso!'}), 201

@app.route('/api/setores', methods=['GET'])
def api_setores():
    """ Rota para listar todos os setores cadastrados. """
    setores = Setor.query.order_by(Setor.id).all()
    # No futuro, pode adicionar estatísticas aqui para cada cartão
    return jsonify([{'id': s.id, 'nome': s.nome} for s in setores])

@app.route('/api/setores/<int:id>/analytics', methods=['GET'])
def api_setor_analytics(id):
    """ 
    Rota que calcula e retorna os dados analíticos para um setor específico.
    VERSÃO FINAL: Adiciona a conversão de fuso horário para exibir a hora local correta.
    """
    setor = Setor.query.get_or_404(id)

    # 1. Busca todas as movimentações de SAÍDA para este setor
    movimentacoes_do_setor = Movimentacao.query.filter_by(
        setor_id=setor.id, 
        tipo='SAIDA'
    ).order_by(Movimentacao.data_hora.desc()).all()

    # --- A partir daqui, todos os cálculos são feitos em Python ---

    # 2. Prepara os dados para o histórico (os 50 mais recentes)
    historico_formatado = []
    # Define os fusos horários uma única vez
    utc_tz = pytz.utc
    sao_paulo_tz = pytz.timezone('America/Sao_Paulo')

    for mov in movimentacoes_do_setor[:50]:
        insumo = mov.insumo
        if insumo:
            # --- LÓGICA DE CONVERSÃO DE FUSO HORÁRIO ---
            # Converte a data/hora de UTC para o fuso horário de São Paulo
            data_utc = mov.data_hora.replace(tzinfo=utc_tz)
            data_local = data_utc.astimezone(sao_paulo_tz)
            # -------------------------------------------

            historico_formatado.append({
                'data': data_local.strftime('%d/%m/%Y %H:%M'), # Usa a data local formatada
                'descricao_insumo': insumo.descricao,
                'quantidade': mov.quantidade,
                'unidade': insumo.unidade_medida,
                'valor_unitario': insumo.valor_unitario or 0,
                'valor_total': mov.quantidade * (insumo.valor_unitario or 0)
            })
    # 3. Calcula os Insumos mais consumidos (Top 5 por valor)
    consumo_por_insumo = {}
    for mov in movimentacoes_do_setor: # Usa todos os dados para os cálculos
        if mov.insumo:
            valor_mov = mov.quantidade * (mov.insumo.valor_unitario or 0)
            dados = consumo_por_insumo.get(mov.insumo.id, {'valor_total': 0, 'quantidade_total': 0})
            consumo_por_insumo[mov.insumo.id] = {
                'descricao': mov.insumo.descricao,
                'unidade': mov.insumo.unidade_medida,
                'valor_total': dados['valor_total'] + valor_mov,
                'quantidade_total': dados['quantidade_total'] + mov.quantidade,
            }
    top_5_insumos = sorted(consumo_por_insumo.values(), key=lambda x: x['valor_total'], reverse=True)[:5]
    
    # 4. Calcula o Consumo Mês a Mês (para o gráfico)
    consumo_mensal_dict = {}
    for mov in movimentacoes_do_setor:
        if mov.insumo:
            mes = mov.data_hora.strftime('%Y-%m')
            valor_mov = mov.quantidade * (mov.insumo.valor_unitario or 0)
            consumo_mensal_dict[mes] = consumo_mensal_dict.get(mes, 0) + valor_mov
    
    consumo_mensal_labels = sorted(consumo_mensal_dict.keys())
    consumo_mensal_data = [consumo_mensal_dict[mes] for mes in consumo_mensal_labels]
    
    # 5. Calcula o Consumo médio diário
    consumo_medio_diario = 0
    if movimentacoes_do_setor:
        consumo_total_periodo = sum(m.quantidade * (m.insumo.valor_unitario or 0) for m in movimentacoes_do_setor if m.insumo)
        data_inicio = min(m.data_hora for m in movimentacoes_do_setor)
        data_fim = max(m.data_hora for m in movimentacoes_do_setor)
        dias = (data_fim - data_inicio).days if data_fim > data_inicio else 1
        consumo_medio_diario = consumo_total_periodo / max(dias, 1)

    # 6. Monta a resposta final em JSON
    return jsonify({
        'setor_nome': setor.nome,
        'insumos_mais_consumidos': top_5_insumos,
        'consumo_mensal': {
            'labels': consumo_mensal_labels,
            'data': consumo_mensal_data
        },
        'consumo_medio_diario': consumo_medio_diario,
        'historico': historico_formatado
    })


@app.route('/api/estoque/exportar', methods=['GET'])
def exportar_estoque_excel():
    """
    Gera um relatório completo do estoque em formato .xlsx e
    o disponibiliza para download.
    """
    try:
        # 1. Busca todos os itens do estoque, juntando com os dados dos insumos
        query = db.session.query(
            Insumo.sku,
            Insumo.descricao,
            Estoque.posicao,
            Estoque.quantidade,
            Insumo.unidade_medida,
            Insumo.valor_unitario
        ).join(Estoque).order_by(Insumo.descricao, Estoque.posicao).all()

        if not query:
            return jsonify({'message': 'Nenhum item no estoque para exportar.'}), 404

        # 2. Prepara os dados para o DataFrame do Pandas
        export_data = []
        for sku, descricao, posicao, qtd, um, vlr_unit in query:
            valor_total = qtd * (vlr_unit or 0)
            export_data.append({
                'SKU': sku,
                'NOME DO INSUMO': descricao,
                'POSIÇÃO': posicao,
                'QUANTIDADE': qtd,
                'UNIDADE': um,
                'VALOR UNITÁRIO': vlr_unit,
                'VALOR TOTAL': valor_total
            })
        
        # 3. Cria o DataFrame e o ficheiro Excel em memória
        df = pd.DataFrame(export_data)
        
        output = BytesIO()
        # Usa o 'ExcelWriter' para formatar os números e auto-ajustar as colunas
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Estoque')
            
            # Formatação (opcional, mas melhora a leitura)
            worksheet = writer.sheets['Estoque']
            for idx, col in enumerate(df):  # itera sobre as colunas do df
                series = df[col]
                max_len = max((
                    series.astype(str).map(len).max(),
                    len(str(series.name))
                )) + 2  # adiciona um pouco de espaço extra
                worksheet.column_dimensions[chr(65 + idx)].width = max_len # auto-ajuste da largura

        output.seek(0)
        
        # 4. Envia o ficheiro para o utilizador
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'relatorio_estoque_{datetime.now().strftime("%Y-%m-%d")}.xlsx'
        )

    except Exception as e:
        print(f"Erro ao exportar Excel: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Ocorreu um erro interno ao gerar o arquivo Excel.'}), 500

# app.py -> Substituir a função extrair_dados_pdf inteira


@app.route('/api/recebimento/upload-pdf', methods=['POST'])
def extrair_dados_pdf():
    """
    Extrai dados de um arquivo PDF de nota fiscal.
    VERSÃO FINAL 3.0: Após encontrar um insumo existente pelo SKU, retorna a 
    descrição limpa da base de dados em vez da descrição do PDF.
    """
    if 'pdf_file' not in request.files:
        return jsonify({'error': 'Nenhum ficheiro PDF foi enviado.'}), 400
    file = request.files['pdf_file']
    if file.filename == '':
        return jsonify({'error': 'Nome de ficheiro inválido.'}), 400

    try:
        text_completo = ''
        todas_as_tabelas = []
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text_completo += page.extract_text(x_tolerance=2) or ''
                page_tables = page.extract_tables()
                if page_tables:
                    todas_as_tabelas.extend(page_tables)
        
        # Lógica para extrair fornecedor e número do documento...
        fornecedor_sugerido, numero_documento_sugerido = None, ''
        cnpj_matches = re.findall(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', text_completo)
        if cnpj_matches:
            for cnpj_str in cnpj_matches:
                cnpj_limpo = re.sub(r'[./-]', '', cnpj_str)
                fornecedor = Fornecedor.query.filter_by(cnpj=cnpj_limpo).first()
                if fornecedor:
                    fornecedor_sugerido = {'id': fornecedor.id, 'text': fornecedor.razao_social}
                    break
        
        numero_doc_match = re.search(r'N[º°]\.?\s*([\d\.-]+)', text_completo, re.IGNORECASE)
        if numero_doc_match:
            numero_documento_sugerido = numero_doc_match.group(1).replace('.', '').replace('-', '')


        # --- LÓGICA DE PROCESSAMENTO DE ITENS REFINADA ---
        itens_sugeridos = []
        novos_produtos_criados = 0
        
        for tabela in todas_as_tabelas:
            if not tabela or not tabela[0]: continue

            header_processado = [str(h).replace('\n', ' ').strip().upper() if h else '' for h in tabela[0]]
            
            idx_desc, idx_qtd, idx_vlr_unit, idx_sku_col = -1, -1, -1, -1
            for i, h in enumerate(header_processado):
                if 'DESCRI' in h: idx_desc = i
                elif 'QTD' in h or 'QUANT' in h: idx_qtd = i
                elif 'UNIT' in h: idx_vlr_unit = i
                elif 'SKU' in h or 'CÓD' in h: idx_sku_col = i

            if not (idx_desc != -1 and idx_qtd != -1 and idx_vlr_unit != -1):
                continue
            
            for linha_dados in tabela[1:]:
                if not linha_dados or len(linha_dados) <= max(idx_desc, idx_qtd, idx_vlr_unit): continue
                
                descricao_pdf = str(linha_dados[idx_desc] or '').replace('\n', ' ').strip()
                if not descricao_pdf: continue
                
                try:
                    qtd_str = str(linha_dados[idx_qtd] or '0').replace('.', '').replace(',', '.')
                    vlr_unit_str = str(linha_dados[idx_vlr_unit] or '0').replace('.', '').replace(',', '.')
                    quantidade_doc = float(qtd_str)
                    valor_unit = float(vlr_unit_str)
                except (ValueError, TypeError): continue

                insumo_encontrado = None
                foi_criado_agora = False

                # Lógica de busca por prioridade...
                if idx_sku_col != -1 and len(linha_dados) > idx_sku_col:
                    sku_pdf = str(linha_dados[idx_sku_col] or '').strip()
                    if sku_pdf: insumo_encontrado = Insumo.query.filter_by(sku=sku_pdf).first()
                
                if not insumo_encontrado:
                    match = re.search(r'\b(\d{8})\b', descricao_pdf)
                    if match:
                        sku_pescado = match.group(1)
                        insumo_encontrado = Insumo.query.filter_by(sku=sku_pescado).first()
                
                if not insumo_encontrado:
                    insumo_encontrado = Insumo.query.filter(Insumo.descricao.ilike(descricao_pdf)).first()
                
                if not insumo_encontrado:
                    sku_para_novo_insumo = (re.search(r'\b(\d{8})\b', descricao_pdf).group(1) if re.search(r'\b(\d{8})\b', descricao_pdf) else gerar_novo_sku())
                    if Insumo.query.filter_by(sku=sku_para_novo_insumo).first(): sku_para_novo_insumo = gerar_novo_sku()

                    print(f"AVISO: Insumo '{descricao_pdf}' não encontrado. Criando novo com SKU: {sku_para_novo_insumo}...")
                    novo_insumo = Insumo(descricao=descricao_pdf.title(), sku=sku_para_novo_insumo, valor_unitario=valor_unit)
                    db.session.add(novo_insumo)
                    db.session.flush()
                    insumo_encontrado = novo_insumo
                    novos_produtos_criados += 1
                    foi_criado_agora = True
                
                # *** PONTO-CHAVE DA CORREÇÃO ***
                # Usa a descrição do insumo encontrado na base de dados, não a do PDF.
                itens_sugeridos.append({
                    'insumo_id': insumo_encontrado.id,
                    'descricao': insumo_encontrado.descricao, # <-- USA A DESCRIÇÃO DO BANCO DE DADOS
                    'quantidade_documento': quantidade_doc,
                    'valor_unitario': valor_unit,
                    'unidade_medida': insumo_encontrado.unidade_medida,
                    'novo': foi_criado_agora
                })
            
            if itens_sugeridos: break

        db.session.commit()
        
        mensagem = "Dados extraídos com sucesso!"
        if novos_produtos_criados > 0:
            mensagem = f"{novos_produtos_criados} novo(s) produto(s) foi/foram cadastrado(s) automaticamente!"
        elif not itens_sugeridos:
            mensagem = "PDF lido, mas nenhum item correspondente foi encontrado na base de dados."

        return jsonify({
            'fornecedor': fornecedor_sugerido,
            'numero_documento': numero_documento_sugerido,
            'itens': itens_sugeridos,
            'message': mensagem
        })

    except Exception as e:
        db.session.rollback()
        print(f"ERRO CRÍTICO AO PROCESSAR PDF: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Ocorreu um erro inesperado ao ler o ficheiro PDF: {e}'}), 500



@app.route('/api/recebimentos/consultar/<numero_documento>', methods=['GET'])
def consultar_recebimento(numero_documento):
    """
    Busca um recebimento pelo número do documento e retorna
    seus detalhes, incluindo os itens.
    """
    try:
        # Busca o recebimento pelo número do documento
        recebimento = Recebimento.query.filter_by(numero_documento=numero_documento).first()

        # Se não encontrar, retorna um erro 404 (Not Found)
        if not recebimento:
            return jsonify({'error': 'Nenhum recebimento encontrado com este número de documento.'}), 404

        # Prepara a lista de itens do recebimento
        itens_da_nota = []
        for item in recebimento.itens:
            itens_da_nota.append({
                'sku': item.insumo.sku,
                'descricao': item.insumo.descricao,
                'quantidade_conferida': item.quantidade_conferida,
                'valor_unitario': item.valor_unitario,
                'valor_total': item.quantidade_conferida * item.valor_unitario
            })
        
        # Monta a resposta JSON com todos os dados necessários
        resultado = {
            'id': recebimento.id,
            'numero_documento': recebimento.numero_documento,
            'fornecedor_nome': recebimento.fornecedor.razao_social,
            'data_recebimento': recebimento.data_recebimento.strftime('%d/%m/%Y'),
            'valor_total_documento': recebimento.valor_total_documento,
            'itens': itens_da_nota
        }

        return jsonify(resultado)

    except Exception as e:
        print(f"Erro ao consultar recebimento: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Ocorreu um erro interno ao processar a sua consulta.'}), 500

@app.route('/api/fornecedores/buscar', methods=['GET'])
def buscar_fornecedores():
    """
    Rota para a busca de fornecedores em campos Select2.
    Recebe um parâmetro de busca 'q' e retorna uma lista de fornecedores.
    """
    # O Select2 envia o termo de busca no parâmetro 'q'
    termo_busca = request.args.get('q', '').lower()
    
    query = Fornecedor.query.filter(Fornecedor.ativo == True)

    if termo_busca:
        query = query.filter(
            Fornecedor.razao_social.ilike(f'%{termo_busca}%') |
            Fornecedor.nome_fantasia.ilike(f'%{termo_busca}%') |
            Fornecedor.cnpj.ilike(f'%{termo_busca}%')
        )

    # Limita a 15 resultados para não sobrecarregar
    fornecedores = query.limit(15).all()

    # Formata a resposta no padrão que o Select2 espera: uma lista de objetos com 'id' e 'text'
    resultados = [{'id': f.id, 'text': f.razao_social} for f in fornecedores]
    
    return jsonify(resultados)

# app.py -> Adicionar esta rota junto com as outras no seu ficheiro

@app.route('/api/insumos/buscar', methods=['GET'])
def buscar_insumos():
    """
    Rota para a busca de insumos em campos Select2.
    Recebe um parâmetro de busca 'q' e retorna uma lista de insumos.
    """
    termo_busca = request.args.get('q', '').lower()
    
    query = Insumo.query

    if termo_busca:
        query = query.filter(
            Insumo.descricao.ilike(f'%{termo_busca}%') |
            Insumo.sku.ilike(f'%{termo_busca}%')
        )

    insumos = query.limit(15).all()

    # Formata a resposta no padrão que o Select2 espera, incluindo dados extras
    # que usamos no JavaScript (como 'valor_unitario').
    resultados = [
        {
            'id': i.id, 
            'text': f"{i.descricao} (SKU: {i.sku})",
            'valor_unitario': i.valor_unitario 
        } 
        for i in insumos
    ]
    
    return jsonify(resultados)

# app.py -> Substituir a função registrar_ordem_de_compra por esta versão

@app.route('/api/ordens-de-compra', methods=['POST'])
def registrar_ordem_de_compra():
    # Envolve toda a lógica num bloco try...except
    try:
        data = request.get_json()
        
        # Validação dos dados recebidos
        required_fields = ['numero_ordem', 'data_compra', 'fornecedor_id', 'itens']
        if not all(field in data for field in required_fields) or not data['itens']:
            return jsonify({'error': 'Dados incompletos. Verifique o número da ordem, data, fornecedor e itens.'}), 400

        if OrdemDeCompra.query.filter_by(numero_ordem=data['numero_ordem']).first():
            return jsonify({'error': f'A ordem de compra "{data["numero_ordem"]}" já existe.'}), 409

        # Cria a Ordem de Compra principal
        nova_ordem = OrdemDeCompra(
            numero_ordem=data['numero_ordem'],
            data_compra=datetime.strptime(data['data_compra'], '%Y-%m-%d').date(),
            data_entrega_prevista=datetime.strptime(data['data_entrega_prevista'], '%Y-%m-%d').date() if data.get('data_entrega_prevista') else None,
            tipo_compra=data.get('tipo_compra'),
            metodo_pagamento=data.get('metodo_pagamento'),
            departamento_solicitante=data.get('departamento_solicitante'),
            fornecedor_id=data['fornecedor_id'],
            subtotal=float(data.get('subtotal', 0)),
            frete=float(data.get('frete', 0)),
            impostos_percentual=float(data.get('impostos_percentual', 0)),
            valor_total=float(data.get('valor_total', 0)),
            observacoes=data.get('observacoes'),
            solicitado_por=data.get('solicitado_por'),
            status_aprovacao=data.get('status_aprovacao', 'Pendente')
        )
        db.session.add(nova_ordem)
        db.session.flush() # Para obter o ID da nova ordem antes de salvar os itens

        # Adiciona os itens à ordem de compra
        for item_data in data['itens']:
            if not item_data.get('insumo_id'): continue # Ignora itens sem insumo selecionado
            novo_item = ItemDaOrdem(
                ordem_de_compra_id=nova_ordem.id,
                insumo_id=item_data['insumo_id'],
                quantidade=float(item_data['quantidade']),
                preco_unitario=float(item_data['preco_unitario'])
            )
            db.session.add(novo_item)

        db.session.commit()
        return jsonify({'message': f'Ordem de compra {nova_ordem.numero_ordem} registrada com sucesso!'}), 201

    except Exception as e:
        # Se qualquer erro acontecer, ele será capturado aqui
        db.session.rollback() # Desfaz qualquer alteração parcial no banco de dados
        print(f"Erro ao registrar ordem de compra: {e}")
        traceback.print_exc() # Imprime o erro detalhado na consola do servidor
        # E retorna uma mensagem de erro em JSON para o frontend
        return jsonify({'error': 'Ocorreu um erro interno ao salvar a ordem de compra. Verifique os dados enviados e tente novamente.'}), 500


@app.route('/api/ordens-de-compra', methods=['GET'])
def listar_ordens_de_compra():
    """ Lista todas as ordens de compra com cálculo de status de atraso. """
    try:
        ordens = OrdemDeCompra.query.order_by(OrdemDeCompra.data_compra.desc()).all()
        resultado = []
        hoje = datetime.utcnow().date()

        for ordem in ordens:
            status = 'Pendente'
            atraso = 0
            
            if ordem.data_chegada_real:
                status = 'Recebido'
                if ordem.data_entrega_prevista and ordem.data_chegada_real > ordem.data_entrega_prevista:
                    atraso = (ordem.data_chegada_real - ordem.data_entrega_prevista).days
                    status = f'Recebido com {atraso} dia(s) de atraso'
                else:
                    status = 'Recebido no prazo'
            elif ordem.data_entrega_prevista and hoje > ordem.data_entrega_prevista:
                atraso = (hoje - ordem.data_entrega_prevista).days
                status = f'Atrasado ({atraso} dia(s))'
            
            resultado.append({
                'id': ordem.id,
                'numero_ordem': ordem.numero_ordem,
                'fornecedor_nome': ordem.fornecedor.razao_social,
                'data_compra': ordem.data_compra.strftime('%d/%m/%Y'),
                'data_entrega_prevista': ordem.data_entrega_prevista.strftime('%d/%m/%Y') if ordem.data_entrega_prevista else 'N/A',
                'valor_total': ordem.valor_total,
                'status': status,
                'atraso_dias': atraso,
                'data_chegada_real': ordem.data_chegada_real.strftime('%d/%m/%Y') if ordem.data_chegada_real else None
            })
            
        return jsonify(resultado)

    except Exception as e:
        print(f"Erro ao listar ordens de compra: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Ocorreu um erro interno ao buscar as ordens de compra.'}), 500


@app.route('/api/ordens-de-compra/<int:id>/registrar-chegada', methods=['POST'])
def registrar_chegada_ordem(id):
    """ Registra a data de chegada real de uma ordem de compra. """
    ordem = OrdemDeCompra.query.get_or_404(id)
    data = request.get_json()
    
    if not data or not data.get('data_chegada'):
        return jsonify({'error': 'A data de chegada é obrigatória.'}), 400

    try:
        ordem.data_chegada_real = datetime.strptime(data['data_chegada'], '%Y-%m-%d').date()
        db.session.commit()
        return jsonify({'message': 'Data de chegada registrada com sucesso!'})
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao registrar chegada: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Ocorreu um erro interno.'}), 500

@app.route('/api/ordens-de-compra/<int:id>', methods=['GET'])
def get_ordem_de_compra_detalhe(id):
    """ Busca e retorna os detalhes completos de uma Ordem de Compra. """
    ordem = OrdemDeCompra.query.get_or_404(id)
    
    # Converte os dados principais da ordem para um dicionário
    resultado = {c.name: getattr(ordem, c.name) for c in ordem.__table__.columns if c.name not in ['data_compra', 'data_entrega_prevista']}
    
    # Formata as datas para o padrão YYYY-MM-DD que os inputs type="date" entendem
    resultado['data_compra'] = ordem.data_compra.strftime('%Y-%m-%d') if ordem.data_compra else ''
    resultado['data_entrega_prevista'] = ordem.data_entrega_prevista.strftime('%Y-%m-%d') if ordem.data_entrega_prevista else ''

    # Adiciona os itens da ordem
    itens = []
    for item in ordem.itens:
        itens.append({
            'insumo_id': item.insumo_id,
            'insumo_text': f"{item.insumo.descricao} (SKU: {item.insumo.sku})",
            'quantidade': item.quantidade,
            'preco_unitario': item.preco_unitario
        })
    resultado['itens'] = itens
    
    return jsonify(resultado)


# app.py - VERSÃO COM ROTAS DO DASHBOARD SEPARADAS

# ... (todo o início do seu arquivo, imports, modelos, etc. - MANTENHA COMO ESTÁ)
import os
import re
import pytz
import pdfplumber
import pandas as pd
from io import BytesIO
from flask import Flask, jsonify, request, render_template, send_file, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy import func, cast, Date
import traceback
from werkzeug.security import generate_password_hash, check_password_hash
import unicodedata
from functools import wraps


@app.route('/api/dashboard/main', methods=['GET'])
def get_dashboard_main_data():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10
        periodo_dias = request.args.get('periodo', 30, type=int)
        filtro_busca = request.args.get('busca', '').strip()
        filtro_status_req = request.args.get('status', 'Todos').strip()
        filtro_status_normalizado = normalize_text(filtro_status_req)

        data_limite = datetime.utcnow() - timedelta(days=periodo_dias)
        
        # --- Lógica da Tabela ---
        base_query = Insumo.query
        if filtro_busca:
            base_query = base_query.filter(
                Insumo.descricao.ilike(f'%{filtro_busca}%') | Insumo.sku.ilike(f'%{filtro_busca}%'))
        
        insumos_filtrados = base_query.all()
        todos_itens_calculados = []
        for insumo in insumos_filtrados:
            estoque_total = db.session.query(func.sum(Estoque.quantidade)).filter(Estoque.insumo_id == insumo.id).scalar() or 0
            qtd_consumida = db.session.query(func.sum(Movimentacao.quantidade)).filter(
                Movimentacao.insumo_id == insumo.id, Movimentacao.tipo == 'SAIDA', Movimentacao.data_hora >= data_limite).scalar() or 0
            saida_media_diaria = qtd_consumida / periodo_dias if periodo_dias > 0 else 0
            
            status_key, dias_de_estoque_display = 'bom', 'N/A'
            if estoque_total <= 0: status_key = 'critico'
            elif insumo.estoque_minimo > 0 and estoque_total <= insumo.estoque_minimo: status_key = 'critico'
            elif insumo.estoque_minimo > 0 and estoque_total <= insumo.estoque_minimo * 1.5: status_key = 'atencao'
            else:
                if saida_media_diaria > 0:
                    dias = estoque_total / saida_media_diaria
                    dias_de_estoque_display = int(dias)
                    if dias <= 30: status_key = 'atencao'
                    elif dias <= 60: status_key = 'bom'
                    else: status_key = 'excelente'
                else: status_key = 'excelente'
            
            todos_itens_calculados.append({'id': insumo.id, 'descricao': insumo.descricao, 'sku': insumo.sku, 'estoque_atual': estoque_total, 'saida_media_diaria': round(saida_media_diaria, 2), 'dias_de_estoque': dias_de_estoque_display, 'consumo_qtd': qtd_consumida, 'consumo_valor': qtd_consumida * (insumo.valor_unitario or 0), 'status_key': status_key})

        if filtro_status_normalizado != 'todos':
            itens_para_tabela = [item for item in todos_itens_calculados if item['status_key'] == filtro_status_normalizado]
        else:
            itens_para_tabela = todos_itens_calculados

        total_items_filtrados = len(itens_para_tabela)
        paginated_items = itens_para_tabela[(page - 1) * per_page : page * per_page]
        total_pages = (total_items_filtrados + per_page - 1) // per_page if per_page > 0 else 0

        # --- Lógica dos KPIs e Resumo de Status ---
        total_skus_distintos = Insumo.query.count()
        total_valor_estoque = db.session.query(func.sum(Estoque.quantidade * Insumo.valor_unitario)).join(Insumo).scalar() or 0
        
        consumo_total_periodo, status_counts = 0, {'excelente': 0, 'bom': 0, 'atencao': 0, 'critico': 0}
        all_insumos_for_kpi = Insumo.query.all()
        for insumo in all_insumos_for_kpi:
            qtd_consumida = db.session.query(func.sum(Movimentacao.quantidade)).filter(Movimentacao.insumo_id == insumo.id, Movimentacao.tipo == 'SAIDA', Movimentacao.data_hora >= data_limite).scalar() or 0
            consumo_total_periodo += qtd_consumida * (insumo.valor_unitario or 0)
            estoque_total = db.session.query(func.sum(Estoque.quantidade)).filter(Estoque.insumo_id == insumo.id).scalar() or 0
            saida_media = (qtd_consumida / periodo_dias) if periodo_dias > 0 else 0
            
            if estoque_total <= 0: status_counts['critico'] += 1
            elif insumo.estoque_minimo > 0 and estoque_total <= insumo.estoque_minimo: status_counts['critico'] += 1
            elif insumo.estoque_minimo > 0 and estoque_total <= insumo.estoque_minimo * 1.5: status_counts['atencao'] += 1
            else:
                if saida_media > 0:
                    dias = estoque_total / saida_media
                    if dias <= 30: status_counts['atencao'] += 1
                    elif dias <= 60: status_counts['bom'] += 1
                    else: status_counts['excelente'] += 1
                else: status_counts['excelente'] += 1
        
        consumo_diario_medio_geral = consumo_total_periodo / periodo_dias if periodo_dias > 0 else 0
        
        # --- PREPARAÇÃO DOS DADOS PARA OS FILTROS ---
        todos_setores = Setor.query.order_by(Setor.nome).all()
        setores_options = [{'id': s.id, 'nome': s.nome} for s in todos_setores]
        status_options = ['Todos', 'Excelente', 'Bom', 'Atenção', 'Crítico']
        
        return jsonify({
            'kpis': {'total_itens': total_skus_distintos, 'valor_total': total_valor_estoque, 'consumo_diario': consumo_diario_medio_geral, 'itens_criticos': status_counts['critico']},
            'table_data': {'items': paginated_items, 'page': page, 'total_pages': total_pages, 'has_next': page < total_pages, 'has_prev': page > 1},
            'status_summary': status_counts,
            # --- CORREÇÃO APLICADA AQUI ---
            # Re-adicionando a chave 'filter_options' à resposta
            'filter_options': {
                'setores': setores_options,
                'status': status_options
            }
        })
    except Exception as e:
        print(f"ERRO NO DASHBOARD (MAIN): {e}")
        traceback.print_exc()
        return jsonify({'error': 'Erro ao calcular dados do dashboard'}), 500


@app.route('/api/dashboard/charts', methods=['GET'])
def get_dashboard_chart_data():
    try:
        periodo_dias = request.args.get('periodo', 30, type=int)
        data_limite = datetime.utcnow() - timedelta(days=periodo_dias)
        
        # --- Gráfico de Consumo por Setor (Lógica já estava correta) ---
        setor_consumo_query = db.session.query(
            Setor.nome,
            func.sum(Movimentacao.quantidade * Insumo.valor_unitario)
        ).join(Movimentacao, Setor.id == Movimentacao.setor_id)\
         .join(Insumo, Insumo.id == Movimentacao.insumo_id)\
         .filter(Movimentacao.tipo == 'SAIDA', Movimentacao.data_hora >= data_limite)\
         .group_by(Setor.nome)\
         .order_by(func.sum(Movimentacao.quantidade * Insumo.valor_unitario).desc()).all()
        
        setor_chart_data = {
            "labels": [row[0] for row in setor_consumo_query],
            "data": [row[1] if row[1] is not None else 0 for row in setor_consumo_query]
        }

        # --- LÓGICA CORRIGIDA PARA O GRÁFICO DE TENDÊNCIA ---

        # 1. Faz uma consulta mais simples, sem o CAST na base de dados
        movimentacoes_periodo = Movimentacao.query\
            .join(Insumo, Insumo.id == Movimentacao.insumo_id)\
            .filter(Movimentacao.tipo == 'SAIDA', Movimentacao.data_hora >= data_limite)\
            .order_by(Movimentacao.data_hora).all()

        # 2. Agrupa os resultados por dia em Python
        consumo_por_dia = {}
        for dia, grupo in groupby(movimentacoes_periodo, key=lambda x: x.data_hora.date()):
            consumo_total_dia = sum(mov.quantidade * (mov.insumo.valor_unitario or 0) for mov in grupo)
            consumo_por_dia[dia] = consumo_total_dia
        
        # 3. Preenche os dias sem consumo com zero para um gráfico contínuo
        labels_tendencia, data_tendencia = [], []
        for i in range(periodo_dias - 1, -1, -1):
            dia_iteracao = (datetime.utcnow() - timedelta(days=i)).date()
            labels_tendencia.append(dia_iteracao.strftime('%d/%m'))
            data_tendencia.append(consumo_por_dia.get(dia_iteracao, 0))

        tendencia_chart_data = {"labels": labels_tendencia, "data": data_tendencia}

        # Resposta final com os dados para ambos os gráficos
        return jsonify({
            'setor_chart_data': setor_chart_data,
            'tendencia_chart_data': tendencia_chart_data
        })

    except Exception as e:
        print(f"ERRO AO GERAR DADOS DOS GRÁFICOS: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Erro ao calcular dados dos gráficos'}), 500


@app.route('/api/atualizar-estoque-minimo', methods=['POST'])
def atualizar_estoque_minimo():
    """
    Lê o ficheiro 'dados_mestre_insumos.xlsx' e atualiza o campo
    'estoque_minimo' para cada insumo correspondente.
    """
    try:
        df = pd.read_excel('dados_mestre_insumos.xlsx')
        
        insumos_atualizados = 0
        insumos_nao_encontrados = []

        for index, row in df.iterrows():
            # Limpa o SKU para remover o prefixo "SKU: "
            sku_limpo = str(row['SKU']).replace('SKU:', '').strip()
            
            # Encontra o insumo no banco de dados pelo SKU
            insumo = Insumo.query.filter_by(sku=sku_limpo).first()
            
            if insumo:
                # Se encontrou o insumo, atualiza o estoque mínimo
                estoque_min_val = row.get('estoque minimo')
                if pd.notna(estoque_min_val):
                    insumo.estoque_minimo = int(estoque_min_val)
                    insumos_atualizados += 1
            else:
                insumos_nao_encontrados.append(sku_limpo)

        db.session.commit()
        
        mensagem = f'{insumos_atualizados} insumos tiveram o seu estoque mínimo atualizado com sucesso.'
        if insumos_nao_encontrados:
            mensagem += f" Atenção: os seguintes SKUs não foram encontrados e foram ignorados: {', '.join(insumos_nao_encontrados)}"

        return jsonify({'message': mensagem}), 200

    except FileNotFoundError:
        return jsonify({'error': "O ficheiro 'dados_mestre_insumos.xlsx' não foi encontrado."}), 404
    except Exception as e:
        db.session.rollback()
        print(f"ERRO AO ATUALIZAR ESTOQUE MÍNIMO: {e}")
        traceback.print_exc()
        return jsonify({'error': f"Ocorreu um erro crítico durante a atualização: {e}"}), 500


@app.route('/api/recebimentos', methods=['POST'])
def finalizar_recebimento():
    """
    Recebe os dados da conferência do frontend, regista o recebimento
    e atualiza o estoque para cada item.
    """
    data = request.get_json()
    if not data or not data.get('fornecedor_id') or not data.get('numero_documento') or not data.get('itens'):
        return jsonify({'error': 'Dados incompletos para finalizar o recebimento.'}), 400

    try:
        # 1. Cria o registo principal do Recebimento
        novo_recebimento = Recebimento(
            fornecedor_id=data['fornecedor_id'],
            tipo_documento='NOTA FISCAL', # Pode ser ajustado se necessário
            numero_documento=data['numero_documento'],
            data_recebimento=datetime.strptime(data['data_recebimento'], '%Y-%m-%d').date(),
            valor_total_documento=sum(item['quantidade_conferida'] * item['valor_unitario'] for item in data['itens']),
            usuario = session.get('username', 'Sistema')
        )
        db.session.add(novo_recebimento)
        db.session.flush() # Para obter o ID do recebimento antes de salvar os itens
        

        # 2. Itera sobre cada item recebido
        for item_data in data['itens']:
            # Cria o registo do item recebido, ligado ao recebimento principal
            item_recebido = ItemRecebido(
                recebimento_id=novo_recebimento.id,
                insumo_id=item_data['insumo_id'],
                quantidade_documento=item_data['quantidade_documento'],
                quantidade_conferida=item_data['quantidade_conferida'],
                valor_unitario=item_data['valor_unitario'],
                posicao_destino=item_data['posicao_destino'],
                status_conferencia='CONFERIDO'
            )
            db.session.add(item_recebido)

            # 3. Atualiza o estoque na posição de destino
            posicao_estoque = Estoque.query.filter_by(
                insumo_id=item_data['insumo_id'],
                posicao=item_data['posicao_destino']
            ).first()

            if posicao_estoque:
                # Se a posição já existe para este insumo, soma a quantidade
                posicao_estoque.quantidade += item_data['quantidade_conferida']
            else:
                # Se não existe, cria um novo registo de estoque
                posicao_estoque = Estoque(
                    insumo_id=item_data['insumo_id'],
                    posicao=item_data['posicao_destino'],
                    quantidade=item_data['quantidade_conferida']
                )
                db.session.add(posicao_estoque)
            
            # 4. (Opcional, mas recomendado) Atualiza o valor unitário do insumo com o valor da última compra
            insumo = Insumo.query.get(item_data['insumo_id'])
            if insumo:
                insumo.valor_unitario = item_data['valor_unitario']

        db.session.commit()
        return jsonify({'message': 'Recebimento finalizado e estoque atualizado com sucesso!'}), 201

    except Exception as e:
        db.session.rollback()
        print(f"ERRO AO FINALIZAR RECEBIMENTO: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Ocorreu um erro interno no servidor: {e}'}), 500


@app.route('/api/inventario/buscar', methods=['GET'])
def buscar_item_inventario():
    """Busca um item no estoque por SKU e/ou Posição para o ajuste."""
    sku = request.args.get('sku')
    posicao = request.args.get('posicao')

    if not sku and not posicao:
        return jsonify({'error': 'Forneça um SKU ou uma Posição para a busca.'}), 400

    query = db.session.query(Estoque, Insumo).join(Insumo, Estoque.insumo_id == Insumo.id)
    
    if sku:
        query = query.filter(Insumo.sku.ilike(f'%{sku}%'))
    if posicao:
        query = query.filter(Estoque.posicao.ilike(f'%{posicao}%'))
        
    resultado = query.first()

    if not resultado:
        return jsonify({'error': 'Nenhum item encontrado com os critérios fornecidos.'}), 404

    estoque, insumo = resultado
    
    # Calcula o status do estoque
    status = "OK"
    if insumo.estoque_minimo > 0:
        if estoque.quantidade == 0:
            status = "Sem Estoque"
        elif estoque.quantidade < insumo.estoque_minimo:
            status = "Estoque Baixo"

    return jsonify({
        'estoque_id': estoque.id,
        'sku': insumo.sku,
        'nome': insumo.descricao,
        'posicao': estoque.posicao,
        'categoria': insumo.categoria,
        'quantidade_atual': estoque.quantidade,
        'unidade_medida': insumo.unidade_medida,
        'status': status
    })

@app.route('/api/inventario/ajustar', methods=['POST'])
def ajustar_estoque_inventario():
    """Ajusta a quantidade de um item e regista o histórico."""
    data = request.get_json()
    estoque_id = data.get('estoque_id')
    nova_quantidade = data.get('nova_quantidade')
    usuario = session.get('username', 'Sistema') 
    
    if not all([estoque_id, nova_quantidade is not None]):
         return jsonify({'error': 'Dados incompletos para o ajuste.'}), 400

    try:
        nova_quantidade = float(nova_quantidade)
        if nova_quantidade < 0:
            return jsonify({'error': 'A quantidade não pode ser negativa.'}), 400
            
        item_estoque = Estoque.query.get(estoque_id)
        if not item_estoque:
            return jsonify({'error': 'Item de estoque não encontrado.'}), 404
        
        quantidade_anterior = item_estoque.quantidade
        diferenca = nova_quantidade - quantidade_anterior
        
        # 1. Atualiza a quantidade no estoque
        item_estoque.quantidade = nova_quantidade
        
        # 2. Cria o registo no histórico de ajustes
        novo_ajuste = AjusteInventario(
            estoque_id=estoque_id,
            quantidade_anterior=quantidade_anterior,
            quantidade_nova=nova_quantidade,
            diferenca=diferenca,
            usuario=usuario,
            observacao=f"Ajuste manual de inventário por {usuario}"
        )
        db.session.add(novo_ajuste)
        db.session.commit()
        
        return jsonify({'message': f'Estoque do item {item_estoque.insumo.sku} ajustado para {nova_quantidade} com sucesso!'})

    except Exception as e:
        db.session.rollback()
        print(f"ERRO AO AJUSTAR ESTOQUE: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Ocorreu um erro interno: {e}'}), 500

@app.route('/api/inventario/historico', methods=['GET'])
def get_historico_inventario():
    """Retorna os últimos 100 ajustes de inventário."""
    historico = db.session.query(AjusteInventario, Estoque, Insumo) \
        .join(Estoque, AjusteInventario.estoque_id == Estoque.id) \
        .join(Insumo, Estoque.insumo_id == Insumo.id) \
        .order_by(AjusteInventario.data_ajuste.desc()).limit(100).all()

    resultado = []
    for ajuste, estoque, insumo in historico:
        resultado.append({
            'data': ajuste.data_ajuste.strftime('%d/%m/%Y %H:%M'),
            'sku': insumo.sku,
            'descricao': insumo.descricao,
            'posicao': estoque.posicao,
            'qtd_anterior': ajuste.quantidade_anterior,
            'qtd_nova': ajuste.quantidade_nova,
            'diferenca': ajuste.diferenca,
            'usuario': ajuste.usuario
        })
    return jsonify(resultado)



@app.route('/inventario')
def pagina_inventario():
    """Renderiza a página de ajuste de inventário."""
    return render_template('inventario.html')


@app.route('/api/inventario/historico/exportar', methods=['GET'])
def exportar_historico_inventario():
    """
    Gera um relatório Excel com o histórico de ajustes de inventário.
    VERSÃO CORRIGIDA: Simplificada a lógica de criação do Excel para evitar erros.
    """
    try:
        # 1. Busca todos os registos de ajuste no banco de dados
        historico_query = db.session.query(AjusteInventario, Estoque, Insumo) \
            .join(Estoque, AjusteInventario.estoque_id == Estoque.id) \
            .join(Insumo, Estoque.insumo_id == Insumo.id) \
            .order_by(AjusteInventario.data_ajuste.desc()).all()

        if not historico_query:
            return "Nenhum histórico para exportar", 404

        # 2. Prepara os dados para o DataFrame
        export_data = []
        for ajuste, estoque, insumo in historico_query:
            export_data.append({
                'Data do Ajuste': ajuste.data_ajuste.strftime('%Y-%m-%d %H:%M:%S'),
                'Usuário': ajuste.usuario,
                'SKU': insumo.sku,
                'Descrição do Insumo': insumo.descricao,
                'Posição': estoque.posicao,
                'Quantidade Anterior': ajuste.quantidade_anterior,
                'Quantidade Nova': ajuste.quantidade_nova,
                'Diferença': ajuste.diferenca,
            })
        
        # 3. Cria o DataFrame e o ficheiro Excel em memória
        df = pd.DataFrame(export_data)
        
        output = BytesIO()
        # A criação do Excel agora é mais direta e segura
        df.to_excel(output, index=False, sheet_name='Historico_Ajustes')
        output.seek(0)
        
        # 4. Envia o ficheiro para o utilizador fazer o download
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'historico_ajustes_{datetime.now().strftime("%Y-%m-%d")}.xlsx'
        )

    except Exception as e:
        print(f"Erro ao exportar histórico de inventário: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Ocorreu um erro interno ao gerar o arquivo Excel.'}), 500


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = Usuario.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Utilizador ou palavra-passe inválida.', 'danger')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if Usuario.query.filter_by(username=username).first():
            flash('Este nome de utilizador já existe.', 'warning')
            return redirect(url_for('register'))

        new_user = Usuario(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Utilizador criado com sucesso! Por favor, faça o login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('login'))

@app.route('/api/fornecedores/exportar', methods=['GET'])
def exportar_fornecedores():
    """
    Gera um relatório Excel completo com todos os dados dos fornecedores.
    """
    try:
        fornecedores = Fornecedor.query.order_by(Fornecedor.razao_social).all()
        if not fornecedores:
            return "Nenhum fornecedor para exportar", 404

        # Pega todos os nomes das colunas do modelo dinamicamente
        colunas = [c.name for c in Fornecedor.__table__.columns]
        dados_export = []
        for fornecedor in fornecedores:
            dados_fornecedor = {col: getattr(fornecedor, col) for col in colunas}
            dados_export.append(dados_fornecedor)

        df = pd.DataFrame(dados_export)
        
        output = BytesIO()
        df.to_excel(output, index=False, sheet_name='Fornecedores')
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'relatorio_fornecedores_{datetime.now().strftime("%Y-%m-%d")}.xlsx'
        )
    except Exception as e:
        print(f"Erro ao exportar fornecedores: {e}")
        return "Erro ao gerar o ficheiro.", 500

@app.route('/api/ordens-de-compra/exportar', methods=['GET'])
def exportar_ordens_de_compra():
    """
    Gera um relatório Excel completo com todas as ordens de compra e seus itens.
    """
    try:
        ordens = OrdemDeCompra.query.order_by(OrdemDeCompra.data_compra.desc()).all()
        if not ordens:
            return "Nenhuma ordem de compra para exportar", 404

        dados_export = []
        hoje = datetime.utcnow().date()

        for ordem in ordens:
            # Lógica de status (a mesma da sua tabela)
            status = 'Pendente'
            if ordem.data_chegada_real:
                status = 'Recebido no prazo'
                if ordem.data_entrega_prevista and ordem.data_chegada_real > ordem.data_entrega_prevista:
                    status = f'Recebido com {(ordem.data_chegada_real - ordem.data_entrega_prevista).days} dia(s) de atraso'
            elif ordem.data_entrega_prevista and hoje > ordem.data_entrega_prevista:
                status = f'Atrasado ({(hoje - ordem.data_entrega_prevista).days} dia(s))'

            # Dados da Ordem Principal
            ordem_info = {
                'Numero Ordem': ordem.numero_ordem,
                'Status': status,
                'Fornecedor': ordem.fornecedor.razao_social,
                'Data Compra': ordem.data_compra.strftime('%d/%m/%Y'),
                'Data Entrega Prevista': ordem.data_entrega_prevista.strftime('%d/%m/%Y') if ordem.data_entrega_prevista else '',
                'Data Chegada Real': ordem.data_chegada_real.strftime('%d/%m/%Y') if ordem.data_chegada_real else '',
                'Valor Total': ordem.valor_total,
                'Subtotal': ordem.subtotal,
                'Frete': ordem.frete,
                'Impostos (%)': ordem.impostos_percentual,
                'Solicitado Por': ordem.solicitado_por,
                'Observacoes': ordem.observacoes,
                # Itens da ordem serão adicionados abaixo
                'Item SKU': '',
                'Item Descricao': '',
                'Item Quantidade': '',
                'Item Preco Unitario': ''
            }
            
            if not ordem.itens:
                dados_export.append(ordem_info)
            else:
                # Adiciona uma linha para cada item da ordem
                for i, item in enumerate(ordem.itens):
                    if i == 0:
                        # Primeira linha do item usa a info da ordem
                        item_info = ordem_info.copy()
                    else:
                        # Linhas seguintes ficam em branco nas colunas da ordem
                        item_info = {key: '' for key in ordem_info}

                    item_info['Item SKU'] = item.insumo.sku
                    item_info['Item Descricao'] = item.insumo.descricao
                    item_info['Item Quantidade'] = item.quantidade
                    item_info['Item Preco Unitario'] = item.preco_unitario
                    dados_export.append(item_info)

        df = pd.DataFrame(dados_export)
        
        output = BytesIO()
        df.to_excel(output, index=False, sheet_name='Ordens_de_Compra')
        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'relatorio_ordens_compra_{datetime.now().strftime("%Y-%m-%d")}.xlsx'
        )
    except Exception as e:
        print(f"Erro ao exportar ordens de compra: {e}")
        traceback.print_exc()
        return "Erro ao gerar o ficheiro.", 500


# --- EXECUÇÃO ---
if __name__ == '__main__':
    app.run(debug=True)
