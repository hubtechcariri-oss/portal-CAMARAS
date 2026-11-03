# Portal para Câmaras Municipais: proposta inicial de produto

Data: 03/11/2026
Referência analisada: https://camaraassare.ce.gov.br/

**Legenda de confiabilidade**
- **[Verificado]**: observado diretamente no site de referência em 03/11/2026.
- **[Fonte]**: tirado de fonte pública citada.
- **[Inferência]**: conclusão minha, que precisa de validação (jurídica, comercial ou técnica).

---

## 1. Resumo executivo

O site de Assaré não é um produto isolado. É uma instância de uma plataforma de um fornecedor regional (o rodapé credita a **Assesi**), com URLs e estrutura típicas de um portal padronizado para câmaras. Ou seja, o mercado existe e já tem concorrentes, inclusive um gratuito do Senado (Interlegis).

O valor que a câmara compra não é "um site bonito". O valor está em três coisas:

1. **Passar nas avaliações de transparência** (PNTP/Atricon e Tribunal de Contas). O selo "Prata 2025" aparece com destaque no portal de referência.
2. **Tirar trabalho do servidor**: publicar leis, sessões, diárias e contratos sem depender de TI.
3. **Reduzir risco jurídico**: LAI, LRF, LGPD, acessibilidade e Lei 14.133.

Recomendação: um **SaaS multi-tenant monolítico** (um código, um banco com isolamento por câmara), com o **checklist do PNTP como o "backlog" do produto**, e um MVP que coloque uma câmara-piloto no ar em 3 a 4 meses.

---

## 2. Análise do site de referência

### 2.1 Estrutura e funcionalidades [Verificado]

| Área | O que existe |
|---|---|
| Barra superior | Transparência, Ouvidoria/e-SIC, Pesquisa, Acessibilidade (contraste, aumentar/diminuir fonte, VLibras, mapa do site), redes sociais |
| Institucional | Sobre a Câmara, Ouvidoria, e-SIC, Lei Orgânica, Regimento Interno, Dicionário Legislativo, Papel do Vereador, Papel da Câmara |
| Legislativo | Parlamentares (páginas individuais), Galeria de Vereadores, Mesa Diretora, Comissões, Sessões, Proposições/Matérias, Legislaturas |
| Gestão Fiscal | Prestação de Contas de Gestão (PCS), Relatório de Gestão Fiscal (RGF) |
| Comunicação | Notícias, Vídeos, Links Úteis, carrossel na home |
| Transparência (página de Acesso à Informação) | ~50 itens em 6 grupos (ver 2.2) |
| Conformidade | Banner de cookies (Concordo/Não concordo), Política de Privacidade, página de selos Atricon |
| Rodapé | CNPJ, endereço, horário, telefone, e-mail, "© 2026 Assesi" |

### 2.2 Página de Transparência [Verificado]

- **Atendimento ao cidadão:** e-SIC, Ouvidoria, Fale Conosco, Carta de Serviços.
- **Execução orçamentária e financeira:** Receitas, Despesas, Ordem Cronológica de pagamentos. **Todos apontam para um sistema externo** (`governotransparente.com.br`).
- **Gestão administrativa:** Decretos, Quadro de Pessoal, Portarias, Diárias, Licitações, Contratos, Legislação, Publicações, Veículos, Obras, Concurso Público, Plano Estratégico, Terceirizados, Estagiários.
- **Fiscal e contas:** LRF, PCS, PCG.
- **Legislativo:** vereadores, sessões, matérias, FAQ, **Dados Abertos**, Glossário, **Cotas Parlamentares**.
- **Normas:** Tabela de diárias, PCA (Plano de Contratação Anual), regulamentações (LAI, diárias, LGPD, Governo Digital, cotas), Pesquisa de Satisfação, link para o Radar da Transparência da Atricon.

### 2.3 O que isso revela sobre o modelo de negócio

