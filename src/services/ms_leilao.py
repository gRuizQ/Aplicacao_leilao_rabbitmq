import datetime
import json
import time
import pika
import sys
import os
import random

#importa o logger
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from logger import create_logger

# Criar logger para este microserviço
logger = create_logger('ms_leilao')

# Configurar conexão com RabbitMQ
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

def carregar_leiloes_dicionario():
    try:
        # Caminho baseado na localização do script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        arquivo_path = os.path.join(script_dir, '..', 'dictionary', 'leiloes_data.json')
        with open(arquivo_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data['leiloes']
    except FileNotFoundError:
        logger.error(f"Arquivo de dicionário de leilões não encontrado em: {arquivo_path}")
        return []
    except Exception as e:
        logger.error(f"Erro ao carregar dicionário de leilões: {e}")
        return []

def gerar_leiloes():
    leiloes_dict = carregar_leiloes_dicionario()
    
    # Selecionar 2 leilões aleatórios do dicionário
    leiloes_selecionados = random.sample(leiloes_dict, min(2, len(leiloes_dict)))
    
    leiloes = []
    for i, leilao_data in enumerate(leiloes_selecionados, 1):
        # Define os dados do leilão
        leiloes.append({
            "id": f"leilao_{i:02d}",
            "descricao": leilao_data['descricao'],
            "valor_minimo": leilao_data.get('valor_minimo', 100.0),  # Valor padrão se não existir
            "data_inicio": datetime.datetime.now() + datetime.timedelta(seconds=4 if i == 1 else 59),
            "data_fim": datetime.datetime.now() + datetime.timedelta(minutes=2 if i == 1 else 3),
            "status": "pendente"
        })
    
    return leiloes

leiloes = gerar_leiloes()

#*****************************************************************************#

# Configurar fila leilao_iniciado e leilao_finalizado e exchange fsnout
channel.queue_declare(queue='leilao_iniciado')
channel.exchange_declare(exchange='leiloes', exchange_type='fanout')
channel.queue_declare(queue='leilao_finalizado')

logger.info("MS Leilão iniciado - monitorando leilões...")
logger.info("Leilões configurados:")
for leilao in leiloes:
    logger.info(f"  {leilao['id']}: {leilao['descricao']} - Início: {leilao['data_inicio']} - Fim: {leilao['data_fim']}")

while True:
    for leilao in leiloes:
        horario_atual = datetime.datetime.now()

        if leilao['status'] == 'pendente' and horario_atual >= leilao['data_inicio'] and not horario_atual >= leilao['data_fim']:
            # Para leilões pendentes tornarem ativos
            leilao['status'] = 'ativo'
            logger.log_leilao_iniciado(leilao['id'], leilao['descricao'], leilao['data_inicio'], leilao['data_fim'])
            
            mensagem = {
                "id_leilao": leilao['id'],
                "descricao": leilao['descricao'],
                "valor_minimo": leilao['valor_minimo'],
                "data_inicio": leilao['data_inicio'].isoformat(),
                "data_fim": leilao['data_fim'].isoformat()
            }

            body = json.dumps(mensagem).encode('utf-8')

            # Publicar mensagem na fila leilao_iniciado
            channel.basic_publish(exchange='', routing_key='leilao_iniciado', body=body)
            # Publicar mensagem via exchange leiloes
            channel.basic_publish(exchange='leiloes', routing_key='', body=body)

        elif leilao['status'] == 'ativo' and horario_atual >= leilao['data_fim']: 
            # Para leilões ativos tornarem encerrados
            leilao['status'] = 'encerrado'
            logger.info(f"LEILÃO FINALIZADO - ID: {leilao['id']}")

            mensagem = {
                "id_leilao": leilao['id'],
            }
            
            body = json.dumps(mensagem).encode('utf-8')
            
            # Publicar mensagem na fila leilao_finalizado
            channel.basic_publish(exchange='', routing_key='leilao_finalizado', body=body)

    time.sleep(1)