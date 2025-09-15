import json
import pika
import sys
import os

# importa o logger
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from logger import create_logger

# Criar logger para este microserviço
logger = create_logger('ms_notificacao')

# Conexão com o RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

#*****************************************************************************#
# Declara exchange leilao
channel.exchange_declare(exchange='leilao', exchange_type='topic')

# Função para notificar lances validados publicando na exchange leilao .lance
def callback_lance_validado(ch, method, properties, body):
    logger.info("Lance validado recebido para notificação")

    msg = body.decode('utf-8')
    data = json.loads(msg)
    id_leilao = data.get('id_leilao')
    id_usuario = data.get('id_usuario')
    valor_do_lance = data.get('valor_do_lance')

    # Declara a fila para o leilão
    channel.queue_declare(queue=id_leilao)

    msg = {
        "id_leilao": id_leilao,
        "id_usuario": id_usuario,
        "valor_do_lance": valor_do_lance
    }

    body_envio = json.dumps(msg).encode('utf-8')
    # Publica o leilão na exchange .lance
    channel.basic_publish( exchange='leilao', routing_key=f"{id_leilao}.lance", body=body_envio)

# Declara a fila lance_validado
channel.queue_declare(queue='lance_validado')
# Consumir mensagens da fila lance_validado
channel.basic_consume(queue='lance_validado', on_message_callback=callback_lance_validado, auto_ack=True)

#*****************************************************************************#

# Função para notificar leilao vencedor publicando na exchange leilao .fim
def callback_leilao_vencedor(ch, method, properties, body):
    logger.info("Processando resultado do leilão")

    msg = body.decode('utf-8')
    data = json.loads(msg)
    id_leilao = data.get('id_leilao')
    id_usuario = data.get('id_usuario')
    valor_do_lance = data.get('valor_do_lance')

    logger.log_leilao_finalizado(id_leilao, id_usuario, f"{valor_do_lance:.2f}")

    # Declara a fila para o leilão
    channel.queue_declare(queue=id_leilao)
    msg = {
        "id_leilao": id_leilao,
        "id_vencedor": id_usuario, 
        "valor_negociado": valor_do_lance
    }

    body_envio = json.dumps(msg).encode('utf-8')
    # Publica o leilão na exchange leilao .fim
    channel.basic_publish( exchange='leilao', routing_key=f"{id_leilao}.fim", body=body_envio)

# Declara a fila leilao_vencedor
channel.queue_declare(queue='leilao_vencedor')
# Consumir mensagens da fila leilao_vencedor
channel.basic_consume(queue='leilao_vencedor', on_message_callback=callback_leilao_vencedor, auto_ack=True)



#*****************************************************************************#

channel.start_consuming()