export type NegotiationCreateRequest = {
    product: string;
    reference_price: number;
    budget: number;
    max_delivery_days: number;
    price_weight: number;
    delivery_weight: number;
    warranty_weight: number;
    randomize_sellers: boolean;
    seed: number | null;
  };
  
  export type NegotiationCreatedResponse = {
    negotiation_id: number;
    status: "CREATED";
  };
  
  export type Offer = {
    seller_name: string;
    price: string;
    base_price: string;
    delivery_days: number;
    warranty_months: number;
    addons: string[];
    status: string;
    utility_score: number | null;
  };
  
  export type NegotiationRound = {
    round_number: number;
    offers: Offer[];
  };
  
  export type Negotiation = {
    id: number;
    product: string;
    budget: string;
    max_delivery_days: number;
  
    price_weight: number;
    delivery_weight: number;
    warranty_weight: number;
  
    status:
      | "CREATED"
      | "RUNNING"
      | "DEAL_FOUND"
      | "NO_DEAL";
  
    winner_seller_name: string | null;
    final_price: string | null;
    created_at: string;
  
    rounds: NegotiationRound[];
  };
  
  const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL ??
    "http://127.0.0.1:8000";
  
  export async function createNegotiation(
    request: NegotiationCreateRequest,
  ): Promise<NegotiationCreatedResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/negotiations`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
      },
    );
  
    if (!response.ok) {
      throw new Error(
        `Failed to create negotiation: ${response.status}`,
      );
    }
  
    return response.json();
  }
  
  export async function getNegotiation(
    negotiationId: number,
  ): Promise<Negotiation> {
    const response = await fetch(
      `${API_BASE_URL}/api/negotiations/${negotiationId}`,
    );
  
    if (!response.ok) {
      throw new Error(
        `Failed to fetch negotiation: ${response.status}`,
      );
    }
  
    return response.json();
  }
  
  export async function startNegotiation(
    negotiationId: number,
  ): Promise<{
    negotiation_id: number;
    status: "RUNNING";
  }> {
    const response = await fetch(
      `${API_BASE_URL}/api/negotiations/${negotiationId}/start`,
      {
        method: "POST",
      },
    );
  
    if (!response.ok) {
      throw new Error(
        `Failed to start negotiation: ${response.status}`,
      );
    }
  
    return response.json();
  }