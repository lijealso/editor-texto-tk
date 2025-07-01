import tkinter as tk
from tkinter import ttk  # para o Combobox
import json  # para permitir usar persistência de dados entre sessões
from tkinter.filedialog import asksaveasfilename, askopenfilename
from tkinter.messagebox import askyesnocancel
# Destaque de sintaxe
from idlelib.colorizer import ColorDelegator, color_config
from idlelib.percolator import Percolator
from idlelib.undo import UndoDelegator

# NOTAS
# -- A janela da aplicação não reduz abaixo de um determinado valor
# para evitar desincronização das linhas da área de texto com
# as linhas do widget de números de linha.
# -- A aplicação começou como editor de texto, por isso a seleção de
# cores. Num editor de código não é habitual haver coloração do texto
# pelo utilizador (eu nunca usei, pelo menos)
# -- O código foi reestruturado por classes quando começou a ter 
# muitas linhas
# -- Optou-se por colocar tudo num ficheiro ao invés de dividir em vários
# ficheiros, só para não se andar a saltar de um lado para outro


class AreaTexto:
    """Gerencia a área de texto principal e números de linha."""

    def __init__(self, parent, familia_fonte="Arial", tamanho_fonte=12):
        self.parent = parent
        self.familia_fonte = familia_fonte
        self.tamanho_fonte = tamanho_fonte
        # variável para controlar se os números de linha estão visíveis
        self.mostrar_numeros_linha = tk.BooleanVar()
        # Definir o número de espaços para a tecla TAB
        self.tab_width = 4
        self._configurar_area_texto()
        self._configurar_realce_sintaxe()

    def _configurar_area_texto(self):
        # Frame para conter o widget de números de linha e o texto
        self.frame = tk.Frame(self.parent)
        self.frame.rowconfigure(0, weight=1)
        # Coluna do texto principal é expansível
        self.frame.columnconfigure(1, weight=1)

        # Frame para conter os números de linha com uma largura fixa
        self.frame_numeros_wrapper = tk.Frame(self.frame, width=50)
        self.frame_numeros_wrapper.grid(row=0, column=0, sticky="ns")
        # Impede que o widget interno redimensione este frame
        self.frame_numeros_wrapper.grid_propagate(False)

        # Widget para números de linha
        self.numeros_linha = tk.Text(
            self.frame_numeros_wrapper,
            width=4, padx=3, takefocus=0, border=0,
            state='disabled', wrap='none',
            font=(self.familia_fonte, self.tamanho_fonte, "bold"),
            bg='lightgray', fg='black'
        )
        self.numeros_linha.pack(fill="both", expand=True)

        # Widget principal de texto
        self.texto = tk.Text(
            self.frame,
            font=(self.familia_fonte, self.tamanho_fonte, "bold"),
            wrap=tk.WORD, fg="black", undo=True
        )
        self.texto.grid(row=0, column=1, sticky="nsew")

        # Adicionar Scrollbar vertical
        self.scrollbar_texto = tk.Scrollbar(
            self.frame, orient=tk.VERTICAL, command=self.texto.yview)
        self.scrollbar_texto.grid(row=0, column=2, sticky="ns")

        self._configurar_scroll_sincronizado()

    def _configurar_realce_sintaxe(self):
        ########## REALCE DE SINTAXE E GESTOR DE UNDO/REDO ##########
        # Configurar o Percolator para interceptar modificações de texto
        self.percolator = Percolator(self.texto)

        # Adicionar o gestor de Undo/Redo
        self.undo = UndoDelegator()
        self.percolator.insertfilter(self.undo)

        # Adicionar o ColorDelegator para syntax highlighting
        self.color = ColorDelegator()
        self.percolator.insertfilter(self.color)

        # Aplicar as cores do tema padrão ao widget de texto
        color_config(self.texto)

        # Substituir algumas cores
        self.texto.tag_configure("COMMENT", foreground="grey")
        self.texto.tag_configure("STRING", foreground="orange")
        self.texto.tag_configure("DEFINITION", foreground="green")
        self.texto.tag_configure("BUILTIN", foreground="green")

    def _configurar_scroll_sincronizado(self):
        """Configura a sincronização de scroll entre o texto principal e os números de linha"""
        def _sincronizar(*args):
            # Atualiza a scrollbar
            self.scrollbar_texto.set(*args)
            # Sincroniza os números de linha, se visíveis
            if self.mostrar_numeros_linha.get():
                self.numeros_linha.yview_moveto(args[0])

        self.texto.config(yscrollcommand=_sincronizar)

    def atualizar_numeros_linha(self):
        """Atualiza os números de linha"""
        # Não mostrar números de linha
        if not self.mostrar_numeros_linha.get():
            return

        # Guardar a posição atual do scroll para restaurar depois
        scroll_pos = self.texto.yview()

        try:
            # O índice 'end-1c' dá a posição do último caractere
            linhas = int(self.texto.index(f"{tk.END}-1c").split('.')[0])
        except tk.TclError:
            linhas = 1  # Se o widget estiver vazio, ainda temos 1 linha

        # Gerar os números de linha
        # Numa string, cada número separado por uma quebra de linha
        # Da linha 1 até "linhas" (+ 1, porque 2º valor de range não é inclusivo)
        numeros = '\n'.join(str(i) for i in range(1, linhas + 1))

        # Atualizar o widget de números de linha e restaurar o scroll
        self.numeros_linha.config(state='normal')
        self.numeros_linha.delete(1.0, tk.END)
        self.numeros_linha.insert(1.0, numeros)
        self.numeros_linha.config(state='disabled')
        self.numeros_linha.yview_moveto(scroll_pos[0])

    def alternar_numeros_linha(self):
        """Mostra ou oculta os números de linha baseado no estado do checkbox"""
        if self.mostrar_numeros_linha.get():
            self.numeros_linha.pack(fill="both", expand=True)
            self.atualizar_numeros_linha()
        else:
            self.numeros_linha.pack_forget()


