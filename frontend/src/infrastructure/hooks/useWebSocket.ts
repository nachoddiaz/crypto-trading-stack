import { useEffect, useRef, useState, useCallback } from 'react'

interface WebSocketMessage {
    type: string
    symbol?: string
    bid_price?: number
    ask_price?: number
    timestamp?: number
}

interface UseWebSocketOptions {
    url: string
    onMessage?: (data: WebSocketMessage) => void
    reconnectInterval?: number
}

export function useWebSocket({ url, onMessage, reconnectInterval = 3000 }: UseWebSocketOptions) {
    const [isConnected, setIsConnected] = useState(false)
    const wsRef = useRef<WebSocket | null>(null)
    const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>()

    // Usar ref para el callback para evitar reconexiones cuando cambia
    const onMessageRef = useRef(onMessage)

    // Actualizar ref cuando cambia el callback
    useEffect(() => {
        onMessageRef.current = onMessage
    }, [onMessage])

    const connect = useCallback(() => {
        try {
            const ws = new WebSocket(url)
            wsRef.current = ws

            ws.onopen = () => {
                console.log('WebSocket connected')
                setIsConnected(true)
            }

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data)
                    // Usar ref para obtener siempre la última versión del callback
                    onMessageRef.current?.(data)
                } catch (e) {
                    console.error('Error parsing WebSocket message:', e)
                }
            }

            ws.onclose = () => {
                console.log('WebSocket disconnected, reconnecting...')
                setIsConnected(false)
                reconnectTimeoutRef.current = setTimeout(connect, reconnectInterval)
            }

            ws.onerror = (error) => {
                console.error('WebSocket error:', error)
                ws.close()
            }
        } catch (error) {
            console.error('Failed to connect WebSocket:', error)
            reconnectTimeoutRef.current = setTimeout(connect, reconnectInterval)
        }
    }, [url, reconnectInterval]) // onMessage removido de dependencias

    useEffect(() => {
        connect()

        return () => {
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current)
            }
            if (wsRef.current) {
                wsRef.current.close()
            }
        }
    }, [connect])

    return { isConnected }
}
