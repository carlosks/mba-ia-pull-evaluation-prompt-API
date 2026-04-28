Otimização de Prompt — Bug to User Story

Objetivo

O objetivo desta etapa foi otimizar o prompt inicial (`bug_to_user_story_v1.yml`) utilizando técnicas de engenharia de prompt, com foco em:

- Melhorar a qualidade das respostas
- Garantir consistência estrutural
- Aumentar desempenho em métricas de avaliação (F1, precisão, etc.)
- Aplicar técnicas modernas de prompt engineering

---

Análise do Prompt Inicial (v1)

O prompt inicial apresentava as seguintes limitações:

-  Ausência de persona bem definida
-  Falta de exemplos (few-shot)
-  Instruções pouco específicas sobre formato
-  Baixa previsibilidade das respostas
-  Resultados inconsistentes em avaliações automatizadas

---

Estratégia de Otimização

Foi criada uma nova versão (`bug_to_user_story_v18.yml`) com melhorias estruturais e aplicação de técnicas avançadas.

---

Técnicas Aplicadas

1.  Few-shot Learning (OBRIGATÓRIO)

Foram incluídos exemplos completos de entrada e saída para guiar o modelo:

- Exemplo de bug report
- Exemplo de User Story no formato correto
- Critérios de aceitação estruturados

Impacto:
- Aumenta consistência
- Reduz ambiguidade
- Melhora aderência ao formato esperado

---

2. Role Prompting

Definição clara de persona:

```text
"Você é um Product Manager experiente..."

Impacto:

Contextualiza o modelo
Melhora qualidade semântica
Torna respostas mais realistas

3. Structured Output (Skeleton of Thought)

Definição explícita do formato de saída:

User Story padrão:
Como um...
Eu quero...
Para que...
Critérios de aceitação:
Dado que...
Quando...
Então...
E...
E...

Impacto:

Respostas padronizadas
Melhor avaliação automatizada
Facilita validação

4. Regras Estritas de Formatação

Foram adicionadas regras como:

Uso obrigatório de 5 critérios
Proibição de texto fora do formato
Proibição de explicações adicionais

Impacto:

Reduz variação de saída
Melhora métricas como F1 e precisão
Resultados Obtidos

Após otimização, o prompt foi avaliado com os seguintes resultados:

Métrica	Resultado
F1 Score	0.9911 
Precision	1.0000 
Correctness	0.9956 
Helpfulness	0.9500 
Clarity	0.9000 

Média geral: 0.9673

Critérios de Aprovação

Todos os critérios foram atendidos:

Helpfulness ≥ 0.9
Correctness ≥ 0.9
F1 Score ≥ 0.9
Clarity ≥ 0.9
Precision ≥ 0.9
Média ≥ 0.9

Testes Automatizados

Foram implementados testes com pytest para validar:

Presença de system prompt
Definição de persona
Uso de formato estruturado
Inclusão de few-shot examples
Ausência de TODOs
Uso de pelo menos 2 técnicas

Resultado:

6 passed 

Conclusão

A otimização do prompt resultou em:

Alta consistência de saída
Forte aderência ao formato esperado
Excelente desempenho nas métricas
Validação automatizada completa

Aprendizados
Prompt engineering impacta diretamente métricas de avaliação
Few-shot learning é essencial para controle de saída
Estrutura explícita melhora previsibilidade
F1 exige controle lexical, não apenas semântico

