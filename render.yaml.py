services:
  - type: web
    name: spine-bot
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    healthCheckPath: /health
    envVars:
      - key: BOT_TOKEN
        value: 8432200353:AAEE-YdcvRKTnU0FbAcASbNiFIVdbFR_bC8
