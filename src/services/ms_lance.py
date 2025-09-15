import json
import pika
import base64
import sys
import os
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA

# importa o logger
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from logger import create_logger

# Criar logger para este microserviço
logger = create_logger('ms_lance')

# Configurar conexão com RabbitMQ
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost'))
channel = connection.channel()


ultimos_lances = {}

#*****************************************************************************#

# Declarar filas 
channel.queue_declare(queue='lance_realizado')
channel.queue_declare(queue='lance_validado')
channel.queue_declare(queue='leilao_finalizado')
channel.queue_declare(queue='leilao_vencedor')

# Verifica o lance e publica na fila lance_validado
def callback_lance(ch, method, properties, body):
    msg = body.decode('utf-8')
    data = json.loads(msg)
    id_leilao = data.get('id_leilao')
    id_usuario = data.get('id_usuario')
    valor_do_lance = data.get('valor_do_lance')
    assinatura_base64 = data.get('assinatura')

    if not all([id_leilao, id_usuario, valor_do_lance, assinatura_base64]):
        logger.error("Mensagem de lance incompleta recebida")
        return

    try:
        # Verifica assinatura com a chave pública do usuário
        with open(f'../keys/public_{id_usuario}.pem', 'rb') as f:
            key = RSA.import_key(f.read())

        msg_original = b'AplicacaoLeilao.2025.2'
        h = SHA256.new(msg_original)

        assinatura_bytes = base64.b64decode(assinatura_base64)

        pkcs1_15.new(key).verify(h, assinatura_bytes)
        
        logger.info(f"Assinatura do usuário {id_usuario} VÁLIDA")
        logger.log_lance_recebido(id_leilao, id_usuario, valor_do_lance)

    except (ValueError, TypeError):
        logger.log_erro_assinatura(id_usuario, "Assinatura inválida")
        logger.log_lance_rejeitado(id_leilao, id_usuario, valor_do_lance, "Assinatura inválida")
        return
    except FileNotFoundError:
        logger.log_erro_assinatura(id_usuario, f"Chave pública não encontrada")
        logger.log_lance_rejeitado(id_leilao, id_usuario, valor_do_lance, "Chave pública não encontrada")
        return
    except Exception as e:
        logger.error(f"Erro inesperado ao processar lance: {e}")
        return

    # Verifica se o lance é maior que o último lance
    ultimo_lance_valor = (ultimos_lances.get(id_leilao, {})).get('valor_do_lance', 0)
    if valor_do_lance <= ultimo_lance_valor:
        logger.info(f"Valor Insuficiente... Cotação atual do leilão: R${ultimo_lance_valor:.2f}")
        logger.log_lance_rejeitado(id_leilao, id_usuario, valor_do_lance, "Valor insuficiente")
        return

    ultimos_lances[id_leilao] = {
        'valor_do_lance': valor_do_lance,
        'id_usuario': id_usuario
    }

    logger.log_lance_validado(id_leilao, id_usuario, valor_do_lance)

    mensagem = {
        "id_leilao": id_leilao,
        "id_usuario": id_usuario,
        "valor_do_lance": valor_do_lance
    }

    body_e = json.dumps(mensagem).encode('utf-8')

    # Publica na fila lance_validado após o lance ser validado
    channel.basic_publish(exchange='', routing_key='lance_validado', body=body_e)


# Consumir mensagens da fila lance_realizado
channel.basic_consume(queue='lance_realizado', on_message_callback=callback_lance, auto_ack=True)

#*****************************************************************************#

# Declara exchange leiloes
channel.exchange_declare(exchange='leiloes', exchange_type='fanout')
result = channel.queue_declare(queue='', exclusive=True) # Declara uma fila temporária
queue_name = result.method.queue
channel.queue_bind(exchange='leiloes', queue=queue_name)

def callback_inicio_leilao(ch, method, properties, body):
    logger.info(f"Novo leilão detectado: {body.decode()}")


# Consumir mensagens da fila temporária provida pela exchange 'leiloes'
channel.basic_consume(queue=queue_name, on_message_callback=callback_inicio_leilao, auto_ack=True)

#*****************************************************************************#

# Declaração de filas leilao_finalizado e leilao vencedor
channel.queue_declare(queue='leilao_finalizado')
channel.queue_declare(queue='leilao_vencedor')

def callback_leilao_finalizado(ch, method, properties, body):
    msg = body.decode('utf-8')
    data = json.loads(msg)
    id_leilao = data.get('id_leilao')
    logger.info(f"Processando finalização do leilão {id_leilao}")

    if not id_leilao:
        logger.error("ID do leilão não encontrado na mensagem de finalização")
        return
    
    # Verifica se houve lances válidos
    if id_leilao not in ultimos_lances:
        logger.warning(f"Leilão {id_leilao} finalizado sem lances válidos")
        mensagem = {
            "id_leilao": id_leilao,
            "id_usuario":  "ninguem",
            "valor_do_lance": 0.00,
        }
    else:
        mensagem = {
            "id_leilao": id_leilao,
            "id_usuario": ultimos_lances[id_leilao]['id_usuario'],
            "valor_do_lance": ultimos_lances[id_leilao]['valor_do_lance']
        }
    
    body_vencedor = json.dumps(mensagem).encode('utf-8')

    # Publica na fila leilao_vencedor
    channel.basic_publish(exchange='', routing_key='leilao_vencedor', body=body_vencedor)  
    
# Consumir mensagens da fila leilao_finalizado
channel.basic_consume(queue='leilao_finalizado', on_message_callback=callback_leilao_finalizado, auto_ack=True)

#*****************************************************************************#

channel.start_consuming()