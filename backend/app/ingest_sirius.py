"""
Script de ingestão dos AEDAs de 2026 extraídos do catálogo da Rede Sirius UERJ.
Fonte: https://catalogo-redesirius.uerj.br/TerminalWeb/Resultado/ListarLegislacao
Data de extracao: 24/06/2026
Total de documentos: 29 AEDAs (ano 2026)
"""
import sys
import io
import google.generativeai as genai
# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, insert_document
from vector_db import add_document_to_vector_db

# ============================================================
# AEDAs de 2026 extraídos da Rede Sirius UERJ
# Órgão emissor: Universidade do Estado do Rio de Janeiro - Reitoria
# ============================================================
AEDAS_2026 = [
    {
        "titulo": "AEDA 0001/REITORIA/2026 - Prorrogação dos Auxílios Transitórios (Vulnerabilidade Social Emergencial e Transporte Emergencial)",
        "tipo": "AEDA",
        "numero": "0001/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/VisualizadorPdf?codigoArquivo=28480&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0001/REITORIA/2026
        Data de assinatura: 13/01/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: PRORROGA O PAGAMENTO DOS AUXÍLIOS TRANSITÓRIOS: AUXÍLIO VULNERABILIDADE SOCIAL EMERGENCIAL E AUXÍLIO TRANSPORTE EMERGENCIAL.

        Este AEDA determina a prorrogação do pagamento dos auxílios transitórios destinados aos estudantes em situação de vulnerabilidade social, incluindo:
        - Auxílio Vulnerabilidade Social Emergencial: benefício financeiro temporário para estudantes em situação de extrema vulnerabilidade econômica.
        - Auxílio Transporte Emergencial: apoio financeiro emergencial para custeio de deslocamento residência-universidade.

        A prorrogação visa garantir a continuidade do suporte financeiro aos estudantes enquanto são processados os trâmites definitivos dos auxílios permanentes da PR-4 (Pró-Reitoria de Políticas e Assistência Estudantis).
        """
    },
    {
        "titulo": "AEDA 0002/REITORIA/2026 - Regulamentação de Emendas Parlamentares Estaduais via Fundação",
        "tipo": "AEDA",
        "numero": "0002/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/VisualizadorPdf?codigoArquivo=28491&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0002/REITORIA/2026
        Data de assinatura: 15/01/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: REGULAMENTA A EXECUÇÃO DAS EMENDAS PARLAMENTARES ESTADUAIS DESTINADAS À UNIVERSIDADE DO ESTADO DO RIO DE JANEIRO – UERJ POR MEIO DA FUNDAÇÃO.

        Este AEDA estabelece normas e procedimentos para a execução das emendas parlamentares estaduais destinadas à UERJ, regulamentando a utilização de fundações de apoio como intermediárias no processo. Define os fluxos de aprovação, prestação de contas e controle dos recursos recebidos via emendas parlamentares.
        """
    },
    {
        "titulo": "AEDA 0003/REITORIA/2026 - Criação de Função de Chefe de Seção de Secretaria para Programa de Pós-Graduação",
        "tipo": "AEDA",
        "numero": "0003/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/VisualizadorPdf?codigoArquivo=28756&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0003/REITORIA/2026
        Data de assinatura: 27/03/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: CRIA FUNÇÃO DE CHEFE DE SEÇÃO DE SECRETARIA PARA PROGRAMA DE PÓS-GRADUAÇÃO.

        Este AEDA cria a função gratificada de Chefe de Seção de Secretaria para atendimento aos Programas de Pós-Graduação da UERJ, visando melhorar a estrutura administrativa e o atendimento aos estudantes e docentes da pós-graduação.
        """
    },
    {
        "titulo": "AEDA 0004/REITORIA/2026 - Regulamentação de Concessão de Moradia e Pagamento (Lei nº 6.932/1981)",
        "tipo": "AEDA",
        "numero": "0004/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/acervo/detalhe/397871",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0004/REITORIA/2026
        Data de assinatura: 30/01/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: REGULAMENTA O ART. 4º, § 5º, INCISO III, DA LEI Nº 6.932, DE 7 DE JULHO DE 1981, PARA DISPOR SOBRE A CONCESSÃO DE MORADIA E O PAGAMENTO DE BENEFÍCIOS CORRELATOS.

        Este AEDA regulamenta as condições de concessão de moradia institucional e pagamentos correlatos para servidores e docentes da UERJ, com base no artigo 4º, § 5º, inciso III da Lei Estadual nº 6.932/1981. Define critérios de elegibilidade, procedimentos de solicitação e obrigações dos beneficiários.
        """
    },
    {
        "titulo": "AEDA 0005/REITORIA/2026 - Normas Internas para Avaliação, Gestão e Fiscalização de Contratações",
        "tipo": "AEDA",
        "numero": "0005/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/Busca/Download?codigoArquivo=28570&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0005/REITORIA/2026
        Data de assinatura: 06/02/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: ESTABELECE NORMAS INTERNAS E PROCEDIMENTOS PARA A AVALIAÇÃO DA GESTÃO E FISCALIZAÇÃO DAS CONTRATAÇÕES NO ÂMBITO DA UERJ.

        Este AEDA estabelece diretrizes e procedimentos internos para a avaliação, gestão e fiscalização de contratos celebrados pela UERJ. Define as responsabilidades dos gestores e fiscais de contratos, prazos de acompanhamento, formas de registro e prestação de contas. Visa garantir a eficiência, transparência e conformidade nas contratações públicas da universidade.
        """
    },
    {
        "titulo": "AEDA 0006/REITORIA/2026 - Codificação do Cargo em Comissão de Pró-Reitor de Planejamento e Gestão",
        "tipo": "AEDA",
        "numero": "0006/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/Busca/Download?codigoArquivo=28580&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0006/REITORIA/2026
        Data de assinatura: 10/02/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: CODIFICA O CARGO EM COMISSÃO DE PRÓ-REITOR DE PLANEJAMENTO E GESTÃO.

        Este AEDA procede à codificação do cargo em comissão de Pró-Reitor de Planejamento e Gestão, inserindo-o no plano de cargos comissionados da UERJ com sua respectiva designação funcional e nível de remuneração.
        """
    },
    {
        "titulo": "AEDA 0007/REITORIA/2026 - Criação da Pró-Reitoria de Planejamento e Gestão (PR-6)",
        "tipo": "AEDA",
        "numero": "0007/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/VisualizadorPdf?codigoArquivo=28575&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0007/REITORIA/2026
        Data de assinatura: 09/02/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: CRIA A PRÓ-REITORIA DE PLANEJAMENTO E GESTÃO - PR-6 E DEFINE OS EIXOS ESTRUTURANTES DAS ÁREAS VINCULADAS.

        Este AEDA cria formalmente a Pró-Reitoria de Planejamento e Gestão (PR-6) no organograma da UERJ, definindo seus eixos estruturantes e as áreas administrativas a ela vinculadas. A PR-6 tem como missão coordenar o planejamento estratégico, a gestão orçamentária e a modernização administrativa da universidade.
        """
    },
    {
        "titulo": "AEDA 0008/REITORIA/2026 - Reestruturação da Comissão de Apoio às Maternidades e Infâncias",
        "tipo": "AEDA",
        "numero": "0008/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/VisualizadorPdf?codigoArquivo=28576&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0008/REITORIA/2026
        Data de assinatura: 09/02/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: REESTRUTURA A COMISSÃO DE APOIO ÀS MATERNIDADES E INFÂNCIAS.

        Este AEDA promove a reestruturação da Comissão de Apoio às Maternidades e Infâncias da UERJ, atualizando sua composição, atribuições e funcionamento para melhor atender às necessidades de estudantes, servidoras e docentes em período de maternidade, bem como crianças pequenas que frequentam as dependências da universidade.
        """
    },
    {
        "titulo": "AEDA 0009/REITORIA/2026 - Alteração do AEDA nº 055/REITORIA/2025 sobre Emendas Parlamentares",
        "tipo": "AEDA",
        "numero": "0009/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/VisualizadorPdf?codigoArquivo=28687&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0009/REITORIA/2026
        Data de assinatura: 11/03/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: ALTERA O AEDA Nº 055/REITORIA/2025 QUE REGULAMENTA A CAPTAÇÃO, A APLICAÇÃO E A PRESTAÇÃO DE CONTAS ADEQUADAS QUANTO À EXECUÇÃO DAS EMENDAS PARLAMENTARES IMPOSITIVAS ESTADUAIS.

        Este AEDA altera dispositivos do AEDA nº 055/REITORIA/2025, atualizando as normas relativas à captação, aplicação e prestação de contas dos recursos oriundos de emendas parlamentares impositivas estaduais destinados à UERJ.
        """
    },
    {
        "titulo": "AEDA 0011/REITORIA/2026 - Institui a Semana de Ciência e Tecnologia da UERJ",
        "tipo": "AEDA",
        "numero": "0011/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/Busca/Download?codigoArquivo=28690&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0011/REITORIA/2026
        Data de assinatura: 19/03/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: INSTITUI A SEMANA DE CIÊNCIA E TECNOLOGIA DA UERJ.

        Este AEDA institui oficialmente a Semana de Ciência e Tecnologia da UERJ como evento anual permanente no calendário acadêmico da universidade. O evento visa promover a divulgação científica, a integração entre pesquisa e comunidade e o incentivo à vocação científica entre estudantes. Define as normas de organização, participação e periodicidade do evento.
        """
    },
    {
        "titulo": "AEDA 0012/REITORIA/2026 - Institui o Comitê Gestor dos Dados Abertos (CGDA) da UERJ",
        "tipo": "AEDA",
        "numero": "0012/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/VisualizadorPdf?codigoArquivo=28749&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0012/REITORIA/2026
        Data de assinatura: 24/03/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: INSTITUI O COMITÊ GESTOR DOS DADOS ABERTOS (CGDA) NO ÂMBITO DA UNIVERSIDADE DO ESTADO DO RIO DE JANEIRO E DÁ OUTRAS PROVIDÊNCIAS.

        Este AEDA cria o Comitê Gestor dos Dados Abertos (CGDA) da UERJ, em conformidade com a Lei de Acesso à Informação (Lei nº 12.527/2011) e a política nacional de dados abertos. O CGDA terá como atribuições: coordenar a publicação de dados abertos da instituição, garantir a transparência institucional, definir padrões de qualidade para os dados publicados e promover a interoperabilidade entre sistemas de informação da universidade.
        """
    },
    {
        "titulo": "AEDA 0013/REITORIA/2026 - Estrutura Administrativa da Pró-Reitoria de Pós-Graduação e Pesquisa (PR-2)",
        "tipo": "AEDA",
        "numero": "0013/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/VisualizadorPdf?codigoArquivo=28750&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0013/REITORIA/2026
        Data de assinatura: 25/03/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: ESTABELECE A ESTRUTURA ADMINISTRATIVA DA PRÓ-REITORIA DE PÓS-GRADUAÇÃO E PESQUISA - PR-2.

        Este AEDA define a estrutura administrativa da Pró-Reitoria de Pós-Graduação e Pesquisa (PR-2) da UERJ, estabelecendo suas divisões internas, competências, quadro de funções gratificadas e relações hierárquicas. A PR-2 é responsável pela coordenação e fomento de todos os Programas de Pós-Graduação stricto e lato sensu da universidade.
        """
    },
    {
        "titulo": "AEDA 0014/REITORIA/2026 - Extinção e Transformação de Cargos em Comissão e Funções Gratificadas",
        "tipo": "AEDA",
        "numero": "0014/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/VisualizadorPdf?codigoArquivo=28762&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0014/REITORIA/2026
        Data de assinatura: 30/03/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: EXTINÇÃO E TRANSFORMAÇÃO DE CARGOS EM COMISSÃO E FUNÇÕES GRATIFICADAS, SEM AUMENTO DE DESPESA.

        Este AEDA promove a extinção e transformação de cargos em comissão e funções gratificadas no âmbito da UERJ, sem geração de aumento de despesa para a folha de pagamento. As alterações visam adequar o quadro de cargos à nova estrutura administrativa da universidade.
        """
    },
    {
        "titulo": "AEDA 0015/REITORIA/2026 - Estrutura Administrativa da Pró-Reitoria de Planejamento e Gestão (PR-6)",
        "tipo": "AEDA",
        "numero": "0015/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/VisualizadorPdf?codigoArquivo=28766&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0015/REITORIA/2026
        Data de assinatura: 09/04/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: INSTITUI A ESTRUTURA ADMINISTRATIVA DA PRÓ-REITORIA DE PLANEJAMENTO E GESTÃO - PR-6, DEFINE SEU SISTEMA DE COMPETÊNCIAS E DÁ OUTRAS PROVIDÊNCIAS.

        Este AEDA, complementando o AEDA 0007/2026 que criou a PR-6, institui formalmente a estrutura administrativa detalhada da Pró-Reitoria de Planejamento e Gestão (PR-6), definindo:
        - Organograma interno com suas divisões e setores
        - Sistema de competências de cada unidade administrativa
        - Quadro de cargos em comissão e funções gratificadas
        - Atribuições do Pró-Reitor e demais dirigentes

        Possui Anexo: Organograma da PR-6.
        URL do Anexo: https://catalogo-redesirius.uerj.br/TerminalWeb/VisualizadorPdf?codigoArquivo=28767&tipoMidia=0
        """
    },
    {
        "titulo": "AEDA 0016/REITORIA/2026 - Unidades de Emendas Parlamentares Impositivas Estaduais de 2026",
        "tipo": "AEDA",
        "numero": "0016/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/Busca/Download?codigoArquivo=28765&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0016/REITORIA/2026
        Data de assinatura: 06/04/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: INSTITUI AS UNIDADES DE EMENDAS PARLAMENTARES IMPOSITIVAS ESTADUAIS DE 2026, NO ÂMBITO DA COMISSÃO TÉCNICA DE APOIO À AVALIAÇÃO E TRAMITAÇÃO DE EMENDAS PARLAMENTARES.

        Este AEDA institui as unidades responsáveis pelo recebimento, avaliação e tramitação das Emendas Parlamentares Impositivas Estaduais destinadas à UERJ no exercício de 2026, definindo a composição e atribuições da Comissão Técnica de Apoio.
        """
    },
    {
        "titulo": "AEDA 0017/REITORIA/2026 - Codificação de Funções Gratificadas",
        "tipo": "AEDA",
        "numero": "0017/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/Busca/Download?codigoArquivo=28770&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0017/REITORIA/2026
        Data de assinatura: 05/05/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: CODIFICA FUNÇÕES GRATIFICADAS.

        Este AEDA procede à codificação de funções gratificadas no âmbito da UERJ, inserindo-as no plano de cargos e funções da universidade com suas respectivas designações e códigos funcionais.
        """
    },
    {
        "titulo": "AEDA 0018/REITORIA/2026 - Transformação de Cargos em Comissão sem Aumento de Despesa",
        "tipo": "AEDA",
        "numero": "0018/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/VisualizadorPdf?codigoArquivo=28775&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0018/REITORIA/2026
        Data de assinatura: 11/05/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: TRANSFORMAÇÃO DE CARGOS EM COMISSÃO, SEM AUMENTO DE DESPESA.

        Este AEDA promove a transformação de cargos em comissão no âmbito da UERJ, adequando denominações e atribuições à nova estrutura organizacional, sem geração de aumento de despesa com pessoal.
        """
    },
    {
        "titulo": "AEDA 0019/REITORIA/2026 - Reajuste do Auxílio Alimentação com base no Decreto nº 22.398/96",
        "tipo": "AEDA",
        "numero": "0019/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/VisualizadorPdf?codigoArquivo=28776&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0019/REITORIA/2026
        Data de assinatura: 12/05/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: REAJUSTA, COM BASE NO DECRETO Nº 22.398/96, O VALOR DO AUXÍLIO ALIMENTAÇÃO.

        Este AEDA determina o reajuste do valor do Auxílio Alimentação concedido aos servidores da UERJ, conforme autorização prevista no Decreto Estadual nº 22.398/96. O reajuste visa adequar o benefício ao custo de vida e garantir a manutenção do poder de compra dos servidores.
        """
    },
    {
        "titulo": "AEDA 0020/REITORIA/2026 - Extinção de Funções Gratificadas",
        "tipo": "AEDA",
        "numero": "0020/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/VisualizadorPdf?codigoArquivo=28779&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0020/REITORIA/2026
        Data de assinatura: 14/05/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: EXTINÇÃO DE FUNÇÕES GRATIFICADAS.

        Este AEDA extingue funções gratificadas que se tornaram desnecessárias em razão de reestruturações administrativas, reorganização de setores ou encerramento de atividades específicas no âmbito da UERJ.
        """
    },
    {
        "titulo": "AEDA 0021/REITORIA/2026 - Reavaliação de Estudantes Indeferidos como Cotistas nos Vestibulares",
        "tipo": "AEDA",
        "numero": "0021/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/Busca/Download?codigoArquivo=28780&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0021/REITORIA/2026
        Data de assinatura: 29/05/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: DISPÕE SOBRE A REAVALIAÇÃO DE ESTUDANTES INDEFERIDOS COMO COTISTAS E APROVADOS NA AMPLA CONCORRÊNCIA NOS VESTIBULARES.

        Este AEDA regulamenta o procedimento de reavaliação para estudantes que foram indeferidos na cota de reserva de vagas (cotas sociais, raciais ou de escola pública) mas foram aprovados na ampla concorrência nos processos seletivos (vestibulares) da UERJ. Define os critérios e prazos para recursos administrativos e a garantia do direito à matrícula desses estudantes.

        IMPORTANTE PARA ESTUDANTES: Se você solicitou cota e foi indeferido, mas foi aprovado na lista de ampla concorrência, você tem direito a ingressar pela ampla concorrência. Este AEDA regula o processo de reavaliação do seu caso.
        """
    },
    {
        "titulo": "AEDA 0022/REITORIA/2026 - Transformação de Cargos em Comissão sem Aumento de Despesa (maio 2026)",
        "tipo": "AEDA",
        "numero": "0022/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/VisualizadorPdf?codigoArquivo=28800&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0022/REITORIA/2026
        Data de assinatura: 01/06/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: TRANSFORMAÇÃO DE CARGOS EM COMISSÃO, SEM AUMENTO DE DESPESA.

        Este AEDA promove nova transformação de cargos em comissão no âmbito da UERJ, adequando denominações e atribuições à estrutura organizacional vigente, sem geração de aumento de despesa com pessoal.
        """
    },
    {
        "titulo": "AEDA 0023/REITORIA/2026 - Alteração da Estrutura Administrativa da Pró-Reitoria de Extensão e Cultura (PR-3)",
        "tipo": "AEDA",
        "numero": "0023/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/acervo/detalhe/400267",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0023/REITORIA/2026
        Data de assinatura: 15/06/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: ALTERA A ESTRUTURA ADMINISTRATIVA DA PRÓ-REITORIA DE EXTENSÃO E CULTURA (PR-3).

        Este AEDA altera a estrutura administrativa da Pró-Reitoria de Extensão e Cultura (PR-3) da UERJ, promovendo ajustes no organograma interno, redistribuição de competências e atualização do quadro de funções gratificadas. A PR-3 é responsável pela coordenação das atividades de extensão universitária e promoção cultural da UERJ.
        """
    },
    {
        "titulo": "AEDA 0024/REITORIA/2026 - Alteração da Estrutura Administrativa da Pró-Reitoria de Políticas e Assistência Estudantis (PR-4)",
        "tipo": "AEDA",
        "numero": "0024/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/VisualizadorPdf?codigoArquivo=28804&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0024/REITORIA/2026
        Data de assinatura: 01/06/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: ALTERA A ESTRUTURA ADMINISTRATIVA DA PRÓ-REITORIA DE POLÍTICAS E ASSISTÊNCIA ESTUDANTIS - PR-4.

        Este AEDA altera a estrutura administrativa da Pró-Reitoria de Políticas e Assistência Estudantis (PR-4) da UERJ, promovendo ajustes no organograma, redistribuição de competências entre setores e atualização do quadro de cargos e funções. A PR-4 é responsável pela gestão das bolsas estudantis, auxílios financeiros e programas de assistência aos estudantes em vulnerabilidade socioeconômica.
        """
    },
    {
        "titulo": "AEDA 0025/REITORIA/2026 - Codificação da Função Gratificada de Chefe de Seção do Serviço de Psicologia Aplicada (SPA)",
        "tipo": "AEDA",
        "numero": "0025/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/Busca/Download?codigoArquivo=28801&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0025/REITORIA/2026
        Data de assinatura: 01/06/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: CODIFICA A FUNÇÃO GRATIFICADA DE CHEFE DE SEÇÃO DO SERVIÇO DE PSICOLOGIA APLICADA - SPA.

        Este AEDA procede à codificação da função gratificada de Chefe de Seção do Serviço de Psicologia Aplicada (SPA) da UERJ, formalizando sua inserção no plano de funções gratificadas da universidade.

        O Serviço de Psicologia Aplicada (SPA) oferece atendimento psicológico à comunidade universitária e à população externa, sendo importante serviço de saúde mental disponibilizado pela UERJ.
        """
    },
    {
        "titulo": "AEDA 0026/REITORIA/2026 - Alteração do AEDA 22/2025 sobre Contabilização de Pontos para Servidoras em Licença-Maternidade",
        "tipo": "AEDA",
        "numero": "0026/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/VisualizadorPdf?codigoArquivo=28805&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0026/REITORIA/2026
        Data de assinatura: 01/06/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: ALTERA O AEDA 22/2025, AMPLIANDO O PERÍODO DE CONTABILIZAÇÃO DE PONTOS NOS PROCESSOS SELETIVOS DA UERJ PARA SERVIDORAS QUE USUFRUÍRAM DE LICENÇA-MATERNIDADE OU ADOTANTE.

        Este AEDA altera o AEDA nº 22/2025 para ampliar o período de contabilização de pontos nos processos seletivos internos da UERJ para servidoras que estiveram em licença-maternidade ou licença adotante. A medida visa proteger as servidoras da desvantagem competitiva decorrente do afastamento por maternidade, garantindo equidade de gênero nos processos seletivos.
        """
    },
    {
        "titulo": "AEDA 0027/REITORIA/2026 - Alteração do AEDA 053/2023 sobre Progressão Funcional dos Servidores da UERJ",
        "tipo": "AEDA",
        "numero": "0027/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/VisualizadorPdf?codigoArquivo=28808&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0027/REITORIA/2026
        Data de assinatura: 02/06/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: ALTERA O AEDA 053/REITORIA/2023, QUE DISPÕE SOBRE AS NORMAS INTERNAS DA UNIVERSIDADE DO ESTADO DO RIO DE JANEIRO – UERJ PARA A PROGRESSÃO FUNCIONAL DOS SERVIDORES DO QUADRO TÉCNICO-ADMINISTRATIVO.

        Este AEDA altera o AEDA nº 053/REITORIA/2023, atualizando as normas internas para a progressão funcional dos servidores do quadro técnico-administrativo da UERJ. As alterações visam aprimorar os critérios de avaliação de desempenho, as condições de promoção e os prazos para progressão na carreira.
        """
    },
    {
        "titulo": "AEDA 0028/REITORIA/2026 - Alteração da Estrutura Administrativa da Editora da UERJ (EdUERJ)",
        "tipo": "AEDA",
        "numero": "0028/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/acervo/detalhe/400274",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0028/REITORIA/2026
        Data de assinatura: 03/06/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: ALTERA A ESTRUTURA ADMINISTRATIVA DA EDITORA DA UERJ - EDUERJ.

        Este AEDA altera a estrutura administrativa da Editora da Universidade do Estado do Rio de Janeiro (EdUERJ), promovendo ajustes no seu organograma interno, redistribuição de funções e atualização do quadro de cargos. A EdUERJ é responsável pela publicação e difusão de obras científicas, literárias e culturais produzidas pela comunidade acadêmica da UERJ.
        """
    },
    {
        "titulo": "AEDA 0029/REITORIA/2026 - Comissão de Padronização de Materiais Médico-Hospitalares da Policlínica Universitária Piquet Carneiro",
        "tipo": "AEDA",
        "numero": "0029/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/VisualizadorPdf?codigoArquivo=28812&tipoMidia=0",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0029/REITORIA/2026
        Data de assinatura: 10/06/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: INSTITUI E REGULAMENTA A COMISSÃO DE PADRONIZAÇÃO DE MATERIAIS MÉDICO-HOSPITALARES E MEDICAMENTOS DA POLICLÍNICA UNIVERSITÁRIA PIQUET CARNEIRO DA UNIVERSIDADE DO ESTADO DO RIO DE JANEIRO.

        Este AEDA cria e regulamenta a Comissão de Padronização de Materiais Médico-Hospitalares e Medicamentos (CPMHM) da Policlínica Universitária Piquet Carneiro (PUPC) da UERJ. A comissão terá como atribuições:
        - Padronizar os materiais médico-hospitalares utilizados na policlínica
        - Regulamentar os medicamentos dispensados pelo serviço de farmácia
        - Promover o uso racional de medicamentos
        - Avaliar e aprovar inclusões e exclusões na lista de materiais e medicamentos padronizados

        A Policlínica Universitária Piquet Carneiro oferece atendimento médico, odontológico e de diversas especialidades à comunidade universitária e à população em geral.
        """
    },
    {
        "titulo": "AEDA 0030/REITORIA/2026 - Reajuste do Adicional de Insalubridade com base no IPCA e Diretrizes para Concessão",
        "tipo": "AEDA",
        "numero": "0030/2026",
        "ano": 2026,
        "url": "https://catalogo-redesirius.uerj.br/TerminalWeb/acervo/detalhe/400293",
        "texto": """
        ATO EXECUTIVO DE DECISÃO ADMINISTRATIVA Nº 0030/REITORIA/2026
        Data de assinatura: 12/06/2026
        Órgão de origem: Universidade do Estado do Rio de Janeiro - Reitoria

        EMENTA: REAJUSTA OS VALORES DO ADICIONAL DE INSALUBRIDADE COM BASE NO IPCA E ESTABELECE DIRETRIZES PARA A REGULAMENTAÇÃO DOS PROCEDIMENTOS DE CONCESSÃO.

        Este AEDA determina o reajuste dos valores do Adicional de Insalubridade pago aos servidores da UERJ que exercem atividades em condições insalubres, com base na variação do Índice Nacional de Preços ao Consumidor Amplo (IPCA). Também estabelece diretrizes para a regulamentação dos procedimentos de concessão deste adicional, incluindo critérios de elegibilidade, laudos técnicos necessários e periodicidade de revisão.
        """
    },
]


