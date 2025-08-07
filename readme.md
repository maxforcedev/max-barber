# BarberFlow - Sistema de Agendamento para Barbearias

Sistema backend desenvolvido em Django, focado em agendamentos para barbearias e gestão de usuários com login via senha ou código de verificação (WhatsApp).

## 🚀 Visão Geral

O BarberFlow é um sistema de agendamento online voltado para barbearias de pequeno e médio porte. Ele oferece:

- Registro de clientes e barbeiros
- Autenticação via senha **ou** código via WhatsApp
- Cadastro e visualização de horários disponíveis
- Painel administrativo para controle dos agendamentos
- Integração com sistema de envio de mensagens Evolution API

## 🔧 Tecnologias Utilizadas

- Python 3.11+
- Django 5+
- Django REST Framework
- PostgreSQL
- Redis (para verificação de código temporário)
- Evolution API (envio de mensagens WhatsApp)
- Docker (ambiente de produção)
- JWT (SimpleJWT)

## ⚙️ Funcionalidades

### ✅ Usuários
- Cadastro obrigatório com senha
- Login com:
  - telefone + senha
  - telefone + código de verificação (sem senha)

### 💈 Barbearia / Barbeiros
- CRUD de barbeiros (admin)
- Relacionamento entre horários e barbeiros
- Cadastro de serviços (ex: corte, barba, combo)

### 📅 Agendamento
- Horários disponíveis por barbeiro
- Clientes escolhem data, horário e serviço
- Cancelamento e histórico de agendamentos

### 🔐 Autenticação
- JWT para segurança das rotas privadas
- Envio de código por WhatsApp para login sem senha
- Expiração de código (via Redis)

## 📁 Estrutura dos Apps (provisório)

- `accounts/` → usuários e autenticação
- `barbers/` → barbeiros e serviços
- `scheduling/` → agendamentos
- `notifications/` → envio de código via Evolution
- `core/` → configs globais

## 📌 Status

> ⚠️ Em desenvolvimento ativo — base de autenticação sendo implementada.

---

Mais atualizações em breve.  
Projeto em fase de estruturação para produção real.

