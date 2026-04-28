# Webhook Setup Guide

## Overview

In **push mode**, paca-agent starts a FastAPI server that receives task assignment webhooks from your project management platform.

## Endpoint

```
POST http://<your-host>:<WEBHOOK_PORT>/webhook/<platform>
```

Where `<platform>` is one of: `paca`, `jira`, `trello`, `clickup`, `redmine`.

## Security

Set `WEBHOOK_SECRET` in your `.env`. The server will validate the `X-Hub-Signature-256` header (HMAC-SHA256) on every incoming request — the same scheme used by GitHub webhooks.

## Platform Configuration

### Paca

In your Paca workspace settings → Integrations → Webhooks, add:
- **URL**: `https://agent.example.com/webhook/paca`
- **Events**: `task.assigned`, `task.created`

### Jira

In your Jira project → Settings → System → WebHooks, add:
- **URL**: `https://agent.example.com/webhook/jira`
- **Events**: Issue → Updated (assigned), Issue → Created

### Trello

Use the [Trello REST API](https://developer.atlassian.com/cloud/trello/rest/api-group-webhooks/) to register:
```bash
curl -X POST "https://api.trello.com/1/webhooks" \
  -d "key=<key>&token=<token>&callbackURL=https://agent.example.com/webhook/trello&idModel=<board_id>"
```

### ClickUp

In ClickUp → Settings → Integrations → Webhooks, add:
- **URL**: `https://agent.example.com/webhook/clickup`
- **Events**: `taskAssigneeUpdated`, `taskCreated`

### Redmine

Install the [redmine_webhook](https://github.com/suer/redmine_webhook) plugin, then configure:
- **URL**: `https://agent.example.com/webhook/redmine`

## Health Check

```
GET http://<your-host>:<WEBHOOK_PORT>/health
→ {"status": "ok"}
```
