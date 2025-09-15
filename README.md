# Sistema de Leilões Distribuído
Sistema de leilões em tempo real usando RabbitMQ e criptografia RSA.

## Funcionalidades
- Leilões em tempo real
- Autenticação com assinatura digital RSA
- Interface gráfica para clientes
- Microserviços distribuídos

## Como Executar o Sistema

### Pré-requisitos
- RabbitMQ rodando em `localhost:15672`
- Python com bibliotecas: `pika`, `pycryptodome` e `tkinter`

### 1. Iniciar Clientes (em terminais separados)

```bash
# Terminal 1 - Cliente 1 (Interface Gráfica)
cd src/client
python cliente.py cliente_01

# Terminal 2 - Cliente 2
cd src/client
python cliente.py cliente_02
```

### 2. Iniciar os Microserviços (em terminais separados)

```bash
# Terminal 3 - Microserviço de Leilão
cd src/services
python ms_leilao.py

# Terminal 4 - Microserviço de Lance
cd src/services
python ms_lance.py

# Terminal 5 - Microserviço de Notificação
cd src/services
python ms_notificacao.py
```

## Como Usar a Interface Gráfica do Cliente

Quando o cliente iniciar, uma janela gráfica será aberta com as seguintes funcionalidades:

### Seção "Dar Lance"
- **ID do Leilão**: Selecione um leilão ativo no dropdown
- **Valor (R$)**: Digite o valor do seu lance
- **Botão "Dar Lance"**: Envia o lance com assinatura digital RSA

### Seção "Leilões Ativos"
- Lista todos os leilões disponíveis com ID, descrição e status
- Mostra se você está "Escutando" ou se o leilão está "Ativo"

### Seção "Log de Atividades"
- Exibe em tempo real:
  - Novos leilões detectados
  - Lances recebidos de outros participantes
  - Vitórias em leilões
  - Finalizações de leilões
  - Erros do sistema

### Botões de Controle
- **Atualizar Leilões**: Recarrega a lista de leilões
- **Limpar Log**: Limpa o histórico de atividades
- **Sair**: Encerra o cliente de forma segura

## Segurança

- Cada cliente gera automaticamente um par de chaves RSA
- Todos os lances são assinados digitalmente
- O sistema valida as assinaturas antes de aceitar lances

## Exemplo de Uso

1. Inicie todos os microserviços
2. Inicie dois clientes
3. Aguarde um leilão começar (você receberá notificação)
4. No cliente 1: digite `1` → `leilao_01` → `150.00`
5. No cliente 2: digite `1` → `leilao_01` → `200.00`
6. Acompanhe as notificações em tempo real!