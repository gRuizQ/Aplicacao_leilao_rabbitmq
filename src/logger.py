import logging
import os
from datetime import datetime

class SystemLogger:
    def __init__(self, service_name, log_level=logging.INFO):
        self.service_name = service_name
        self.log_level = log_level
        
        # Criar diretório de logs se não existir
        self.log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs'))
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Configurar logger
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(log_level)
        
        # Evitar duplicação de handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        # Handler para arquivo
        log_filename = f"{self.service_name}_{datetime.now().strftime('%Y%m%d')}.log"
        log_filepath = os.path.join(self.log_dir, log_filename)
        
        file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
        file_handler.setLevel(self.log_level)
        
        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        
        # Formato das mensagens
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def info(self, message):
        """Log de informação"""
        self.logger.info(message)
    
    def warning(self, message):
        """Log de aviso"""
        self.logger.warning(message)
    
    def error(self, message):
        """Log de erro"""
        self.logger.error(message)
    
    def debug(self, message):
        """Log de debug"""
        self.logger.debug(message)
    
    def critical(self, message):
        """Log crítico"""
        self.logger.critical(message)
    
    def log_leilao_iniciado(self, leilao_id, descricao, data_inicio, data_fim):
        """Log específico para início de leilão"""
        self.info(f"LEILÃO INICIADO - ID: {leilao_id}, Descrição: {descricao}, Início: {data_inicio}, Fim: {data_fim}")
    
    def log_lance_recebido(self, leilao_id, usuario, valor):
        """Log específico para lance recebido"""
        self.info(f"LANCE RECEBIDO - Leilão: {leilao_id}, Usuário: {usuario}, Valor: R${valor}")
    
    def log_lance_validado(self, leilao_id, usuario, valor):
        """Log específico para lance validado"""
        self.info(f"LANCE VALIDADO - Leilão: {leilao_id}, Usuário: {usuario}, Valor: R${valor}")
    
    def log_lance_rejeitado(self, leilao_id, usuario, valor, motivo):
        """Log específico para lance rejeitado"""
        self.warning(f"LANCE REJEITADO - Leilão: {leilao_id}, Usuário: {usuario}, Valor: R${valor}, Motivo: {motivo}")
    
    def log_leilao_finalizado(self, leilao_id, vencedor, valor_final):
        """Log específico para finalização de leilão"""
        self.info(f"LEILÃO FINALIZADO - ID: {leilao_id}, Vencedor: {vencedor}, Valor Final: R${valor_final}")
    
    def log_conexao_rabbitmq(self, status):
        """Log específico para conexão RabbitMQ"""
        if status == 'conectado':
            self.info("Conexão com RabbitMQ estabelecida com sucesso")
        elif status == 'perdida':
            self.error("Conexão com RabbitMQ perdida")
        elif status == 'reconectando':
            self.warning("Tentando reconectar com RabbitMQ")
    
    def log_erro_assinatura(self, usuario, motivo):
        """Log específico para erros de assinatura"""
        self.error(f"ERRO ASSINATURA - Usuário: {usuario}, Motivo: {motivo}")
    
    def log_cliente_acao(self, acao, detalhes=""):
        """Log específico para ações do cliente"""
        self.info(f"AÇÃO CLIENTE - {acao} {detalhes}")

# Função de conveniência para criar loggers
def create_logger(service_name, log_level=logging.INFO):
    """Cria um logger para um serviço específico"""
    return SystemLogger(service_name, log_level)