- **[Verificado]** Os dados de receitas e despesas vêm de outro sistema (contábil/financeiro). O portal só faz o link.
- **[Inferência]** Esse é o padrão do mercado. A contabilidade pública da câmara roda em um ERP de outro fornecedor (exigido pelo SIAFIC, Decreto 10.540/2020), e o portal institucional é um produto separado. **Não tente competir com o ERP contábil no começo.** Integre ou faça link.
- **[Verificado]** Os cards de vereadores mostram "0 Matérias" para todos. **[Inferência]** O módulo legislativo existe, mas a câmara não alimenta. Isso indica uma dor real: cadastrar matéria é trabalhoso. Um produto que facilite isso (importar PDF, preencher metadados, workflow simples) tem diferencial.
- **[Inferência]** A estrutura de URLs (`.php`, `?car=11`, `?cat=4`) sugere uma aplicação PHP legada e padronizada entre clientes, ou seja, um template replicado por câmara.
- **[Verificado]** O webmail aponta para um domínio de terceiro (`webmail-seguro.com.br`). **[Inferência]** O fornecedor provavelmente vende hospedagem e e-mail junto. É receita adicional possível, mas fora do núcleo.

### 2.4 Concorrência [Fonte + Inferência]

- **Interlegis / Senado Federal**: oferece **gratuitamente** o *Portal Modelo* e o *SAPL* (Sistema de Apoio ao Processo Legislativo) a câmaras parceiras, e o Senado divulga câmaras que ganharam selo de transparência usando-os ([Senado/Interlegis](https://www12.senado.leg.br/interlegis/materias/com-portal-modelo-camara-de-santana-do-serido-conquista-selo-de-transparencia-pelo-segundo-ano-consecutivo)). **Esse é o concorrente mais importante a entender:** o seu produto precisa justificar o preço contra o gratuito. O argumento comercial costuma ser suporte, implantação, alimentação assistida de conteúdo e responsabilidade pelo selo.
- **Fornecedores regionais** (Assesi no Ceará, entre muitos outros; o próprio resultado de busca mostra a Assesi promovendo o "Troféu Diamantes da Transparência" para prefeituras e câmaras). **[Inferência]** O mercado é pulverizado e regional, e é vendido por relacionamento e por licitação/dispensa.
- **Sistemas legislativos especializados** (ex.: Plenus e similares) com sessão eletrônica, votação e painel.

---

## 3. Obrigações legais que o produto precisa atender

> Aviso: esta seção é um mapeamento técnico, não parecer jurídico. Valide com um advogado de direito público e, principalmente, com a **matriz de avaliação do PNTP do ano vigente** e com as instruções do **Tribunal de Contas de cada estado** onde for vender.

| Norma | O que exige do portal (resumo) | Confiança |
|---|---|---|
| **LAI, Lei 12.527/2011** | Transparência ativa (art. 8º): estrutura, competências, endereços, horários, repasses, despesas, licitações e contratos, FAQ. Pesquisa, download em formatos abertos e legíveis por máquina, acessibilidade. Transparência passiva: e-SIC com protocolo e prazo de 20 dias (+10). | [Fonte: texto legal] |
| **LRF, LC 101/2000, arts. 48 e 48-A (incluídos pela LC 131/2009)** | Informações pormenorizadas de receitas e despesas **em tempo real** e RGF, PCS. | [Fonte: texto legal] |
| **Lei 14.133/2021 (Licitações)** | Publicidade de licitações e contratos, PCA. Divulgação obrigatória no PNCP (art. 174). O portal deve espelhar ou linkar. | [Fonte] + [Inferência] sobre integração com o PNCP |
| **Lei 13.460/2017** | Ouvidoria e Carta de Serviços ao Usuário. | [Fonte] |
| **Lei 14.129/2021 (Governo Digital)** | Dados abertos, serviços digitais. A aplicabilidade a municípios depende de adesão/regulamentação local; o site de referência tem "Regulamentação do Governo Digital". | [Inferência] |
| **LGPD, Lei 13.709/2018** | Política de privacidade, encarregado (DPO) indicado, base legal para coleta (e-SIC, ouvidoria), consentimento de cookies não essenciais, segurança, registro de operações. **O fornecedor SaaS é operador; a câmara é controladora.** Isso precisa estar no contrato. Atenção ao conflito LAI × LGPD: publicar remuneração nominal de servidores é exigido; CPF completo não. | [Fonte] + [Inferência] sobre o desenho contratual |
| **Lei Brasileira de Inclusão, Lei 13.146/2015, art. 63** | Sites de órgãos públicos devem ser acessíveis. Na prática: **eMAG** (Modelo de Acessibilidade em Governo Eletrônico) e WCAG 2.x nível AA, VLibras. | [Fonte] |
| **PNTP (Programa Nacional de Transparência Pública, Atricon/TCs)** | Não é lei, mas é **o critério pelo qual a câmara é avaliada e recebe selo**. A matriz lista itens essenciais, obrigatórios e recomendados. O selo exibido em Assaré ("Prata 2025") vem desse programa. | [Verificado] o selo; [Inferência] que é o principal driver de compra |
| **Instruções do Tribunal de Contas estadual** | Cada TCE pode exigir itens e formatos próprios (ex.: TCE-CE para Assaré). | [Inferência]: precisa levantamento por estado |
| **Domínio `.leg.br`** | Câmaras podem usar `.leg.br` (gerido com o Interlegis); muitas usam `.gov.br`. O produto deve suportar domínio próprio por cliente. | [Inferência] |

**Implicação de produto [Inferência]:** transforme a matriz do PNTP em um **painel de conformidade dentro do admin** ("você cumpre 78 de 92 itens; faltam: diárias de setembro, contrato X..."). Isso vende melhor que qualquer funcionalidade visual, porque responde à pergunta que o presidente da câmara realmente faz: "vamos ganhar o selo?".

---

## 4. Escopo funcional proposto

### 4.1 Portal público (por câmara)
- Home configurável (banner, notícias, vereadores, atalhos, selos).
- Institucional: páginas livres (CMS), Lei Orgânica, Regimento.
- Vereadores: perfil, partido, legislaturas, comissões, matérias de autoria, presenças.
- Legislativo: sessões (pauta, ata, vídeo, votações), matérias/proposições com tramitação, normas jurídicas (leis, decretos legislativos, resoluções, portarias) com busca por número, ano, tipo e texto.
- Transparência: estrutura de menus pronta, alinhada ao PNTP, com módulos estruturados (diárias, pessoal, licitações, contratos, obras, veículos, terceirizados, estagiários, concursos, cotas parlamentares) e links/integrações para receitas e despesas do ERP contábil.
- e-SIC e Ouvidoria: protocolo, prazos, respostas, recurso, relatório estatístico anual.
- Notícias, vídeos (embed YouTube), galerias.
- Busca global, mapa do site, FAQ, glossário.
- Dados abertos: cada listagem exportável em CSV/JSON + API pública de leitura.
- Acessibilidade: eMAG/WCAG AA, VLibras, contraste, fonte, atalhos de teclado.
- LGPD: banner de cookies real (que de fato bloqueia rastreadores sem consentimento), política de privacidade, canal do titular.

### 4.2 Painel administrativo
- Usuários e perfis por câmara (admin, comunicação, legislativo, transparência, ouvidor).
- Cadastro estruturado com upload de PDF, metadados e publicação agendada.
- **Painel de conformidade PNTP** (diferencial).
- Alertas de vencimento (ex.: "RGF do 2º quadrimestre ainda não publicado"; "pedido e-SIC vence em 3 dias").
- Trilha de auditoria (quem publicou, alterou ou removeu o quê e quando). É importante porque informação pública removida vira problema.
- Importação em massa (planilha, PDFs) para migrar o acervo de um fornecedor anterior.

### 4.3 Fora do MVP (fases posteriores)
- Sessão eletrônica / votação nominal / painel de plenário.
- Tramitação legislativa completa com protocolo eletrônico e assinatura digital (ICP-Brasil).
- Integrações automáticas com ERPs contábeis e com o PNCP.
- Diário Oficial do Legislativo.
- App móvel. **[Inferência]** Um portal responsivo resolve; app raramente se paga nesse mercado.

---

## 5. Arquitetura recomendada

### 5.1 Princípios
- **Proporcionalidade.** O tráfego de um portal de câmara pequena é baixo (milhares de acessos/mês). Centenas de câmaras cabem confortavelmente em poucos servidores. **Microserviços e Kubernetes não se justificam no início.**
- **Um código para todos os clientes.** Diferenças entre câmaras são configuração (tema, menus, módulos ativos), nunca fork.
- **Conteúdo público é cacheável.** 95%+ das requisições são leitura anônima. Use CDN agressivamente.

### 5.2 Desenho

```
               ┌──────────── CDN (cache, TLS, WAF básico) ────────────┐
camara-x.leg.br ─┤                                                      │
camara-y.gov.br ─┤──► App monolítica (modular) ──► PostgreSQL (tenant_id + RLS)
                 │      ├─ Portal público (SSR)      │
                 │      ├─ Admin                      ├─► Storage S3-compatível (PDFs, imagens)
                 │      ├─ API pública (dados abertos)├─► Busca full-text (Postgres FTS → OpenSearch se precisar)
                 │      └─ Jobs (fila): e-mails, OCR, └─► Fila/jobs (no próprio Postgres ou Redis)
                 │         alertas, importações
```

| Decisão | Recomendação | Por quê |
|---|---|---|
| Multi-tenancy | **Banco compartilhado, `tenant_id` em todas as tabelas + Row-Level Security do Postgres** | Custo operacional mínimo e migrações únicas. O RLS dá uma segunda barreira contra vazamento entre câmaras. Schema-por-tenant ou banco-por-tenant só se um cliente grande exigir contratualmente. |
| Resolução de tenant | Pelo **domínio** da requisição (tabela `dominios → tenant`) | Cada câmara usa o próprio domínio; certificados automáticos (Let's Encrypt / CDN). |
| Aplicação | **Monólito modular** em uma stack que a equipe domine (Laravel, Django, Rails, Next.js+Node ou .NET são todas adequadas) | O gargalo é velocidade de entrega e custo de manutenção, não escala. |
| Renderização | **SSR/HTML server-side** com JS mínimo | Acessibilidade, SEO, desempenho em conexões ruins e celulares simples. SPA pesada atrapalha eMAG. |
| Arquivos | Object storage com URLs estáveis e permanentes | Documento público não pode "quebrar link". O PNTP e os TCs verificam links. |
| Busca | Postgres full-text search (português) no início | Evita mais um componente. OCR de PDFs escaneados em job assíncrono. |
| Dados abertos | Toda listagem com `?format=csv/json` | Requisito da LAI resolvido de forma barata e uniforme. |
| Auditoria | Tabela append-only de eventos + soft delete | Prova de publicação e histórico. |
| Hospedagem | Nuvem com região no Brasil | **[Inferência]** Não há obrigação legal geral de dados no Brasil, mas facilita a conversa de LGPD e a de editais. |
| Backups | Diários, com retenção de 30+ dias e teste de restauração | Óbvio, mas é o que derruba fornecedor pequeno. |

### 5.3 Modelo de dados núcleo (simplificado)
`tenant`, `dominio`, `usuario`, `perfil`, `pagina`, `noticia`, `parlamentar`, `legislatura`, `mandato`, `comissao`, `sessao`, `materia`, `tramitacao`, `norma`, `documento` (genérico, com `categoria_transparencia` mapeada aos itens do PNTP), `pedido_esic`, `manifestacao_ouvidoria`, `evento_auditoria`.

**Dica de modelagem [Inferência]:** a maioria dos ~50 itens de transparência é "lista de documentos com metadados" (data, competência, número, PDF). Um modelo genérico `documento` + `categoria` configurável cobre 70% do menu sem criar 50 telas. Só faça módulos estruturados (com campos próprios) onde o PNTP pede dado tabular: diárias, pessoal, contratos, licitações.

---

## 6. Fases do MVP

| Fase | Duração estimada [Inferência] | Entrega | Critério de pronto |
|---|---|---|---|
| **0. Descoberta** | 2 a 3 semanas | Baixar a matriz PNTP vigente, levantar exigências do TCE do estado-alvo, entrevistar 3 a 5 câmaras (secretário, comunicação, controle interno), fechar uma câmara-piloto | Lista priorizada de itens obrigatórios e uma piloto comprometida |
| **1. MVP público** | 8 a 10 semanas | Multi-tenant, CMS, vereadores, notícias, normas, documentos de transparência por categoria, e-SIC/ouvidoria, acessibilidade, LGPD/cookies, dados abertos CSV/JSON | Piloto no ar com domínio próprio e **avaliação interna pela matriz PNTP com todos os itens "essenciais" atendidos** |
| **2. Produto vendável** | 6 a 8 semanas | Painel de conformidade PNTP, alertas de prazo, importação em massa (migração), sessões com pauta/ata/vídeo, matérias com tramitação simples, temas configuráveis | Implantação de uma câmara nova em **menos de 1 semana** |
| **3. Diferenciação** | contínua | Integrações com ERPs contábeis comuns na região, espelho do PNCP, OCR, sessão/votação eletrônica, assinatura digital | Guiado por pedidos de clientes pagantes |

Equipe mínima sugerida [Inferência]: 2 devs full-stack + 1 pessoa de produto/implantação (que entenda de câmara e de PNTP). A pessoa de implantação é tão importante quanto os devs, porque o serviço de "alimentar e manter o selo" é parte do que se vende.

---

## 7. Riscos e pontos de atenção

1. **Concorrente gratuito (Interlegis).** Defina cedo o argumento de valor: suporte, implantação, conformidade garantida, alimentação assistida.
2. **Venda ao setor público.** Contratação via licitação ou dispensa por valor (Lei 14.133). Ciclos atrelados ao orçamento e a mudança de mesa diretora (anual/bienal). Prepare documentação de habilitação e atestados de capacidade técnica desde o primeiro cliente.
3. **Variação por estado.** Cada TCE tem as suas exigências. Comece por **um estado** e domine-o.
4. **Responsabilidade LGPD.** Contrato de operador, DPA, plano de resposta a incidentes.
5. **Critérios mudam todo ano.** A matriz PNTP é revista anualmente. Modele categorias de transparência como configuração, não como código.
6. **Migração de acervo.** O cliente que troca de fornecedor tem anos de PDFs. Sem ferramenta de importação, a implantação vira trabalho manual caro.
7. **Clonagem visual.** Não copie layout, textos ou marca da Assesi ou de outro fornecedor. A estrutura de informação é ditada pela lei e pelo PNTP e pode ser reproduzida; o design e o código, não.

---

## 8. Próximos passos sugeridos

1. Definir stack e equipe (ver pergunta na conversa).
2. Escolher o estado-alvo e baixar a matriz PNTP vigente + normas do TCE.
3. Conseguir uma câmara-piloto (idealmente com quem você já tenha relacionamento).
4. Com isso, detalhar o backlog da Fase 1 e o modelo de dados.

---

### Fontes
- Site de referência: https://camaraassare.ce.gov.br/ e https://camaraassare.ce.gov.br/acessoainformacao (acessados em 03/11/2026)
- Interlegis / Portal Modelo: https://www12.senado.leg.br/interlegis/materias/com-portal-modelo-camara-de-santana-do-serido-conquista-selo-de-transparencia-pelo-segundo-ano-consecutivo
- Assesi / Troféu Diamantes da Transparência: https://diariodonordeste.verdesmares.com.br/opiniao/colunistas/sisi-por-jeritza-gurgel/captei-assesi-brasil-homenageia-prefeituras-e-camaras-com-trofeu-diamantes-da-transparencia-1.3771725
- Radar da Transparência Pública (Atricon): https://radardatransparencia.atricon.org.br/
- Textos legais citados: Lei 12.527/2011, LC 101/2000 (com LC 131/2009), Lei 14.133/2021, Lei 13.460/2017, Lei 14.129/2021, Lei 13.709/2018, Lei 13.146/2015, Decreto 10.540/2020 (citados de conhecimento prévio; não reconsultados nesta análise)