def run_ingest_sirius_2026():
    """Ingere os AEDAs de 2026 extraídos da Rede Sirius no banco de dados."""
    print("=" * 60)
    print("Ingestão de AEDAs 2026 - Rede Sirius UERJ")
    print("=" * 60)
    
    # Inicializar banco se necessário
    init_db()
    
    inserted = 0
    updated = 0
    errors = 0
    
    for i, doc in enumerate(AEDAS_2026, 1):
        try:
            doc_id = insert_document(
                titulo=doc["titulo"],
                tipo=doc["tipo"],
                numero=doc["numero"],
                ano=doc["ano"],
                url=doc["url"],
                texto=doc["texto"].strip()
            )
            
            # Indexar no ChromaDB (vector DB)
            try:
                add_document_to_vector_db(
                    doc_id=doc_id,
                    titulo=doc["titulo"],
                    tipo=doc["tipo"],
                    texto=doc["texto"].strip()
                )
            except Exception as ve:
                print(f"  ⚠ Aviso: Falha ao indexar no ChromaDB (doc_id={doc_id}): {ve}")
            
            print(f"  [{i:02d}/{len(AEDAS_2026)}] [OK] Inserido/Atualizado: {doc['numero']} - {doc['titulo'][:60]}...")
            inserted += 1
            
        except Exception as e:
            print(f"  [{i:02d}/{len(AEDAS_2026)}] [ERRO] ao inserir {doc.get('numero', '?')}: {e}")
            errors += 1
    
    print()
    print("=" * 60)
    print(f"Resultado da ingestao:")
    print(f"  [OK] Documentos processados com sucesso: {inserted}")
    print(f"  [ERRO] Erros: {errors}")
    print(f"  Total de AEDAs 2026: {len(AEDAS_2026)}")
    print("=" * 60)


if __name__ == "__main__":
    run_ingest_sirius_2026()