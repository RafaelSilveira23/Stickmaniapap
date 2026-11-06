# Diagrama de Gantt — StickMania

Planeamento do projeto da PAP, de setembro de 2026 a junho de 2027. O GitHub desenha o diagrama
a partir do código Mermaid abaixo. As barras escuras são tarefas concluídas, as realçadas estão
em curso e as claras estão planeadas.

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
    Anteprojeto, requisitos e escolha das tecnologias :done, t1, 2026-09-15, 2026-10-10
    section Desenvolvimento (versões 1 a 20)
    Protótipo - rinque, jogadores, bola e física :done, t2, 2026-10-01, 2026-10-10
    Interface do mockup, símbolos e seleção de equipas :done, t3, 2026-10-06, 2026-10-15
    Mira de remate, IA com dificuldades e faltas :done, t4, 2026-10-11, 2026-10-20
    Animações, balizas, câmara e bancadas :done, t5, 2026-10-16, 2026-10-24
    Correção das colisões, IA tática e guarda-redes :done, t6, 2026-10-21, 2026-10-28
    Correção da bola no stick e da ordem de desenho :done, t7, 2026-10-25, 2026-10-31
    Modo carreira com SQLite :done, t8, 2026-11-01, 2026-11-08
    Menu novo, definições, ecrã inteiro e gráficos :done, t9, 2026-11-04, 2026-11-11
    Sons, simulação dos jogos e ecrãs da carreira :done, t10, 2026-11-08, 2026-11-15
    Planteis reais, marcadores e melhores marcadores :done, t11, 2026-11-11, 2026-11-18
    Estilo arcade (golos e impactos) :done, t12, 2026-11-15, 2026-11-21
    Remate na primeira pessoa e modo teste :done, t13, 2026-11-18, 2026-11-24
    Remate em movimento, defesas e bloqueio :done, t14, 2026-11-21, 2026-11-27
    Ecrã do remate (pavilhão, placas, stick) :done, t15, 2026-11-24, 2026-11-30
    Defesas no remate - perspetiva e sprites HD :done, t16, 2026-11-27, 2026-12-03
    Carreira de jogador (só o meu jogador) :done, t17, 2026-12-04, 2026-12-18
    Vida do jogador - escolhas, eventos e atividades :done, t18, 2026-12-14, 2026-12-31
    Menus e gráficos - pausa, fim de jogo e transições :done, t19, 2026-12-28, 2027-01-10
    Vida - pessoas, consequências e conquistas :done, t20, 2027-01-11, 2027-01-24
    Otimização, arranque sem consola e limpeza :done, t21, 2027-01-25, 2027-01-31
    Modo online - jogar contra um amigo pela internet :done, t22, 2027-02-01, 2027-02-14
    section Novas funcionalidades
    Estatísticas da partida e modo de 2 jogadores :t23, 2026-11-16, 2026-12-31
    Mais estatísticas e transferências :t24, 2027-01-07, 2027-03-31
    section Validação e entrega
    Testes com colegas, correção de erros, sprites :t25, 2027-03-01, 2027-04-30
    Relatório final, manual e apresentação :active, t26, 2027-04-01, 2027-05-31
    Defesa da PAP :t27, 2027-06-01, 2027-06-30
```

## Tarefas

| N.º | Fase | Tarefa | Início | Fim | Estado |
|---|---|---|---|---|---|
| 1 | Análise e planeamento | Anteprojeto, requisitos e escolha das tecnologias | 15/09/2026 | 10/10/2026 | Concluído |
| 2 | Desenvolvimento (versões 1 a 20) | Protótipo: rinque, jogadores, bola e física | 01/10/2026 | 10/10/2026 | Concluído |
| 3 | Desenvolvimento (versões 1 a 20) | Interface do mockup, símbolos e seleção de equipas | 06/10/2026 | 15/10/2026 | Concluído |
| 4 | Desenvolvimento (versões 1 a 20) | Mira de remate, IA com dificuldades e faltas | 11/10/2026 | 20/10/2026 | Concluído |
| 5 | Desenvolvimento (versões 1 a 20) | Animações, balizas, câmara e bancadas | 16/10/2026 | 24/10/2026 | Concluído |
| 6 | Desenvolvimento (versões 1 a 20) | Correção das colisões, IA tática e guarda-redes | 21/10/2026 | 28/10/2026 | Concluído |
| 7 | Desenvolvimento (versões 1 a 20) | Correção da bola no stick e da ordem de desenho | 25/10/2026 | 31/10/2026 | Concluído |
| 8 | Desenvolvimento (versões 1 a 20) | Modo carreira com SQLite | 01/11/2026 | 08/11/2026 | Concluído |
| 9 | Desenvolvimento (versões 1 a 20) | Menu novo, definições, ecrã inteiro e gráficos | 04/11/2026 | 11/11/2026 | Concluído |
| 10 | Desenvolvimento (versões 1 a 20) | Sons, simulação dos jogos e ecrãs da carreira | 08/11/2026 | 15/11/2026 | Concluído |
| 11 | Desenvolvimento (versões 1 a 20) | Planteis reais, marcadores e melhores marcadores | 11/11/2026 | 18/11/2026 | Concluído |
| 12 | Desenvolvimento (versões 1 a 20) | Estilo arcade (golos e impactos) | 15/11/2026 | 21/11/2026 | Concluído |
| 13 | Desenvolvimento (versões 1 a 20) | Remate na primeira pessoa e modo teste | 18/11/2026 | 24/11/2026 | Concluído |
| 14 | Desenvolvimento (versões 1 a 20) | Remate em movimento, defesas e bloqueio | 21/11/2026 | 27/11/2026 | Concluído |
| 15 | Desenvolvimento (versões 1 a 20) | Ecrã do remate (pavilhão, placas, stick) | 24/11/2026 | 30/11/2026 | Concluído |
| 16 | Desenvolvimento (versões 1 a 20) | Defesas no remate: perspetiva e sprites HD | 27/11/2026 | 03/12/2026 | Concluído |
| 17 | Desenvolvimento (versões 1 a 20) | Carreira de jogador (só o meu jogador) | 04/12/2026 | 18/12/2026 | Concluído |
| 18 | Desenvolvimento (versões 1 a 20) | Vida do jogador: escolhas, eventos e atividades | 14/12/2026 | 31/12/2026 | Concluído |
| 19 | Desenvolvimento (versões 1 a 20) | Menus e gráficos: pausa, fim de jogo e transições | 28/12/2026 | 10/01/2027 | Concluído |
| 20 | Desenvolvimento (versões 1 a 20) | Vida: pessoas, consequências e conquistas | 11/01/2027 | 24/01/2027 | Concluído |
| 21 | Desenvolvimento (versões 1 a 20) | Otimização, arranque sem consola e limpeza | 25/01/2027 | 31/01/2027 | Concluído |
| 22 | Desenvolvimento (versões 1 a 20) | Modo online: jogar contra um amigo pela internet | 01/02/2027 | 14/02/2027 | Concluído |
| 23 | Novas funcionalidades | Estatísticas da partida e modo de 2 jogadores | 16/11/2026 | 31/12/2026 | Planeado |
| 24 | Novas funcionalidades | Mais estatísticas e transferências | 07/01/2027 | 31/03/2027 | Planeado |
| 25 | Validação e entrega | Testes com colegas, correção de erros, sprites | 01/03/2027 | 30/04/2027 | Planeado |
| 26 | Validação e entrega | Relatório final, manual e apresentação | 01/04/2027 | 31/05/2027 | Em curso |
| 27 | Validação e entrega | Defesa da PAP | 01/06/2027 | 30/06/2027 | Planeado |
