#!/bin/bash

# Playwright MCP Daemon Starter
# Mantiene Playwright MCP attivo su porta 8020

PLAYWRIGHT_PORT=8020
PLAYWRIGHT_PID_FILE="/tmp/playwright-mcp.pid"
PLAYWRIGHT_LOG_FILE="/home/sam/claude-code-multimodel/logs/playwright-mcp.log"

# Crea directory logs se non esiste
mkdir -p "$(dirname "$PLAYWRIGHT_LOG_FILE")"

check_playwright_running() {
    if [ -f "$PLAYWRIGHT_PID_FILE" ] && kill -0 "$(cat "$PLAYWRIGHT_PID_FILE")" 2>/dev/null; then
        echo "✅ Playwright MCP già attivo (PID: $(cat "$PLAYWRIGHT_PID_FILE"))"
        return 0
    fi
    return 1
}

start_playwright_daemon() {
    echo "🚀 Avvio Playwright MCP daemon su porta $PLAYWRIGHT_PORT..."
    
    # Verifica se porta è già occupata
    if netstat -tln | grep -q ":$PLAYWRIGHT_PORT "; then
        echo "⚠️ Porta $PLAYWRIGHT_PORT già occupata"
        # Trova il processo che usa la porta
        PORT_PID=$(lsof -ti:$PLAYWRIGHT_PORT 2>/dev/null)
        if [ -n "$PORT_PID" ]; then
            echo "Processo esistente PID: $PORT_PID"
            echo "$PORT_PID" > "$PLAYWRIGHT_PID_FILE"
            return 0
        fi
    fi
    
    # Avvia Playwright MCP
    nohup npx @playwright/mcp --port "$PLAYWRIGHT_PORT" --headless \
        > "$PLAYWRIGHT_LOG_FILE" 2>&1 &
    
    PLAYWRIGHT_PID=$!
    echo "$PLAYWRIGHT_PID" > "$PLAYWRIGHT_PID_FILE"
    
    # Attendi che il server sia pronto
    echo "⏳ Attendo che Playwright MCP sia pronto..."
    for i in {1..30}; do
        if curl -s "http://localhost:$PLAYWRIGHT_PORT/health" >/dev/null 2>&1; then
            echo "✅ Playwright MCP attivo su http://localhost:$PLAYWRIGHT_PORT"
            echo "📝 SSE endpoint: http://localhost:$PLAYWRIGHT_PORT/sse"
            echo "📋 Log file: $PLAYWRIGHT_LOG_FILE"
            return 0
        fi
        sleep 1
    done
    
    echo "❌ Playwright MCP non si è avviato correttamente"
    return 1
}

stop_playwright_daemon() {
    if [ -f "$PLAYWRIGHT_PID_FILE" ]; then
        PID=$(cat "$PLAYWRIGHT_PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "🛑 Terminazione Playwright MCP (PID: $PID)"
            kill "$PID"
            rm -f "$PLAYWRIGHT_PID_FILE"
        else
            echo "❌ Processo non trovato, rimuovo PID file"
            rm -f "$PLAYWRIGHT_PID_FILE"
        fi
    else
        echo "❌ Nessun PID file trovato"
    fi
}

status_playwright() {
    if check_playwright_running; then
        echo "📊 Status: ATTIVO"
        echo "🔗 SSE URL: http://localhost:$PLAYWRIGHT_PORT/sse"
        echo "📋 Log: tail -f $PLAYWRIGHT_LOG_FILE"
    else
        echo "📊 Status: NON ATTIVO"
    fi
}

case "$1" in
    start)
        if ! check_playwright_running; then
            start_playwright_daemon
        fi
        ;;
    stop)
        stop_playwright_daemon
        ;;
    restart)
        stop_playwright_daemon
        sleep 2
        start_playwright_daemon
        ;;
    status)
        status_playwright
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        echo ""
        echo "Comandi:"
        echo "  start   - Avvia Playwright MCP daemon"
        echo "  stop    - Termina Playwright MCP daemon"
        echo "  restart - Riavvia Playwright MCP daemon"
        echo "  status  - Mostra status Playwright MCP"
        exit 1
        ;;
esac