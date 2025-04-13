#!/bin/bash

cat <<EOF > /etc/webhook/hooks.json
[
  {
    "id": "deploy-development",
    "execute-command": "/scripts/deploy.sh",
    "command-working-directory": "/scripts",
    "pass-arguments-to-command": [
      {
        "source": "payload",
        "name": "ref"
      }
    ],
    "trigger-rule": {
      "match": {
        "type": "value",
        "value": "refs/heads/development",
        "parameter": {
          "source": "payload",
          "name": "ref"
        }
      }
    },
    "secret": "$GITHUB_WEBHOOK_SECRET"
  }
]
EOF

exec /usr/local/bin/webhook -hooks /etc/webhook/hooks.json -port 9001 -verbose
