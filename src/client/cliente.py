import json
import pika
import threading
import base64 
import sys
import os
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from client_window import ClienteGUI

# importa o logger
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from logger import create_logger

#conecta com o servidor rabbitmq
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost')
)
channel = connection.channel()

#define o id do cliente
if len(sys.argv) > 1:
    CLIENTE_ID = sys.argv[1]
else:
    print("ERRO: ID do cliente não fornecido na linha de comando.")
    print("Uso: python cliente.py <id_do_cliente>")
    sys.exit(1)

# Criar logger e lista de leiloes para este cliente
logger = create_logger(f'cliente_{CLIENTE_ID}')
leiloes_interessados = set()
leiloes_conhecidos = {}

# Cria o diretório keys se não existir
os.makedirs("../keys", exist_ok=True)
#gera as chaves publica e privada
key = RSA.generate(2048)
private_key = key.export_key()
with open(f"../keys/private_{CLIENTE_ID}.pem", "wb") as f:
    f.write(private_key)

public_key = key.publickey().export_key()
with open(f"../keys/public_{CLIENTE_ID}.pem", "wb") as f:
    f.write(public_key)

#*****************************************************************************#

#configura o canal para receber informações dos leiloes
channel.exchange_declare(exchange='leiloes', exchange_type='fanout')
result = channel.queue_declare(queue='', exclusive=True) #fila temporária do cliente
queue_name = result.method.queue
channel.queue_bind(exchange='leiloes', queue=queue_name)

# Variável global para a GUI
gui = None

#comando de execução após receber a mensagem do ms_leilao
def callback_inicio_leilao(ch, method, properties, body):
    global gui
    msg = body.decode('utf-8')
    data = json.loads(msg)
    
    id_leilao = data.get('id_leilao')
    descricao = data.get('descricao')
    valor_minimo = data.get('valor_minimo', 100.0)
    leiloes_conhecidos[id_leilao] = descricao
    
    logger.info(f"NOVO LEILÃO INICIADO - ID: {id_leilao}, Descrição: {descricao}")
    logger.info(f"Valor mínimo: R$ {valor_minimo:.2f}")
    logger.info(f"Período: {data.get('data_inicio')} até {data.get('data_fim')}")
    
    # Notificar GUI se estiver disponível
    if gui:
        # Armazenar valor mínimo e inicializar cotação atual
        gui.valores_minimos[id_leilao] = valor_minimo
        gui.cotacoes_atuais[id_leilao] = f"R$ {valor_minimo:.2f}"
        gui.novo_leilao(id_leilao, descricao, data.get('data_inicio'), data.get('data_fim'))

#consome as mensagens da fila temporária
channel.basic_consume(queue=queue_name, on_message_callback=callback_inicio_leilao, auto_ack=True)

#*****************************************************************************#

#gera a assinatura digital
message = b'AplicacaoLeilao.2025.2'
key = RSA.import_key(open(f'../keys/private_{CLIENTE_ID}.pem').read())
h = SHA256.new(message)
signature = pkcs1_15.new(key).sign(h)

#*****************************************************************************#

def dar_lance(id_leilao, valor):
    global gui
    
    #verifica se o leilao é conhecido
    if id_leilao not in leiloes_conhecidos:
        logger.error(f"Tentativa de lance em leilão inexistente: {id_leilao}")
        logger.info(f"Leilões disponíveis: {', '.join(leiloes_conhecidos.keys())}")
        if gui:
            gui.log_message(f"❌ Leilão {id_leilao} não existe")
        return
    
    #verifica se o leilao faz parte dos leiloes de interesse do cliente
    if id_leilao not in leiloes_interessados:
        leiloes_interessados.add(id_leilao)
        escutar_leilao(id_leilao)
    
    #não aceita valores nulos ou negativos
    if valor <= 0:
        logger.error(f"Valor de lance inválido: {valor} (deve ser maior que zero)")
        if gui:
            gui.log_message(f"❌ Valor de lance inválido: R$ {valor:.2f}")
        return
    
    # Verificar se o valor é suficiente comparado à cotação atual
    if gui and id_leilao in gui.cotacoes_atuais:
        cotacao_str = gui.cotacoes_atuais[id_leilao]
        # Extrair valor numérico da string "R$ X,XX"
        cotacao_atual = float(cotacao_str.replace('R$ ', '').replace(',', '.'))
        if valor <= cotacao_atual:
            logger.error(f"Valor insuficiente: R$ {valor:.2f} <= R$ {cotacao_atual:.2f}")
            gui.lance_rejeitado(id_leilao, valor, "Valor insuficiente", cotacao_str)
            return
    
    #define a assinatura digital
    assinatura_base64 = base64.b64encode(signature).decode('utf-8')

    #define os dados do lance
    dados_do_lance = {
        "id_usuario": CLIENTE_ID,
        "id_leilao": id_leilao,
        "valor_do_lance": valor,
        "assinatura": assinatura_base64 
    }
    
    try:
        #conecta ao broker
        connection_envio = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost')
        )
        canal_envio = connection_envio.channel()

        #declara a fila de lance_realizado
        canal_envio.queue_declare(queue='lance_realizado')
        mensagem_json = json.dumps(dados_do_lance)
        canal_envio.basic_publish(exchange='',routing_key='lance_realizado',body=mensagem_json.encode('utf-8')        )
        connection_envio.close()

        logger.log_cliente_acao("LANCE_ENVIADO", f"R$ {valor} para leilão {id_leilao} ({leiloes_conhecidos[id_leilao]})")
        
        if gui:
            gui.log_message(f"💰 Lance enviado: R$ {valor:.2f} para leilão {id_leilao}")

    except Exception as e:
        logger.error(f"Erro ao enviar lance: {e}")
        if gui:
            gui.log_message(f"❌ Erro ao enviar lance: {e}")

