# Diagrama de Gantt — StickMania

Planeamento do projeto da PAP, de setembro de 2026 a junho de 2027. O GitHub desenha o diagrama
a partir do código Mermaid abaixo. As barras escuras são tarefas concluídas, as realçadas estão
em curso e as claras estão planeadas.

**Divisão de tarefas:** o projeto é feito em dupla. Cada tarefa diz entre parênteses quem a fez (Vasco Andreia: 16 tarefas; Rafael da Hora Silveira: 10; os dois: 11). Na imagem do relatório ([`09_gantt.png`](diagramas/09_gantt.png)) a cor de cada barra mostra quem fez a tarefa.

> Este ficheiro é gerado pelo script [`docs/diagramas/gerar_gantt.py`](diagramas/gerar_gantt.py),
> o mesmo que faz a imagem do relatório ([`09_gantt.png`](diagramas/09_gantt.png)): os dois têm
> sempre as mesmas datas.

```mermaid
gantt
    title StickMania - Diagrama de Gantt (set. 2026 a jun. 2027)
    dateFormat YYYY-MM-DD
    axisFormat %m/%Y
    tickInterval 1month
    todayMarker off
    section Análise e planeamento
    Anteprojeto, requisitos e escolha das tecnologias (Os dois) :done, t1, 2026-09-15, 2026-10-10
    section Desenvolvimento (versões 1 a 29)
    Protótipo - rinque, jogadores, bola e física (Rafael) :done, t2, 2026-10-01, 2026-10-10
    Interface do mockup, símbolos e seleção de equipas (Vasco) :done, t3, 2026-10-06, 2026-10-15
    IA com três níveis de dificuldade (Vasco) :done, t4, 2026-10-11, 2026-10-20
    Mira de remate e faltas (Rafael) :done, t5, 2026-10-11, 2026-10-20
    Animações, balizas, câmara e bancadas (Rafael) :done, t6, 2026-10-16, 2026-10-24
    Correção das colisões (Rafael) :done, t7, 2026-10-21, 2026-10-28
    IA tática e guarda-redes (Vasco) :done, t8, 2026-10-21, 2026-10-28
    Correção da bola no stick e da ordem de desenho (Rafael) :done, t9, 2026-10-25, 2026-10-31
    Modo carreira - campeonato e calendário (Os dois) :done, t10, 2026-11-01, 2026-11-08
    Base de dados SQLite (Vasco) :done, t11, 2026-11-01, 2026-11-08
    Menu novo, definições e ecrã inteiro (Vasco) :done, t12, 2026-11-04, 2026-11-11
    Gráficos do rinque e do pavilhão (Rafael) :done, t13, 2026-11-04, 2026-11-11
    Sons criados por síntese (Vasco) :done, t14, 2026-11-08, 2026-11-15
    Simulação dos jogos e ecrãs da carreira (Os dois) :done, t15, 2026-11-08, 2026-11-15
    Planteis reais, marcadores e melhores marcadores (Os dois) :done, t16, 2026-11-11, 2026-11-18
    Estilo arcade (golos e impactos) (Os dois) :done, t17, 2026-11-15, 2026-11-21
    Remate na primeira pessoa e modo teste (Vasco) :done, t18, 2026-11-18, 2026-11-24
    Remate em movimento, defesas e bloqueio (Vasco) :done, t19, 2026-11-21, 2026-11-27
    Ecrã do remate (pavilhão, placas, stick) (Vasco) :done, t20, 2026-11-24, 2026-11-30
    Defesas no remate - perspetiva e sprites HD (Vasco) :done, t21, 2026-11-27, 2026-12-03
    Carreira de jogador (só o meu jogador) (Vasco) :done, t22, 2026-12-04, 2026-12-18
    Vida do jogador - escolhas, eventos e atividades (Vasco) :done, t23, 2026-12-14, 2026-12-31
    Menus - pausa, fim de jogo e transições (Vasco) :done, t24, 2026-12-28, 2027-01-10
    Vida - pessoas, consequências e conquistas (Vasco) :done, t25, 2027-01-11, 2027-01-24
    Otimização, arranque sem consola e limpeza (Os dois) :done, t26, 2027-01-25, 2027-01-31
    Modo online - jogar contra um amigo pela internet (Rafael) :done, t27, 2027-02-01, 2027-02-14
    Versão para o browser (site) e online com código (Rafael) :done, t28, 2027-02-15, 2027-02-28
    Aplicação para Windows, instalador e servidor online (Rafael) :done, t29, 2027-03-01, 2027-03-14
    Guarda-redes no ecrã do remate (animação) (Vasco) :done, t30, 2027-03-15, 2027-03-21
    Stickada no online e servidor na Europa (Rafael) :done, t31, 2027-03-22, 2027-03-28
    Cânticos dos clubes (feitos por código) (Vasco) :done, t32, 2027-03-29, 2027-04-04
    section Novas funcionalidades
    Estatísticas da partida e modo de 2 jogadores (Os dois) :t33, 2026-11-16, 2026-12-31
    Mais estatísticas e transferências (Os dois) :t34, 2027-01-07, 2027-03-31
    section Validação e entrega
    Testes com colegas, correção de erros, sprites (Os dois) :t35, 2027-03-01, 2027-04-30
    Relatório final, manual e apresentação (Os dois) :active, t36, 2027-04-01, 2027-05-31
    Defesa da PAP (Os dois) :t37, 2027-06-01, 2027-06-30
```

