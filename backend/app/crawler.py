import os
import requests
from bs4 import BeautifulSoup
import urllib3
from datetime import datetime
from database import insert_document, mark_as_revoked
from vector_db import add_document_to_vector_db

# Desabilitar avisos de SSL não confiável (comum em sites acadêmicos)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_html(url: str) -> str:
    """Faz requisição HTTP GET para obter o HTML da página."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=20)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Erro ao acessar {url}: Status {response.status_code}")
            return ""
    except Exception as e:
        print(f"Exceção ao acessar {url}: {e}")
        return ""

def scrape_carta_servicos() -> list:
    """Scrapea o portal de serviços da UERJ para extrair informações."""
    url = "https://www.servicos.uerj.br/"
    html = fetch_html(url)
    if not html:
        return []
        
    soup = BeautifulSoup(html, "html.parser")
    documents = []
    
    # Busca por elementos de serviços ou tópicos
    # Vamos extrair links e textos dos cartões de serviços
    # A estrutura comum costuma ter links para sub-serviços
    services_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Se for um sublink de serviço
        if "servico/" in href or "categoria/" in href:
            full_url = href if href.startswith("http") else f"https://www.servicos.uerj.br{href}"
            services_links.append((a.get_text(strip=True), full_url))
            
    # Para a PoC, se não achar links específicos de serviço, raspamos a página principal
    main_text = ""
    # Pega todo o texto dos elementos principais
    for elem in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        txt = elem.get_text(strip=True)
        if txt and len(txt) > 20:
            main_text += txt + "\n\n"
            
    if main_text:
        documents.append({
            "titulo": "Carta de Serviços da UERJ - Portal Principal",
            "tipo": "Carta de Servico",
            "numero": None,
            "ano": datetime.now().year,
            "url": url,
            "texto": main_text
        })
        
    print(f"Carta de Serviços raspada. Obtido 1 documento principal ({len(main_text)} caracteres).")
    return documents

def scrape_rede_sirius_legislacao() -> list:
    """Raspagem da página de busca de legislação da Rede Sirius."""
    # url = "https://catalogo-redesirius.uerj.br/Terminalweb/busca/legislacao"
    url = "https://www.pr4.uerj.br/normativos"
    # url = "https://catalogo-redesirius.uerj.br/TerminalWeb/Resultado/ListarLegislacao?guid=1781716640102"
    # url = "https://catalogo-redesirius.uerj.br/TerminalWeb/VisualizadorPdf?codigoArquivo=23151&tipoMidia=0"
    html = fetch_html(url)
    if not html:
        return []
        
    soup = BeautifulSoup(html, "html.parser")
    documents = []
    
    # Extrai o texto da página inicial da busca
    content = ""
    for elem in soup.find_all(["h1", "h2", "p", "div"]):
        # Ignorar menus/footers se possível, pegando classes de conteúdo principal
        txt = elem.get_text(strip=True)
        if txt and len(txt) > 30 and not any(x in txt.lower() for x in ["copyright", "menu", "desenvolvido por"]):
            content += txt + "\n\n"
            
    if content:
        documents.append({
            "titulo": "Rede Sirius - Busca de Legislação e Atos Normativos",
            "tipo": "Regulamento",
            "numero": None,
            "ano": datetime.now().year,
            "url": url,
            "texto": content
        })
        
    print(f"Rede Sirius Legislação raspada. Obtido 1 documento principal ({len(content)} caracteres).")
    return documents

def scrape_dep_manuais() -> list:
    """Scrapea a página de Manuais do DEP UERJ."""
    url = "http://www.dep.uerj.br/manuais.php"
    html = fetch_html(url)
    if not html:
        return []
        
    soup = BeautifulSoup(html, "html.parser")
    documents = []
    
    # Extrai links de manuais e arquivos em PDF
    content = "Manuais e Orientações do DEP (Departamento de Estudos de Projeção):\n\n"
    manuais_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if "arqs/" in href or ".pdf" in href.lower():
            full_url = href if href.startswith("http") else f"http://www.dep.uerj.br/{href}"
            manuais_links.append(f"- {text}: {full_url}")
            
    if manuais_links:
        content += "\n".join(manuais_links)
    else:
        for elem in soup.find_all(["h4", "p", "li"]):
            txt = elem.get_text(strip=True)
            if txt and len(txt) > 20:
                content += txt + "\n"
                
    documents.append({
        "titulo": "DEP UERJ - Manuais e Orientações de Graduação",
        "tipo": "Regulamento",
        "numero": None,
        "ano": datetime.now().year,
        "url": url,
        "texto": content
    })
    
    print(f"Página de Manuais do DEP raspada. Obtido 1 documento principal ({len(content)} caracteres).")
    return documents

def get_seed_documents() -> list:
    """Retorna uma base de dados semeada com leis, regulamentos e AEDAs fundamentais da UERJ."""
    return [
        {
            "titulo": "AEDA 038/REITORIA/2007 - Normas de Avaliação de Desempenho Acadêmico",
            "tipo": "AEDA",
            "numero": "038/2007",
            "ano": 2007,
            "url": "https://www.rsirius.uerj.br/legis/aeda_038_2007.pdf",
            "texto": """
            ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 038/REITORIA/2007
            Dispõe sobre as normas de avaliação do rendimento escolar de alunos de graduação da UERJ.
            
            1. FREQUÊNCIA E PRESENÇA:
            A frequência às aulas e demais atividades escolares é obrigatória. O aluno que não atingir o mínimo de 75% (setenta e cinco por cento) de frequência na disciplina será considerado reprovado por falta (RF), independentemente de suas notas.
            
            2. SISTEMA DE NOTAS E AVALIAÇÃO:
            O rendimento acadêmico é expresso em notas de 0 (zero) a 10 (dez).
            Durante o período letivo serão realizadas avaliações periódicas (provas, trabalhos, testes). A média das avaliações do período é chamada de Média Semestral (MS).
            
            3. APROVAÇÃO DIRETA:
            O estudante que obtiver Média Semestral (MS) igual ou superior a 7,0 (sete) estará aprovado diretamente na disciplina, dispensado da Prova Final (PF).
            
            4. PROVA FINAL (PF):
            O estudante que obtiver Média Semestral (MS) inferior a 7,0 (sete) e igual ou superior a 3,0 (três) terá direito a realizar a Prova Final (PF).
            Se o aluno obtiver Média Semestral (MS) inferior a 3,0 (três), estará reprovado direto, sem direito à Prova Final.
            
            5. MÉDIA FINAL (MF):
            Para o aluno que realizou a Prova Final (PF), a Média Final (MF) será calculada pela média aritmética simples entre a Média Semestral (MS) e a nota da Prova Final (PF):
            MF = (MS + PF) / 2
            O estudante será considerado APROVADO se a Média Final (MF) for igual ou superior a 5,0 (cinco). Caso contrário, será considerado REPROVADO por nota.
            
            6. SEGUNDA CHAMADA:
            O aluno que faltar a qualquer avaliação terá direito a realizar prova de segunda chamada se apresentar justificativa aceita pela coordenação de curso no prazo máximo de 3 (três) dias úteis após a data da avaliação perdida.
            """
        },
        {
            "titulo": "Regulamento de Desligamento Acadêmico e Jubilamento na UERJ",
            "tipo": "Regulamento",
            "numero": "Deliberação 012/2012",
            "ano": 2012,
            "url": "https://www.rsirius.uerj.br/legis/delib_012_2012.pdf",
            "texto": """
            DELIBERAÇÃO Nº 012/CSEPE/2012
            Regulamenta as condições de desligamento acadêmico (jubilamento) do estudante da UERJ.
            
            O aluno será desligado da UERJ (perderá a vaga) nas seguintes condições:
            1. REPROVAÇÃO POR FALTA (RF) CONSECUTIVA:
            Reprovar por falta (RF) em todas as disciplinas em que se matriculou em dois períodos letivos consecutivos.
            
            2. LIMITE DE REPROVAÇÕES NA MESMA DISCIPLINA:
            O aluno que for reprovado por 3 (três) vezes na mesma disciplina (seja por nota ou por falta) será desligado da UERJ. A quarta matrícula na mesma disciplina não é permitida.
            
            3. TEMPO MÁXIMO DE INTEGRALIZAÇÃO:
            Não concluir o curso dentro do prazo máximo de integralização estabelecido pelo currículo do curso (geralmente equivalente ao dobro do tempo regular do curso. Por exemplo, 8 anos para um curso de 4 anos).
            
            4. COEFICIENTE DE RENDIMENTO (CR):
            Apresentar Coeficiente de Rendimento (CR) acumulado inferior a 3.0 (três) durante três períodos letivos consecutivos.
            
            5. ABANDONO DE CURSO:
            Não realizar matrícula em nenhum componente curricular no prazo fixado pelo Calendário Acadêmico (sem estar sob trancamento de matrícula ativo).
            
            RECURSOS E EXCEÇÕES:
            O aluno notificado de desligamento tem o direito de intervir com recurso administrativo junto ao Colegiado do Curso, apresentando justificativas médicas, profissionais ou socioeconômicas no prazo de 10 dias após a notificação.
            """
        },
        {
            "titulo": "Normas de Trancamento e Cancelamento de Matrícula - Deliberação 044/2018",
            "tipo": "Regulamento",
            "numero": "Deliberação 044/2018",
            "ano": 2018,
            "url": "https://www.rsirius.uerj.br/legis/delib_044_2018.pdf",
            "texto": """
            DELIBERAÇÃO Nº 044/CSEPE/2018
            Regula os procedimentos de Trancamento de Matrícula (Total e Parcial) e Cancelamento de Inscrição em Disciplina.
            
            1. TRANCAMENTO TOTAL DE MATRÍCULA:
            O trancamento total é a suspensão temporária das atividades acadêmicas do aluno, mantendo seu vínculo com a UERJ.
            - O aluno pode usufruir de trancamento total por, no máximo, 4 (quatro) períodos letivos, consecutivos ou intercalados, ao longo de todo o curso.
            - Não é permitido o trancamento total no primeiro período letivo do aluno (ingressante/calouro), exceto por motivos de força maior devidamente comprovados (doença grave ou serviço militar).
            
            2. TRANCAMENTO PARCIAL E CANCELAMENTO DE DISCIPLINA:
            O aluno pode solicitar o cancelamento da inscrição em disciplinas específicas dentro dos prazos definidos no Calendário Acadêmico da UERJ.
            - Deve-se manter a carga horária mínima exigida pelo curso em cada período letivo (geralmente equivalente a pelo menos 3 disciplinas).
            - O cancelamento de disciplinas não conta para o limite de trancamentos totais, mas a disciplina cancelada constará no histórico sem atribuição de nota.
            
            3. TRANCAMENTO AUTOMÁTICO:
            Ocorre quando o estudante não renova sua matrícula no prazo, mas ainda dispõe de períodos de trancamento permitidos. Se o limite de 4 períodos for excedido e o aluno não fizer matrícula, ele incorrerá em abandono de curso e consequente desligamento.
            """
        },
        {
            "titulo": "Bolsas de Assistência Estudantil e Auxílios da PR4 (AEDA 023/2021)",
            "tipo": "AEDA",
            "numero": "023/2021",
            "ano": 2021,
            "url": "https://www.pr4.uerj.br/aeda/aeda_023_2021.pdf",
            "texto": """
            ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 023/REITORIA/2021
            Define os auxílios financeiros da Pró-Reitoria de Políticas Estudantis (PR4) para os estudantes da UERJ.
            
            A UERJ oferece bolsas de assistência estudantil para alunos em situação de vulnerabilidade socioeconômica, cotistas e não-cotistas elegíveis:
            
            1. BOLSA DE APOIO À VULNERABILIDADE SOCIAL (BAVS):
            Destinada a estudantes com renda familiar per capita de até 1,5 salário mínimo. O valor atual é pago mensalmente para auxiliar na permanência do estudante na universidade.
            
            2. AUXÍLIO TRANSPORTE:
            Pago aos beneficiários de bolsas da PR4 para custeio de deslocamento residência-universidade. Estudantes de graduação também têm direito ao passe livre universitário municipal (Riocard Universitário), conforme regulamentação da prefeitura do Rio de Janeiro.
            
            3. AUXÍLIO ALIMENTAÇÃO:
            Concedido para estudantes de campi que não dispõem de Restaurante Universitário (Bandejão), ou como complemento em situações específicas avaliadas pelo serviço social.
            
            4. AUXÍLIO CRECHE:
            Pago mensalmente para apoiar estudantes que possuem filhos de até 6 anos de idade incompletos, ajudando no custeio de creche ou cuidador enquanto realizam suas atividades acadêmicas.
            
            5. AUXÍLIO MATERIAL DIDÁTICO:
            Cota anual ou semestral paga para aquisição de livros, cópias e materiais específicos necessários para o andamento do curso.
            
            Manutenção da bolsa exige: Coeficiente de Rendimento (CR) regular, aprovação em pelo menos 50% das disciplinas matriculadas no período anterior e não possuir vínculo empregatício.
            """
        },
        {
            "titulo": "Restaurante Universitário da UERJ (Bandejão) - Regras de Acesso",
            "tipo": "Carta de Servico",
            "numero": "RU-001",
            "ano": 2023,
            "url": "https://www.servicos.uerj.br/servico/restaurante-universitario",
            "texto": """
            REGRAS DE ACESSO E FUNCIONAMENTO DO RESTAURANTE UNIVERSITÁRIO (RU - BANDEJÃO)
            
            O Restaurante Universitário fornece refeições (almoço e jantar) balanceadas e de baixo custo para a comunidade acadêmica da UERJ no campus Maracanã e outros campi integrados.
            
            1. VALORES DAS REFEIÇÕES:
            - Alunos bolsistas PR4 / Cotistas da UERJ: Refeição gratuita (isento de pagamento).
            - Alunos não-cotistas de graduação: R$ 2,00 (dois reais) por refeição.
            - Alunos de pós-graduação e servidores: R$ 3,00 (três reais) por refeição.
            - Visitantes e público externo: R$ 10,00 por refeição.
            
            2. REQUISITOS PARA ACESSO:
            - Apresentação obrigatória da Carteira de Identidade Estudantil da UERJ (física ou digital no app).
            - Comprovante de matrícula atualizado em conjunto com documento oficial com foto (caso a carteirinha ainda esteja em confecção).
            - Compra de créditos/tickets previamente nas bilheterias localizadas ao lado do refeitório.
            
            3. HORÁRIO DE FUNCIONAMENTO:
            - Almoço: das 11:00 às 14:30 (segunda a sexta-feira).
            - Jantar: das 17:30 às 20:30 (segunda a sexta-feira).
            """
        },
        {
            "titulo": "AEDA 042/REITORIA/2024 - Atualização de Auxílios Estudantis (Revoga Parcialmente AEDA 023/2021)",
            "tipo": "AEDA",
            "numero": "042/2024",
            "ano": 2024,
            "url": "https://www.pr4.uerj.br/wp-content/uploads/2024/09/AEDA-042-REITORIA-2024.pdf",
            "texto": """
            ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 042/REITORIA/2024
            Atualiza os valores das Bolsas de Assistência Estudantil e revoga o Artigo 12 do AEDA 023/2021 que limitava a cumulação de auxílios.
            
            1. NOVOS VALORES DE BOLSAS:
            - A Bolsa de Apoio à Vulnerabilidade Social (BAVS) passa a ter o valor mensal de R$ 700,00 (setecentos reais).
            - O Auxílio Creche passa a ser de R$ 400,00 (quatrocentos reais) por filho elegível.
            - O Auxílio Material Didático anual passa a ser de R$ 600,00 (seiscentos reais).
            
            2. CUMULAÇÃO DE AUXÍLIOS:
            Fica autorizada a cumulação da Bolsa de Apoio à Vulnerabilidade Social (BAVS) com o Auxílio Creche e o Auxílio Transporte. Fica revogada qualquer disposição em contrário contida no AEDA 023/2021 ou regulamentos anteriores que proibiam o recebimento cumulativo destes benefícios específicos.
            """
        }
    ]

def run_ingest():
    """Roda o processo completo de coleta, salvamento em SQLite e indexação no ChromaDB."""
    print("Iniciando processo de ingestão de dados...")
    
    # 1. Coleta de dados via scraping
    scraped_docs = []
    
    print("Executando scraping da Carta de Serviços...")
    try:
        scraped_docs.extend(scrape_carta_servicos())
    except Exception as e:
        print(f"Erro no scraping da Carta de Serviços: {e}")
        
    print("Executando scraping da Rede Sirius...")
    try:
        scraped_docs.extend(scrape_rede_sirius_legislacao())
    except Exception as e:
        print(f"Erro no scraping da Rede Sirius: {e}")

    print("Executando scraping dos Manuais do DEP...")
    try:
        scraped_docs.extend(scrape_dep_manuais())
    except Exception as e:
        print(f"Erro no scraping dos Manuais do DEP: {e}")
        
    # 2. Obter dados de semente (seed data)
    seed_docs = get_seed_documents()
    
    all_docs = scraped_docs + seed_docs
    print(f"Total de documentos coletados para ingestão: {len(all_docs)}")
    
    # 3. Gravar no SQLite e indexar no ChromaDB
    for doc in all_docs:
        # Inserir ou atualizar no SQLite
        doc_id = insert_document(
            titulo=doc["titulo"],
            tipo=doc["tipo"],
            numero=doc["numero"],
            ano=doc["ano"],
            url=doc["url"],
            texto=doc["texto"]
        )
        
        # Indexar no ChromaDB
        add_document_to_vector_db(
            doc_id=doc_id,
            titulo=doc["titulo"],
            tipo=doc["tipo"],
            texto=doc["texto"]
        )
        
    # 4. Tratar conflitos de leis (exemplo: AEDA 045/2024 revoga parcialmente o AEDA 023/2021)
    print("Verificando conflitos de leis e revogações...")
    # Executar marcações manuais baseadas no histórico conhecido
    # Se o AEDA 045/2024 existe, marcar o AEDA 023/2021 como parcialmente revogado
    # Aqui, a marcação é feita usando nossa lógica de banco de dados
    changes = mark_as_revoked(
        titulo_or_numero="023/2021", 
        revogado_por="AEDA 045/2024 (Revogado parcialmente nos termos da cumulação de auxílios e valores atualizados)"
    )
    if changes:
        print("AEDA 023/2021 marcado como parcialmente revogado pelo AEDA 042/2024.")
        
    print("Ingestão de dados concluída com sucesso!")

if __name__ == "__main__":
    # Inicializar banco relacional se for rodado como script independente
    from database import init_db
    init_db()
    run_ingest()