#*****************************************************************************#

#configura o canal para receber as mensagens de um leilão de interesse do cliente
channel.exchange_declare(exchange='leilao', exchange_type='topic')

def escutar_leilao(id_leilao):
    #função para notificar as mensagens de um leilão de interesse para o cliente
    def callback_notificacao(ch, method, properties, body):
        global gui
        msg = body.decode('utf-8')
        data = json.loads(msg)

        routing_key = method.routing_key
        
        #verifica se a mensagem é um lance
        if routing_key.endswith('.lance'):
            logger.log_lance_recebido(id_leilao, data.get('id_usuario'), data.get('valor_do_lance'))
            
            # Notificar GUI se estiver disponível
            if gui:
                gui.lance_recebido(id_leilao, data.get('id_usuario'), data.get('valor_do_lance'))
        
        #verifica se a mensagem é um fim de leilão
        if routing_key.endswith('.fim'):
            vencedor = data.get('id_vencedor')
            valor_final = data.get('valor_negociado')
            logger.log_leilao_finalizado(id_leilao, vencedor, str(valor_final))
            
            if vencedor == CLIENTE_ID:
                logger.log_cliente_acao("VITÓRIA", f"Venceu leilão {id_leilao} com R$ {valor_final}")
            
            # Notificar GUI sobre fim do leilão
            if gui:
                if data.get('id_vencedor') == CLIENTE_ID:
                    gui.log_message(f"🏆 PARABÉNS! Você venceu o leilão {id_leilao} com R$ {data.get('valor_negociado'):.2f}!")
                else:
                    gui.log_message(f"🏁 Leilão {id_leilao} finalizado. Vencedor: {data.get('id_vencedor')} - R$ {data.get('valor_negociado'):.2f}")

    #função para escutar as mensagens de um leilão de interesse do cliente
    def thread_listener():
        try:
            #cria uma conexão com o broker
            conn_local = pika.BlockingConnection(
                pika.ConnectionParameters('localhost')
            )
            ch_local = conn_local.channel()

            #cria uma fila temporária
            result = ch_local.queue_declare(queue='', exclusive=True)
            qname = result.method.queue
            
            #associa a fila à exchange com as routing keys do leilão
            ch_local.queue_bind(exchange='leilao', queue=qname, routing_key=f"{id_leilao}.lance")
            ch_local.queue_bind(exchange='leilao', queue=qname, routing_key=f"{id_leilao}.fim")
            
            #inicia a consumação de mensagens
            ch_local.basic_consume(queue=qname, on_message_callback=callback_notificacao, auto_ack=True)
            logger.log_cliente_acao("ESCUTANDO_LEILAO", f"Monitorando eventos do leilão {id_leilao}")
            
            ch_local.start_consuming()
        except Exception as e:
            logger.error(f"Erro ao escutar leilão {id_leilao}: {e}")

    #inicia a thread para escutar as mensagens
    t = threading.Thread(target=thread_listener, daemon=True)
    t.start()

#*****************************************************************************#

def iniciar_gui():
    """Inicia a interface gráfica"""
    global gui
    gui = ClienteGUI(CLIENTE_ID, dar_lance, leiloes_conhecidos, leiloes_interessados)
    gui.run()

###########################################################################
# Iniciar RabbitMQ em thread separada
def iniciar_rabbitmq():
    try:
        channel.start_consuming()
    except pika.exceptions.StreamLostError:
        logger.log_conexao_rabbitmq('perdida')
    except KeyboardInterrupt:
        logger.info("Cliente interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
    finally:
        try:
            connection.close()
        except:
            pass

logger.info("Cliente iniciado - aguardando leilões...")
logger.info("Iniciando interface gráfica...")

# Iniciar RabbitMQ em thread separada
thread_rabbitmq = threading.Thread(target=iniciar_rabbitmq, daemon=True)
thread_rabbitmq.start()

# Iniciar GUI na thread principal
iniciar_gui()