class PainelFerramentas:
    """Gerencia o painel de ferramentas lateral."""
    
    def __init__(self, parent, area_texto, gestor_ficheiros):
        self.parent = parent
        self.area_texto = area_texto
        self.gestor_ficheiros = gestor_ficheiros
        self._configurar_painel()

    def _configurar_painel(self):
        self.frame = tk.Frame(self.parent, relief=tk.RAISED, bd=2)

        # dicionário para criar os botões
        botoes = {
            "Novo": self.gestor_ficheiros.novo_ficheiro,
            "Abrir": self.gestor_ficheiros.abrir_ficheiro,
            "Gravar": self.gestor_ficheiros.gravar_ficheiro,
            "Gravar Como": self.gestor_ficheiros.gravar_como,
            # Não implementado
            "Verificar Sintaxe": self._verificar_sintaxe 
        }

        # criação dos botões utilizando o dicionário
        for i, (texto_botao, comando) in enumerate(botoes.items()):
            botao = tk.Button(self.frame, text=texto_botao, command=comando)
            botao.grid(row=i, column=0, padx=5, pady=5, sticky="ew")

        # Checkbox para mostrar/ocultar números de linha
        checkbox_numeros = tk.Checkbutton(
            self.frame, text="Números de Linha",
            variable=self.area_texto.mostrar_numeros_linha,
            command=self.area_texto.alternar_numeros_linha
        )
        checkbox_numeros.grid(row=len(botoes), column=0,
                              padx=5, pady=5, sticky="w")

        # Controles de formatação
        self._configurar_controles_formatacao(len(botoes) + 1)

    def _configurar_controles_formatacao(self, linha_inicial):
        # Label e seleção de cor do texto
        label_cor = tk.Label(self.frame, text="Cor do Texto:")
        label_cor.grid(row=linha_inicial, column=0,
                       padx=5, pady=(10, 0), sticky="w")

        # Frame para os botões de cor
        frame_cores = tk.Frame(self.frame)
        frame_cores.grid(row=linha_inicial + 1, column=0,
                         padx=5, pady=5, sticky="w")

        # Dicionário com cores disponíveis
        self.cores_disponiveis = {
            "Preto": "black", "Azul": "blue", "Vermelho": "red",
            "Verde": "green", "Roxo": "purple", "Laranja": "orange"
        }

        # Pre-configurar tags de cor para o texto
        for cor in self.cores_disponiveis.values():
            self.area_texto.texto.tag_config(f"color_{cor}", foreground=cor)

        # Criar botões para cada cor
        for i, (nome_cor, valor_cor) in enumerate(self.cores_disponiveis.items()):
            botao_cor = tk.Button(
                frame_cores, text=nome_cor, bg=valor_cor, width=8,
                fg="white" if valor_cor in [
                    "black", "blue", "purple"] else "black",
                command=lambda cor=valor_cor: self._alterar_cor_texto(cor)
            )
            # Organizar em 2 colunas
            botao_cor.grid(row=i // 2, column=i % 2, padx=2, pady=2)

        # Label paraa o tamanho da fonte
        label_tamanho_fonte = tk.Label(self.frame, text="Tamanho da Fonte:")
        label_tamanho_fonte.grid(
            row=linha_inicial + 2, column=0, padx=5, pady=(10, 0), sticky="w")

        # Variável para controlar o tamanho da fonte
        self.tamanho_fonte_var = tk.IntVar(value=12)

        # Slider para alterar tamanho da fonte
        slider_tamanho_fonte = tk.Scale(
            # Intervalo de valores e orientação vertical
            self.frame, from_=10, to=16, orient=tk.HORIZONTAL,
            variable=self.tamanho_fonte_var,
            # Função que é chamada quando se acciona o slider
            command=self._alterar_tamanho_fonte
        )
        
        slider_tamanho_fonte.grid(
            row=linha_inicial + 3, column=0, padx=5, pady=5, sticky="ew")

        # Label e combobox para a família da fonte
        label_familia_fonte = tk.Label(self.frame, text="Família da Fonte:")
        label_familia_fonte.grid(
            row=linha_inicial + 4, column=0, padx=5, pady=(10, 0), sticky="w")

        # Opções de família de fonte disponíveis
        familias_fonte_disponiveis = [
            "Arial", "Times New Roman", "Courier New"]

        self.combobox_familia_fonte = ttk.Combobox(
            self.frame, values=familias_fonte_disponiveis,
            state="readonly", width=15  # impede edição manual
        )
        self.combobox_familia_fonte.set(self.area_texto.familia_fonte)
        self.combobox_familia_fonte.bind(
            "<<ComboboxSelected>>", self._alterar_familia_fonte)
        self.combobox_familia_fonte.grid(
            row=linha_inicial + 5, column=0, padx=5, pady=5, sticky="ew")

    def _alterar_cor_texto(self, nova_cor):
        """Altera a cor do texto selecionado no editor."""
        try:
            # Obter os índices do texto selecionado
            start, end = self.area_texto.texto.tag_ranges(tk.SEL)
        except ValueError:
            return  # Nenhum texto selecionado

        # Remover tags de cor existentes da seleção
        for cor in self.cores_disponiveis.values():
            self.area_texto.texto.tag_remove(f"color_{cor}", start, end)

        # Adicionar a nova tag de cor à seleção
        if nova_cor != "black":
            self.area_texto.texto.tag_add(f"color_{nova_cor}", start, end)

    def _alterar_tamanho_fonte(self, novo_tamanho_str):
        """Altera o tamanho da fonte no editor e nos números de linha."""
        novo_tamanho = int(novo_tamanho_str)
        nova_fonte = (self.area_texto.familia_fonte, novo_tamanho, "bold")

        self.area_texto.texto.config(font=nova_fonte)
        self.area_texto.numeros_linha.config(font=nova_fonte)
        self.area_texto.atualizar_numeros_linha()

    def _alterar_familia_fonte(self, event=None):
        """Altera a família da fonte no editor e nos números de linha."""
        nova_familia = self.combobox_familia_fonte.get()
        self.area_texto.familia_fonte = nova_familia

        nova_fonte = (nova_familia, self.tamanho_fonte_var.get(), "bold")
        self.area_texto.texto.config(font=nova_fonte)
        self.area_texto.numeros_linha.config(font=nova_fonte)
        self.area_texto.atualizar_numeros_linha()

    # Não implementado
    # Verificação de error no código
    def _verificar_sintaxe(self):
        if hasattr(self.parent, 'verificar_sintaxe'):
            self.parent.verificar_sintaxe()


class PainelPesquisa:
    """Gerencia o painel de pesquisa."""

    def __init__(self, parent, area_texto):
        self.parent = parent
        self.area_texto = area_texto
        # Lista para armazenar informações dos resultados
        self.resultados_pesquisa = []
        self._configurar_painel()

    def _configurar_painel(self):
        # Frame para o painel de pesquisa
        self.frame = tk.Frame(self.parent, relief=tk.RAISED, bd=2)

        # Campo de pesquisa e botões
        label_termo = tk.Label(self.frame, text="Pesquisar:")
        label_termo.grid(row=0, column=0, padx=(5, 2), pady=3, sticky="w")

        self.entry_pesquisa = tk.Entry(self.frame, width=8)
        self.entry_pesquisa.grid(row=0, column=1, padx=2, pady=3)
        # tecla Enter chama a função de pesquisa de texto
        self.entry_pesquisa.bind("<Return>", self.pesquisar_texto)

        # Carregando no botão chama a mesma função
        btn_pesquisar = tk.Button(
            self.frame, text="Pesquisar", command=self.pesquisar_texto)
        btn_pesquisar.grid(row=0, column=2, padx=2, pady=3)

        btn_limpar = tk.Button(self.frame, text="Limpar",
                               command=self.limpar_pesquisa)
        btn_limpar.grid(row=0, column=3, padx=(2, 5), pady=3)

        # Listbox com resultados
        frame_listbox = tk.Frame(self.frame)
        frame_listbox.grid(row=1, column=0, columnspan=4,
                           padx=5, pady=(3, 5), sticky="ew")

        self.listbox_resultados = tk.Listbox(frame_listbox, height=5, width=80)
        self.listbox_resultados.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar para a listbox
        scrollbar_listbox = tk.Scrollbar(
            frame_listbox, orient=tk.VERTICAL, command=self.listbox_resultados.yview)
        scrollbar_listbox.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox_resultados.config(yscrollcommand=scrollbar_listbox.set)

        # Bind para duplo clique na listbox
        self.listbox_resultados.bind(
            # Duplo clique no botão esquerdo do rato
            "<Double-Button-1>", self.ir_para_resultado)

        # Configurar expansão do frame de pesquisa
        self.frame.columnconfigure(1, weight=0)

    def pesquisar_texto(self, event=None):
        """Pesquisa o texto no editor e mostra os resultados na listbox."""
        # Obtem o termo de pesquisa da caixa de texto
        termo_pesquisa = self.entry_pesquisa.get().strip()
        # Se nenhuma palavra foi digitada, sai da função
        if not termo_pesquisa:
            return
        # Se alguma palavra foi digitada, prosseegue:
        # Limpar resultados anteriores
        self.listbox_resultados.delete(0, tk.END)
        self.resultados_pesquisa.clear()

        # Remove realces anteriores
        self.area_texto.texto.tag_remove("search_highlight", "1.0", tk.END)

        # Obtem todo o conteúdo do texto
        conteudo = self.area_texto.texto.get("1.0", tk.END)
        # Divide o conteúdo por linhas, o que vai permitir mostrar os números de linha no resultado
        linhas = conteudo.split('\n')

        # Pesquisar em cada linha
        for num_linha, linha in enumerate(linhas, 1):
            # Se o termo da pesquisa for encontrado na linha
            if termo_pesquisa.lower() in linha.lower():
                # Define as "coordenadas" desse termo no texto
                pos = linha.lower().find(termo_pesquisa.lower())
                linha_pos = f"{num_linha}.{pos}"
                fim_pos = f"{num_linha}.{pos + len(termo_pesquisa)}"

                # Adicionar realce ao texto pesquisado
                # Adiciona um tag específica (search_highlight)
                self.area_texto.texto.tag_add(
                    "search_highlight", linha_pos, fim_pos)

                # Preparar texto para mostrar na listbox (limitado a 60 caracteres)
                contexto = linha.strip()
                if len(contexto) > 60:
                    contexto = contexto[:60] + "..."

                # String com o resultado
                resultado_texto = f"Linha {num_linha}: {contexto}"
                # Adiciona resultado à listbox
                self.listbox_resultados.insert(tk.END, resultado_texto)

                # Armazena informações de cada resultado num dicionário
                # 'posicao' obtida da linha E coluna (inicio da palavra pesquisada)
                # 'fim_posicao' permite definir o fim do realce
                self.resultados_pesquisa.append({
                    'linha': num_linha, 'coluna': pos,
                    'posicao': linha_pos, 'fim_posicao': fim_pos
                })

        # Configurar cor do highlight
        self.area_texto.texto.tag_config(
            "search_highlight", background="yellow", foreground="black")

        # Mostra os resultados
        if len(self.resultados_pesquisa) == 0:
            # Se o dicionãrio está vazio, mostra uma mensagem indicativa
            self.listbox_resultados.insert(
                tk.END, "Nenhum resultado encontrado")
        # Se o dicionário tiver dados:
        elif self.resultados_pesquisa:
            # Obtem o primeiro resultado
            primeiro_resultado = self.resultados_pesquisa[0]
            # e faz o scroll para a posição desse resultado
            self.area_texto.texto.see(primeiro_resultado['posicao'])

    def limpar_pesquisa(self):
        """Limpa os resultados da pesquisa e remove os highlights."""
        # Limpar campos de pesquisa e resultados
        self.entry_pesquisa.delete(0, tk.END)
        self.listbox_resultados.delete(0, tk.END)
        self.resultados_pesquisa.clear()
        # Remove os realces
        self.area_texto.texto.tag_remove("search_highlight", "1.0", tk.END)

    def ir_para_resultado(self, event=None):
        """Vai para o resultado selecionado na listbox."""
        selecao = self.listbox_resultados.curselection()
        # Se nada estiver selecionado, sai da função
        if not selecao or selecao[0] >= len(self.resultados_pesquisa):
            return
        #
        resultado = self.resultados_pesquisa[selecao[0]]

        # Move o scroll para tornar o resultado visível
        self.area_texto.texto.see(resultado['posicao'])
        # Move o cursor para o resultado
        self.area_texto.texto.mark_set(tk.INSERT, resultado['posicao'])

        # Remove seleções
        self.area_texto.texto.tag_remove(tk.SEL, "1.0", tk.END)
        # Adiciona seleções, com base nos resultados
        self.area_texto.texto.tag_add(
            tk.SEL, resultado['posicao'], resultado['fim_posicao'])

        # Focar no texto
        self.area_texto.texto.focus_set()

    def focar_pesquisa(self, event=None):
        """Foca no campo de pesquisa quando Ctrl+F é pressionado."""
        self.entry_pesquisa.focus_set()
        self.entry_pesquisa.select_range(0, tk.END)


class GestorFicheiros:
    """Gerencia operações de ficheiro."""

    def __init__(self, area_texto, callback_titulo):
        self.area_texto = area_texto
        self.callback_titulo = callback_titulo
        # A variável para armazenar o caminho do ficheiro aberto
        self.caminho_ficheiro = None
        # inicia a variável como "texto sem modificações"
        self.modificado = False

    def novo_ficheiro(self, event=None):
        """ Cria um novo documento de texto. """
        # Se existem mofificações não gravadas
        if not self._verificar_modificacoes():
            # sai da função
            return
        # Se não existem modificações não gravadas prossegue:
        # Apaga o texto todo
        self.area_texto.texto.delete(1.0, tk.END)
        # Desassocia o caminho do ficheiro: Documento "Sem título"
        self.caminho_ficheiro = None
        # Não existem modificações não gravadas
        self.modificado = False
        # Altera a flag (de modificações) interna
        self.area_texto.texto.edit_modified(False)
        # Atualiza o título da janela: "Sem título"
        self.callback_titulo()
        # Atualiza os números de linha para texto vazio (1 linha)
        self.area_texto.atualizar_numeros_linha()

    def abrir_ficheiro(self, event=None):
        """ Abre um um documento de texto """
        # Mesmo que na função acima
        if not self._verificar_modificacoes():
            return
        # Abre uma caixa de diálogo para escolher o ficheiro a abrir
        caminho = askopenfilename(
            # Tipos de ficheiro possíveis de selecionar
            filetypes=[
                ("Ficheiro de Texto Formatado", "*.rtxt"),
                ("Ficheiros de texto", "*.txt"),
                ("Todos os Ficheiros", "*.*")
            ]
        )
        # SE None ou falso saí da função
        if not caminho:
            return
        # Lê o conteúdo do ficheiro
        try:
            with open(caminho, "r", encoding='utf-8') as ficheiro:
                if caminho.endswith('.rtxt'):
                    # Tenta carregar como JSON (formato formatado)
                    dados = json.load(ficheiro)
                    conteudo = dados.get('content', '')
                    tags = dados.get('tags', [])
                else:
                    # Carrega como texto simples
                    conteudo = ficheiro.read()
                    tags = []
        except (IOError, json.JSONDecodeError) as erro:
            tk.messagebox.showerror(
                "Erro ao Abrir", f"Não foi possível abrir o ficheiro:\n{erro}")
            return

        # Limpa a área de texto e insere o novo conteúdo
        self.area_texto.texto.delete(1.0, tk.END)
        self.area_texto.texto.insert(tk.END, conteudo)

        # Aplicar as tags de formatação guardadas
        for tag in tags:
            if 'name' in tag and 'start' in tag and 'end' in tag:
                self.area_texto.texto.tag_add(
                    tag['name'], tag['start'], tag['end'])

        # Atualiza o estado do editor
        self.caminho_ficheiro = caminho
        self.modificado = False
        self.area_texto.texto.edit_modified(False)
        self.callback_titulo()
        self.area_texto.atualizar_numeros_linha()

    def _coletar_tags_formatacao(self):
        """Coleta apenas as tags de formatação aplicadas pelo usuário (cores)."""
        # Lista de dicionários. Cada dicionário corresponde a uma tag (com a respetiva informação, abaixo)
        tags = []
        # As tags de cor são prefixadas com "color_"
        tag_names = [t for t in self.area_texto.texto.tag_names()
                     if t.startswith("color_")]

        for tag_name in tag_names:
            ranges = self.area_texto.texto.tag_ranges(tag_name)
            for i in range(0, len(ranges), 2):
                # Acrescenta cada dicionário com a informação de cada tag
                tags.append({
                    # Nome da tag, ex: color_{cor}
                    "name": tag_name,
                    # Início e fim da formatação
                    "start": str(ranges[i]),
                    "end": str(ranges[i+1])
                })
        return tags

    def gravar_ficheiro(self, event=None):
        # Se não tiver caminho (ficheiro novo) redireciona para a função gravar_como
        if not self.caminho_ficheiro:
            return self.gravar_como()
        # Se tiver caminho, grava normalmente
        try:  # Se tudo correr bem executa o trecho centro do try
            # Se for um ficheiro .txt, grava como texto simples para compatibilidade
            if self.caminho_ficheiro.endswith(".txt"):
                # "end-1c" exclui o último caracter ('\n') que é adicionado automaticamente pelo Tkinter
                conteudo = self.area_texto.texto.get(1.0, "end-1c")
                # Grava sem as tags
                with open(self.caminho_ficheiro, "w", encoding='utf-8') as fich:
                    fich.write(conteudo)
            else:  # Para .rtxt ou outros, guarda com formatação (JSON)
                # Define o conteudo e as tags para colocar no ficheiro gravado
                conteudo = self.area_texto.texto.get(1.0, "end-1c")
                # Usa a função para coletar apenas tags de formatação do utilizador
                tags = self._coletar_tags_formatacao()
                # Define o dicionário com os dados para gravar
                dados_para_salvar = {"content": conteudo, "tags": tags}
                with open(self.caminho_ficheiro, "w", encoding='utf-8') as fich:
                    # usa o método dump para guardar o objecto num ficheiro
                    json.dump(dados_para_salvar, fich, indent=4)
        # Caso algo corra mal, é levantada uma excepção e mostrada uma mensagem de erro
        except Exception as erro:
            tk.messagebox.showerror(
                "Erro ao Gravar", f"Não foi possível gravar o ficheiro:\n{erro}")
            return False

        # reposição de variáveis/estado
        self.modificado = False
        self.area_texto.texto.edit_modified(False)
        self.callback_titulo()
        return True

    def gravar_como(self, event=None):
        caminho = asksaveasfilename(
            # Mudar a extensão padrão para o nosso novo formato
            defaultextension=".rtxt",
            # Adicionar o novo tipo de ficheiro e colocá-lo como primeira opção
            filetypes=[
                ("Ficheiro de Texto Formatado", "*.rtxt"),
                ("Ficheiros de texto", "*.txt"),
                ("Todos os Ficheiros", "*.*")
            ]
        )
        if not caminho:
            return False

        self.caminho_ficheiro = caminho
        # A lógica de qual formato usar já está dentro de gravar_ficheiro()
        return self.gravar_ficheiro()

    def _verificar_modificacoes(self):
        # verifica se o texto foi modificado desde a última vez que ele foi salvo
        if not self.modificado:
            return True
        # se foi modificado, mostra uma mensagem perguntando se quer guardar as alterações
        resposta = askyesnocancel(
            title="Guardar Ficheiro?",
            message="O ficheiro atual tem alterações não guardadas. Quer guardar as alterações?"
        )

        if resposta is None:  # Cancelar
            return False
        elif resposta:  # Sim (Guardar)
            return self.gravar_ficheiro()
        else:  # Não (Não guardar)
            return True


class EditorTexto:
    """Classe principal que coordena todos os componentes do editor."""

    def __init__(self, master):
        """
        Inicializa o editor de texto com arquitetura modular.
        Configura a janela principal e cria todos os componentes.    
        Args:
            master: Janela principal do Tkinter
        """
        self.master = master
        self.master.title("Sem Título - PyCharmoso, editor de código Python")
        self._configurar_layout()
        self._criar_componentes()
        self._configurar_bindings()

    def _configurar_layout(self):
        self.master.rowconfigure(0, minsize=300, weight=1)
        # Linha para o painel de pesquisa
        self.master.rowconfigure(1, minsize=180, weight=0)
        self.master.columnconfigure(
            0, minsize=200, weight=0)  # Coluna dos botões
        self.master.columnconfigure(
            1, minsize=600, weight=1)  # Coluna do texto

    def _criar_componentes(self):
        """ Cria e configura todos os componentes do editor de texto """
        # Área de texto
        self.area_texto = AreaTexto(self.master)
        self.area_texto.frame.grid(row=0, column=1, sticky="nsew")

        # Gestor de ficheiros
        self.gestor_ficheiros = GestorFicheiros(
            self.area_texto, self._atualizar_titulo)

        # Painel de ferramentas
        self.painel_ferramentas = PainelFerramentas(
            self.master, self.area_texto, self.gestor_ficheiros)
        self.painel_ferramentas.frame.grid(row=0, column=0, sticky="ns")

        # Painel de pesquisa
        self.painel_pesquisa = PainelPesquisa(self.master, self.area_texto)
        self.painel_pesquisa.frame.grid(
            row=1, column=1, sticky="ew", padx=5, pady=(5, 10))

    def _configurar_bindings(self):
        """ Configura bindings para eventos específicos """
        # funciona como um listener, que é chamado sempre que ocorre uma mudança na caixa de texto
        self.area_texto.texto.bind("<<Modified>>", self._ao_modificar)
        # Interceptar a tecla Tab para inserir espaços
        self.area_texto.texto.bind("<Tab>", self._on_tab_key)

        # Atalhos de teclado
        self.master.bind("<Control-n>", self.gestor_ficheiros.novo_ficheiro)
        self.master.bind("<Control-c>", self.gestor_ficheiros.gravar_como)
        self.master.bind("<Control-f>", self.painel_pesquisa.focar_pesquisa)

        # Ligar os eventos de Undo/Redo do widget de texto ao nosso gestor de undo
        self.area_texto.texto.bind("<<Undo>>", self.area_texto.undo.undo_event)
        self.area_texto.texto.bind("<<Redo>>", self.area_texto.undo.redo_event)

        # WM_DELETE_WINDOW é um evento que é acionado quando o usuário tenta fechar a janela
        self.master.protocol("WM_DELETE_WINDOW", self._ao_fechar)

    def _ao_modificar(self, event=None):
        """ Trata a modificação do texto e atualiza a flag de modificação. """
        # verifica se a flag de modificação está ativada (== True)
        if self.area_texto.texto.edit_modified():
            # se sim, altera a variável da aplicação para True
            self.gestor_ficheiros.modificado = True
            # e atualiza o título da janela com um asterisco (*) no início do título
            self._atualizar_titulo()
            # Atualiza os números de linha, pois o conteúdo mudou
            self.area_texto.atualizar_numeros_linha()
            # Faz o reset da flag interna de modificado
            self.area_texto.texto.edit_modified(False)

    def _on_tab_key(self, event=None):
        """Insere um número predefinido de espaços em vez de um caractere de tabulação."""
        self.area_texto.texto.insert(
            tk.INSERT, " " * self.area_texto.tab_width)
        # Impede o comportamento padrão da tecla Tab
        return "break"

    def _atualizar_titulo(self):
        """ Atualiza o título da janela com base no caminho do ficheiro e nas modificações. """
        # obtém o nome do ficheiro a partir do caminho completo
        # se não houver caminho definido, usa "Sem Título"
        nome_ficheiro = (self.gestor_ficheiros.caminho_ficheiro.split("/")[-1]
                         if self.gestor_ficheiros.caminho_ficheiro else "Sem Título")
        # mostra um asterisco (*) no início do título da janela se o texto tiver sido modificado
        modificado_str = "*" if self.gestor_ficheiros.modificado else ""
        self.master.title(
            f"{modificado_str}{nome_ficheiro} - PyCharmoso, editor de código Python")

    def _ao_fechar(self):
        # TODO
        """  """
        # verifica se há modificações não guardadas antes de fechar a janela
        if self.gestor_ficheiros._verificar_modificacoes():
            # Limpar o percolator para evitar erros ao fechar
            self.area_texto.percolator.close()
            # se não há modificações não guardadas, fecha a janela
            self.master.destroy()


def main():
    janela = tk.Tk()
    # Impede redimensionamento horizontal abaixo de 500px
    janela.minsize(1300, 800)
    app = EditorTexto(janela)
    janela.mainloop()


if __name__ == "__main__":
    main()
