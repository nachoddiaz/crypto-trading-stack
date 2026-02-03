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
                    onMessage?.(data)
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
    }, [url, onMessage, reconnectInterval])

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
