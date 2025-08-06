🧠 Sistema de Agendamento para Barbearia

📝 Descrição Geral

Você foi contratado para desenvolver o backend de um sistema de agendamento para uma barbearia. O sistema deve permitir que clientes agendem horários com barbeiros, escolham serviços, visualizem disponibilidade, e acompanhem seus agendamentos. Barbeiros podem gerenciar sua agenda, e o administrador controla os serviços, horários e o cadastro de profissionais.

🧩 Funcionalidades por Perfil

👤 Cliente
- Cadastro/login
- Listar barbeiros disponíveis
- Ver horários livres por data/barbeiro
- Agendar serviço
- Cancelar agendamento (até X horas antes)
- Ver histórico de agendamentos

✂️ Barbeiro
- Login
- Ver sua própria agenda
- Bloquear horários (ex: almoço, folga)
- Confirmar presença do cliente (check-in manual)

🛠️ Admin
- CRUD de barbeiros
- CRUD de serviços
- Definir horários de funcionamento
- Ver agenda geral
- Forçar agendamentos ou cancelamentos

🔁 Regras de Negócio

- Um agendamento só pode ser feito se:
  - Horário estiver livre
  - Estiver dentro do horário de funcionamento do barbeiro
- Cancelamento permitido até X horas antes (ex: 2h)
- Um barbeiro não pode ter dois agendamentos no mesmo horário
- O sistema deve calcular automaticamente o end_time com base na duração do serviço
- Barbeiros podem bloquear horários (motivo opcional)

📌 Extras Técnicos (opcional para impressionar)

- Notificações por e-mail (confirmação/cancelamento)
- Pagamento online (Stripe, MercadoPago)
- Geração de QR Code para check-in
- Suporte para múltiplas unidades (multi-barbearia)
- Painel admin customizado

🎯 Objetivo

Criar o backend completo em Django + DRF, com foco em:
- Boas práticas
- Arquitetura REST
- Testes automatizados
- Organização e segurança
- Validações de regras de negócio

🧪 Avaliação esperada

- Validação correta dos horários
- Agendamentos sem conflito
- Modelagem coerente
- Separação por roles
- Documentação clara (README + Swagger/OpenAPI)