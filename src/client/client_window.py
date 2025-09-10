import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
from datetime import datetime

class ClienteGUI:
    def __init__(self, cliente_id, dar_lance_callback, leiloes_conhecidos, leiloes_interessados):
        self.cliente_id = cliente_id
        self.dar_lance_callback = dar_lance_callback
        self.leiloes_conhecidos = leiloes_conhecidos
        self.leiloes_interessados = leiloes_interessados
        
        # Dicionário para armazenar cotações atuais dos leilões
        self.cotacoes_atuais = {}
        # Dicionário para armazenar valores mínimos dos leilões
        self.valores_minimos = {}
        
        # Queue para comunicação thread-safe
        self.message_queue = queue.Queue()
        
        # Criar janela principal
        self.root = tk.Tk()
        self.root.title(f"Sistema de Leilões - {cliente_id}")
        self.root.geometry("1100x350")
        self.root.configure(bg='#f0f0f0')
        
        self.setup_ui()
        
        # Timer para verificar mensagens
        self.check_messages()
        
    def setup_ui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Título
        title_label = tk.Label(main_frame, text=f"Cliente: {self.cliente_id}", 
                              font=('Arial', 16, 'bold'), bg='#f0f0f0')
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Frame para dar lance
        lance_frame = ttk.LabelFrame(main_frame, text="Dar Lance", padding="10")
        lance_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        lance_frame.columnconfigure(1, weight=1)
        
        # ID do leilão
        ttk.Label(lance_frame, text="ID do Leilão:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.leilao_id_var = tk.StringVar()
        self.leilao_combo = ttk.Combobox(lance_frame, textvariable=self.leilao_id_var, width=20)
        self.leilao_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Valor do lance
        ttk.Label(lance_frame, text="Valor (R$):").grid(row=0, column=2, sticky=tk.W, padx=(10, 10))
        self.valor_var = tk.StringVar()
        valor_entry = ttk.Entry(lance_frame, textvariable=self.valor_var, width=15)
        valor_entry.grid(row=0, column=3, sticky=tk.W, padx=(0, 10))
        
        # Botão dar lance
        lance_btn = ttk.Button(lance_frame, text="Dar Lance", command=self.dar_lance)
        lance_btn.grid(row=0, column=4, padx=(10, 0))
        
        # Frame para leilões
        leiloes_frame = ttk.LabelFrame(main_frame, text="Leilões Ativos", padding="10")
        leiloes_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        leiloes_frame.columnconfigure(0, weight=1)
        leiloes_frame.rowconfigure(0, weight=1)
        
        # Lista de leilões
        self.leiloes_tree = ttk.Treeview(leiloes_frame, columns=('descricao', 'cotacao', 'status'), show='tree headings')
        self.leiloes_tree.heading('#0', text='ID')
        self.leiloes_tree.heading('descricao', text='Descrição')
        self.leiloes_tree.heading('cotacao', text='Cotação Atual')
        self.leiloes_tree.heading('status', text='Status')
        self.leiloes_tree.column('#0', width=80)
        self.leiloes_tree.column('descricao', width=180)
        self.leiloes_tree.column('cotacao', width=120)
        self.leiloes_tree.column('status', width=100)
        
        # Scrollbar para a lista
        leiloes_scroll = ttk.Scrollbar(leiloes_frame, orient=tk.VERTICAL, command=self.leiloes_tree.yview)
        self.leiloes_tree.configure(yscrollcommand=leiloes_scroll.set)
        
        self.leiloes_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        leiloes_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Frame para log de mensagens
        log_frame = ttk.LabelFrame(main_frame, text="Log de Atividades", padding="10")
        log_frame.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Área de texto para log
        self.log_text = scrolledtext.ScrolledText(log_frame, width=40, height=20, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Botões de ação
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(buttons_frame, text="Atualizar Leilões", command=self.atualizar_leiloes).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Limpar Log", command=self.limpar_log).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Sair", command=self.sair).pack(side=tk.RIGHT)
        
        # Atualizar interface inicial
        self.atualizar_leiloes()
        self.log_message(f"Cliente {self.cliente_id} iniciado - aguardando leilões...")
        
    def dar_lance(self):
        leilao_id = self.leilao_id_var.get().strip()
        valor_str = self.valor_var.get().strip()
        
        if not leilao_id:
            messagebox.showerror("Erro", "Selecione um leilão!")
            return
            
        if not valor_str:
            messagebox.showerror("Erro", "Digite um valor!")
            return
            
        try:
            valor = float(valor_str)
            if valor <= 0:
                messagebox.showerror("Erro", "Valor deve ser positivo!")
                return
                
            # Chamar função de dar lance em thread separada
            threading.Thread(target=self._dar_lance_thread, args=(leilao_id, valor), daemon=True).start()
            
            # Limpar campos
            self.valor_var.set("")
            
            self.log_message(f"Lance de R$ {valor:.2f} enviado para {leilao_id}")
            
        except ValueError:
            messagebox.showerror("Erro", "Valor deve ser um número!")
            
    def _dar_lance_thread(self, leilao_id, valor):
        try:
            self.dar_lance_callback(leilao_id, valor)
        except Exception as e:
            self.message_queue.put(("error", f"Erro ao dar lance: {e}"))
            
    def atualizar_leiloes(self):
        # Limpar lista atual
        for item in self.leiloes_tree.get_children():
            self.leiloes_tree.delete(item)
            
        # Adicionar leilões conhecidos
        leiloes_list = []
        for leilao_id, descricao in self.leiloes_conhecidos.items():
            status = "Escutando" if leilao_id in self.leiloes_interessados else "Ativo"
            cotacao = self.cotacoes_atuais.get(leilao_id, "R$ 0,00")
            self.leiloes_tree.insert('', 'end', text=leilao_id, values=(descricao, cotacao, status))
            leiloes_list.append(leilao_id)
            
        # Atualizar combobox
        self.leilao_combo['values'] = leiloes_list
        
    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def limpar_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def sair(self):
        if messagebox.askokcancel("Sair", "Deseja realmente sair do sistema?"):
            self.root.quit()
            
    def novo_leilao(self, leilao_id, descricao, data_inicio, data_fim):
        """Método para ser chamado quando um novo leilão é detectado"""
        self.message_queue.put(("novo_leilao", {
            'id': leilao_id,
            'descricao': descricao,
            'data_inicio': data_inicio,
            'data_fim': data_fim
        }))
        
    def lance_recebido(self, leilao_id, usuario, valor):
        """Método para ser chamado quando um lance é recebido"""
        self.message_queue.put(("lance", {
            'leilao_id': leilao_id,
            'usuario': usuario,
            'valor': valor
        }))
        
    def lance_rejeitado(self, leilao_id, valor_rejeitado, motivo, valor_atual=None):
        """Método para ser chamado quando um lance é rejeitado"""
        self.message_queue.put(("lance_rejeitado", {
            'leilao_id': leilao_id,
            'valor_rejeitado': valor_rejeitado,
            'motivo': motivo,
            'valor_atual': valor_atual
        }))
        
    def check_messages(self):
        """Verifica mensagens na queue e atualiza a interface"""
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()
                
                if msg_type == "novo_leilao":
                    self.log_message(f"🆕 NOVO LEILÃO: {data['id']} - {data['descricao']}")
                    self.atualizar_leiloes()
                    
                elif msg_type == "lance":
                    # Atualizar cotação atual
                    self.cotacoes_atuais[data['leilao_id']] = f"R$ {data['valor']:.2f}"
                    self.log_message(f"💰 Lance: {data['usuario']} - R$ {data['valor']:.2f} ({data['leilao_id']})")
                    # Atualizar interface para mostrar nova cotação
                    self.atualizar_leiloes()
                    
                elif msg_type == "lance_rejeitado":
                    if data['motivo'] == "Valor insuficiente" and data['valor_atual']:
                        self.log_message(f"❌ Lance rejeitado: R$ {data['valor_rejeitado']:.2f} é insuficiente. Cotação atual: {data['valor_atual']}")
                    else:
                        self.log_message(f"❌ Lance rejeitado: {data['motivo']}")
                    
                elif msg_type == "error":
                    self.log_message(f"❌ {data}")
                    messagebox.showerror("Erro", data)
                    
        except queue.Empty:
            pass
            
        # Reagendar verificação
        self.root.after(100, self.check_messages)
        
    def run(self):
        """Inicia a interface gráfica"""
        self.root.mainloop()