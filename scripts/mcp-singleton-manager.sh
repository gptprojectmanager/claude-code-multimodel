#!/bin/bash

# MCP Singleton Manager - Evita duplicazione server MCP
# Usage: ./mcp-singleton-manager.sh [start|stop|status|cleanup]

LOCK_DIR="/tmp/claude-mcp-locks"
MAIN_LOCK="$LOCK_DIR/main.lock"
PID_FILE="$LOCK_DIR/mcp_manager.pid"

# Crea directory lock se non esiste
mkdir -p "$LOCK_DIR"

start_mcp_servers() {
    # Verifica se manager già attivo
    if [ -f "$MAIN_LOCK" ] && kill -0 "$(cat "$MAIN_LOCK")" 2>/dev/null; then
        echo "✅ MCP Manager già attivo (PID: $(cat "$MAIN_LOCK"))"
        return 0
    fi

    echo "🚀 Avvio MCP Singleton Manager..."
    
    # Registra PID corrente
    echo $$ > "$MAIN_LOCK"
    echo $$ > "$PID_FILE"
    
    # Cleanup automatico al termine
    trap 'cleanup_on_exit' EXIT INT TERM
    
    echo "📋 MCP Manager attivo con PID: $$"
    
    # Mantieni processo attivo
    while true; do
        sleep 30
        # Verifica se claude è ancora attivo
        if ! pgrep -f "claude" > /dev/null; then
            echo "⚠️ Nessuna istanza Claude attiva, terminando MCP Manager"
            break
        fi
    done
}

stop_mcp_servers() {
    echo "🛑 Terminazione MCP servers..."
    
    # Termina processi MCP
    pkill -f "mcp-" 2>/dev/null
    pkill -f "npm exec.*mcp" 2>/dev/null
    pkill -f "context7-mcp" 2>/dev/null
    pkill -f "n8n-mcp-server" 2>/dev/null
    
    # Rimuovi lock files
    rm -f "$MAIN_LOCK" "$PID_FILE"
    rm -f "$LOCK_DIR"/*.lock
    
    echo "✅ MCP servers terminati"
}

status_mcp() {
    if [ -f "$MAIN_LOCK" ] && kill -0 "$(cat "$MAIN_LOCK")" 2>/dev/null; then
        echo "✅ MCP Manager attivo (PID: $(cat "$MAIN_LOCK"))"
        echo "📊 Processi MCP attivi:"
        ps aux | grep -E "(mcp-|npm exec.*mcp|context7|n8n-mcp)" | grep -v grep | wc -l | xargs echo "   - Totale processi:"
    else
        echo "❌ MCP Manager non attivo"
    fi
}

cleanup_on_exit() {
    echo "🧹 Cleanup MCP Manager..."
    stop_mcp_servers
    exit 0
}

force_cleanup() {
    echo "🔧 Cleanup forzato processi MCP duplicati..."
    
    # Termina tutte le istanze Claude tranne quella corrente
    current_claude_pid=$(pgrep -f "claude" | head -1)
    for pid in $(pgrep -f "claude"); do
        if [ "$pid" != "$current_claude_pid" ]; then
            echo "Terminando Claude PID: $pid"
            kill -TERM "$pid" 2>/dev/null
        fi
    done
    
    # Cleanup completo MCP
    stop_mcp_servers
    
    # Rimuovi directory lock
    rm -rf "$LOCK_DIR"
    
    echo "✅ Cleanup completato"
}

case "$1" in
    start)
        start_mcp_servers
        ;;
    stop)
        stop_mcp_servers
        ;;
    status)
        status_mcp
        ;;
    cleanup)
        force_cleanup
        ;;
    *)
        echo "Usage: $0 {start|stop|status|cleanup}"
        echo ""
        echo "Commands:"
        echo "  start   - Avvia MCP Manager singleton"
        echo "  stop    - Termina tutti i MCP servers"
        echo "  status  - Mostra stato MCP Manager"
        echo "  cleanup - Cleanup forzato duplicati"
        exit 1
        ;;
esac