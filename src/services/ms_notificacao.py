import json
import pika
import sys
import os

# Adicionar o diretório pai ao path para importar o logger
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from logger import create_logger

# Criar logger para este microserviço
logger = create_logger('ms_notificacao')

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

#*****************************************************************************#

channel.exchange_declare(exchange='leilao', exchange_type='topic')

def callback_lance_validado(ch, method, properties, body):
    logger.info("Lance validado recebido para notificação")

    msg = body.decode('utf-8')
    data = json.loads(msg)
    id_leilao = data.get('id_leilao')
    id_usuario = data.get('id_usuario')
    valor_do_lance = data.get('valor_do_lance')
    channel.queue_declare(queue=id_leilao)

    msg = {
        "id_leilao": id_leilao,
        "id_usuario": id_usuario,
        "valor_do_lance": valor_do_lance
    }
    body_envio = json.dumps(msg).encode('utf-8')
    channel.basic_publish( exchange='leilao', routing_key=f"{id_leilao}.lance", body=body_envio)


channel.queue_declare(queue='lance_validado')
channel.basic_consume(queue='lance_validado', on_message_callback=callback_lance_validado, auto_ack=True)



#*****************************************************************************#

def callback_leilao_vencedor(ch, method, properties, body):
    logger.info("Processando resultado do leilão")

    msg = body.decode('utf-8')
    data = json.loads(msg)
    id_leilao = data.get('id_leilao')
    id_usuario = data.get('id_usuario')
    valor_do_lance = data.get('valor_do_lance')

    logger.log_leilao_finalizado(id_leilao, id_usuario, f"{valor_do_lance:.2f}")
    channel.queue_declare(queue=id_leilao)
    msg = {
        "id_leilao": id_leilao,
        "id_vencedor": id_usuario, 
        "valor_negociado": valor_do_lance
    }
    body_envio = json.dumps(msg).encode('utf-8')
    channel.basic_publish( exchange='leilao', routing_key=f"{id_leilao}.fim", body=body_envio)

channel.queue_declare(queue='leilao_vencedor')
channel.basic_consume(queue='leilao_vencedor', on_message_callback=callback_leilao_vencedor, auto_ack=True)



#*****************************************************************************#

channel.start_consuming()