## Tarefas

| N.º | Fase | Tarefa | Quem fez | Início | Fim | Estado |
|---|---|---|---|---|---|---|
| 1 | Análise e planeamento | Anteprojeto, requisitos e escolha das tecnologias | **Os dois** | 15/09/2026 | 10/10/2026 | Concluído |
| 2 | Desenvolvimento (versões 1 a 29) | Protótipo: rinque, jogadores, bola e física | **Rafael da Hora Silveira** | 01/10/2026 | 10/10/2026 | Concluído |
| 3 | Desenvolvimento (versões 1 a 29) | Interface do mockup, símbolos e seleção de equipas | **Vasco Andreia** | 06/10/2026 | 15/10/2026 | Concluído |
| 4 | Desenvolvimento (versões 1 a 29) | IA com três níveis de dificuldade | **Vasco Andreia** | 11/10/2026 | 20/10/2026 | Concluído |
| 5 | Desenvolvimento (versões 1 a 29) | Mira de remate e faltas | **Rafael da Hora Silveira** | 11/10/2026 | 20/10/2026 | Concluído |
| 6 | Desenvolvimento (versões 1 a 29) | Animações, balizas, câmara e bancadas | **Rafael da Hora Silveira** | 16/10/2026 | 24/10/2026 | Concluído |
| 7 | Desenvolvimento (versões 1 a 29) | Correção das colisões | **Rafael da Hora Silveira** | 21/10/2026 | 28/10/2026 | Concluído |
| 8 | Desenvolvimento (versões 1 a 29) | IA tática e guarda-redes | **Vasco Andreia** | 21/10/2026 | 28/10/2026 | Concluído |
| 9 | Desenvolvimento (versões 1 a 29) | Correção da bola no stick e da ordem de desenho | **Rafael da Hora Silveira** | 25/10/2026 | 31/10/2026 | Concluído |
| 10 | Desenvolvimento (versões 1 a 29) | Modo carreira: campeonato e calendário | **Os dois** | 01/11/2026 | 08/11/2026 | Concluído |
| 11 | Desenvolvimento (versões 1 a 29) | Base de dados SQLite | **Vasco Andreia** | 01/11/2026 | 08/11/2026 | Concluído |
| 12 | Desenvolvimento (versões 1 a 29) | Menu novo, definições e ecrã inteiro | **Vasco Andreia** | 04/11/2026 | 11/11/2026 | Concluído |
| 13 | Desenvolvimento (versões 1 a 29) | Gráficos do rinque e do pavilhão | **Rafael da Hora Silveira** | 04/11/2026 | 11/11/2026 | Concluído |
| 14 | Desenvolvimento (versões 1 a 29) | Sons criados por síntese | **Vasco Andreia** | 08/11/2026 | 15/11/2026 | Concluído |
| 15 | Desenvolvimento (versões 1 a 29) | Simulação dos jogos e ecrãs da carreira | **Os dois** | 08/11/2026 | 15/11/2026 | Concluído |
| 16 | Desenvolvimento (versões 1 a 29) | Planteis reais, marcadores e melhores marcadores | **Os dois** | 11/11/2026 | 18/11/2026 | Concluído |
| 17 | Desenvolvimento (versões 1 a 29) | Estilo arcade (golos e impactos) | **Os dois** | 15/11/2026 | 21/11/2026 | Concluído |
| 18 | Desenvolvimento (versões 1 a 29) | Remate na primeira pessoa e modo teste | **Vasco Andreia** | 18/11/2026 | 24/11/2026 | Concluído |
| 19 | Desenvolvimento (versões 1 a 29) | Remate em movimento, defesas e bloqueio | **Vasco Andreia** | 21/11/2026 | 27/11/2026 | Concluído |
| 20 | Desenvolvimento (versões 1 a 29) | Ecrã do remate (pavilhão, placas, stick) | **Vasco Andreia** | 24/11/2026 | 30/11/2026 | Concluído |
| 21 | Desenvolvimento (versões 1 a 29) | Defesas no remate: perspetiva e sprites HD | **Vasco Andreia** | 27/11/2026 | 03/12/2026 | Concluído |
| 22 | Desenvolvimento (versões 1 a 29) | Carreira de jogador (só o meu jogador) | **Vasco Andreia** | 04/12/2026 | 18/12/2026 | Concluído |
| 23 | Desenvolvimento (versões 1 a 29) | Vida do jogador: escolhas, eventos e atividades | **Vasco Andreia** | 14/12/2026 | 31/12/2026 | Concluído |
| 24 | Desenvolvimento (versões 1 a 29) | Menus: pausa, fim de jogo e transições | **Vasco Andreia** | 28/12/2026 | 10/01/2027 | Concluído |
| 25 | Desenvolvimento (versões 1 a 29) | Vida: pessoas, consequências e conquistas | **Vasco Andreia** | 11/01/2027 | 24/01/2027 | Concluído |
| 26 | Desenvolvimento (versões 1 a 29) | Otimização, arranque sem consola e limpeza | **Os dois** | 25/01/2027 | 31/01/2027 | Concluído |
| 27 | Desenvolvimento (versões 1 a 29) | Modo online: jogar contra um amigo pela internet | **Rafael da Hora Silveira** | 01/02/2027 | 14/02/2027 | Concluído |
| 28 | Desenvolvimento (versões 1 a 29) | Versão para o browser (site) e online com código | **Rafael da Hora Silveira** | 15/02/2027 | 28/02/2027 | Concluído |
| 29 | Desenvolvimento (versões 1 a 29) | Aplicação para Windows, instalador e servidor online | **Rafael da Hora Silveira** | 01/03/2027 | 14/03/2027 | Concluído |
| 30 | Desenvolvimento (versões 1 a 29) | Guarda-redes no ecrã do remate (animação) | **Vasco Andreia** | 15/03/2027 | 21/03/2027 | Concluído |
| 31 | Desenvolvimento (versões 1 a 29) | Stickada no online e servidor na Europa | **Rafael da Hora Silveira** | 22/03/2027 | 28/03/2027 | Concluído |
| 32 | Desenvolvimento (versões 1 a 29) | Cânticos dos clubes (feitos por código) | **Vasco Andreia** | 29/03/2027 | 04/04/2027 | Concluído |
| 33 | Novas funcionalidades | Estatísticas da partida e modo de 2 jogadores | **Os dois** | 16/11/2026 | 31/12/2026 | Planeado |
| 34 | Novas funcionalidades | Mais estatísticas e transferências | **Os dois** | 07/01/2027 | 31/03/2027 | Planeado |
| 35 | Validação e entrega | Testes com colegas, correção de erros, sprites | **Os dois** | 01/03/2027 | 30/04/2027 | Planeado |
| 36 | Validação e entrega | Relatório final, manual e apresentação | **Os dois** | 01/04/2027 | 31/05/2027 | Em curso |
| 37 | Validação e entrega | Defesa da PAP | **Os dois** | 01/06/2027 | 30/06/2027 | Planeado |
