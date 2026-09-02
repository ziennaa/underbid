export type RoundStartedEvent = {
    event_type: "ROUND_STARTED";
    negotiation_id: number;
    round_number: number;
  };
  
  export type OfferCreatedEvent = {
    event_type: "OFFER_CREATED";
    negotiation_id: number;
    round_number: number;
  
    seller_name: string;
    price: string;
    base_price: string;
  
    delivery_days: number;
    warranty_months: number;
    addons: string[];
  
    status: string;
    utility_score: number | null;
  };
  
  export type SellerWalkedEvent = {
    event_type: "SELLER_WALKED";
    negotiation_id: number;
    round_number: number;
    seller_name: string;
  };
  
  export type DealFoundEvent = {
    event_type: "DEAL_FOUND";
    negotiation_id: number;
    round_number: number;
  
    seller_name: string;
    price: string;
    utility_score: number | null;
  };
  
  export type NoDealEvent = {
    event_type: "NO_DEAL";
    negotiation_id: number;
    round_number: number;
    reason: string;
  };
  
  export type NegotiationEvent =
    | RoundStartedEvent
    | OfferCreatedEvent
    | SellerWalkedEvent
    | DealFoundEvent
    | NoDealEvent;
  
  
  const WS_BASE_URL =
    process.env.NEXT_PUBLIC_WS_URL ??
    "ws://127.0.0.1:8000";
  
  
  export function connectNegotiationSocket(
    negotiationId: number,
    handlers: {
      onOpen?: () => void;
      onEvent?: (event: NegotiationEvent) => void;
      onClose?: () => void;
      onError?: () => void;
    },
  ): WebSocket {
    const socket = new WebSocket(
      `${WS_BASE_URL}/ws/negotiations/${negotiationId}`,
    );
  
    socket.onopen = () => {
      handlers.onOpen?.();
    };
  
    socket.onmessage = (message) => {
      const event = JSON.parse(
        message.data,
      ) as NegotiationEvent;
  
      handlers.onEvent?.(event);
    };
  
    socket.onclose = () => {
      handlers.onClose?.();
    };
  
    socket.onerror = () => {
      handlers.onError?.();
    };
  
    return socket;
  }