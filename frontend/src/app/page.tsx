"use client";

import {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  createNegotiation,
  startNegotiation,
} from "@/lib/api";

import {
  connectNegotiationSocket,
  type NegotiationEvent,
  type OfferCreatedEvent,
} from "@/lib/socket";

type WeightKey = "price" | "delivery" | "warranty";

type Weights = {
  price: number;
  delivery: number;
  warranty: number;
};

const WEIGHT_KEYS: WeightKey[] = [
  "price",
  "delivery",
  "warranty",
];

export default function Home() {
  const [product, setProduct] = useState("");
  const [budget, setBudget] = useState("");
  const [isCreating, setIsCreating] = useState(false);

const [createError, setCreateError] =
  useState<string | null>(null);

const [negotiationId, setNegotiationId] =
  useState<number | null>(null);
  const [maxDeliveryDays, setMaxDeliveryDays] =
    useState(4);

  const [weights, setWeights] = useState<Weights>({
    price: 60,
    delivery: 25,
    warranty: 15,
  });
  const [negotiationStatus, setNegotiationStatus] =
  useState<
    "CREATED" |
    "RUNNING" |
    "DEAL_FOUND" |
    "NO_DEAL"
  >("CREATED");

const [startError, setStartError] =
  useState<string | null>(null);
const [receivedEvents, setReceivedEvents] =
  useState<NegotiationEvent[]>([]);
const socketRef = useRef<WebSocket | null>(null);
  const [socketStatus, setSocketStatus] =
  useState<
    "DISCONNECTED" |
    "CONNECTING" |
    "CONNECTED" |
    "ERROR"
  >("DISCONNECTED");


  useEffect(() => {
    if (negotiationId === null) {
      return;
    }
  
    const socket = connectNegotiationSocket(
      negotiationId,
      {
        onOpen: async () => {
          if (socketRef.current !== socket) {
            return;
          }
  
          setSocketStatus("CONNECTED");
          setStartError(null);
  
          try {
            await startNegotiation(negotiationId);
  
            setNegotiationStatus("RUNNING");
          } catch (error) {
            if (error instanceof Error) {
              setStartError(error.message);
            } else {
              setStartError(
                "Failed to start the negotiation.",
              );
            }
          }
        },
        onEvent: (event) => {
          setReceivedEvents((previous) => [
            ...previous,
            event,
          ]);
        
          if (event.event_type === "DEAL_FOUND") {
            setNegotiationStatus("DEAL_FOUND");
          }
        
          if (event.event_type === "NO_DEAL") {
            setNegotiationStatus("NO_DEAL");
          }
        },
        onClose: () => {
          if (socketRef.current === socket) {
            setSocketStatus("DISCONNECTED");
          }
        },
  
        onError: () => {
          if (socketRef.current === socket) {
            setSocketStatus("ERROR");
          }
        },
      },
    );
  
    socketRef.current = socket;
  
    return () => {
      if (socketRef.current === socket) {
        socketRef.current = null;
      }
  
      socket.close();
    };
  }, [negotiationId]);

  function updateWeight(
    changedKey: WeightKey,
    newValue: number,
  ) {
    const clampedValue = Math.max(
      0,
      Math.min(100, newValue),
    );

    setWeights((previous) => {
      const otherKeys = WEIGHT_KEYS.filter(
        (key) => key !== changedKey,
      );

      const firstKey = otherKeys[0];
      const secondKey = otherKeys[1];

      const remaining = 100 - clampedValue;

      const previousOtherTotal =
        previous[firstKey] + previous[secondKey];

      let firstValue: number;

      if (previousOtherTotal === 0) {
        firstValue = Math.floor(remaining / 2);
      } else {
        firstValue = Math.round(
          (previous[firstKey] /
            previousOtherTotal) *
            remaining,
        );
      }

      const secondValue =
        remaining - firstValue;

      return {
        ...previous,
        [changedKey]: clampedValue,
        [firstKey]: firstValue,
        [secondKey]: secondValue,
      };
    });
  }

  const parsedBudget = Number(budget);

  const formValid =
    product.trim().length > 0 &&
    budget.length > 0 &&
    Number.isFinite(parsedBudget) &&
    parsedBudget > 0;
    const offerEvents = receivedEvents.filter(
      (
        event,
      ): event is OfferCreatedEvent =>
        event.event_type === "OFFER_CREATED",
    );
    
    const sellerNames = [
      "SELLER A",
      "SELLER B",
      "SELLER C",
    ] as const;
    
    const currentRound = receivedEvents.reduce(
      (latest, event) =>
        Math.max(
          latest,
          event.round_number ?? 0,
        ),
      0,
    );
    
    const sellerHistories = sellerNames.map(
      (sellerName) => ({
        sellerName,
    
        offers: offerEvents.filter(
          (offer) =>
            offer.seller_name === sellerName,
        ),
      }),
    );
    async function handleCreateNegotiation() {
      if (!formValid || isCreating) {
        return;
      }
    
      setIsCreating(true);
      setCreateError(null);
      setStartError(null);
      setNegotiationId(null);
      setNegotiationStatus("CREATED");
      setSocketStatus("DISCONNECTED");
      setReceivedEvents([]);
    
      try {
        const result = await createNegotiation({
          product: product.trim(),
          budget: parsedBudget,
          max_delivery_days: maxDeliveryDays,
    
          price_weight: weights.price / 100,
          delivery_weight: weights.delivery / 100,
          warranty_weight: weights.warranty / 100,
    
          randomize_sellers: false,
          seed: null,
        });
    
        setSocketStatus("CONNECTING");
        setNegotiationId(result.negotiation_id);
      } catch (error) {
        if (error instanceof Error) {
          setCreateError(error.message);
        } else {
          setCreateError(
            "Something went wrong while creating the negotiation.",
          );
        }
      } finally {
        setIsCreating(false);
      }
    }

  return (
    <main className="min-h-screen bg-neutral-950 text-white">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <header className="mb-16 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              UNDERBID
            </h1>

            <p className="mt-1 text-sm text-neutral-500">
              Sellers compete. You choose.
            </p>
          </div>

          <div className="rounded-full border border-neutral-800 px-4 py-2 text-xs text-neutral-400">
            REVERSE MARKETPLACE
          </div>
        </header>

        <section className="grid gap-16 lg:grid-cols-[1fr_0.8fr]">
          <div>
            <p className="mb-4 text-sm font-medium uppercase tracking-[0.25em] text-neutral-500">
              New negotiation
            </p>

            <h2 className="max-w-2xl text-5xl font-medium leading-tight tracking-tight">
              Tell us the deal you want.
            </h2>

            <p className="mt-6 max-w-xl text-lg leading-8 text-neutral-400">
              Three sellers independently compete on
              price, delivery and warranty while
              respecting their private economic limits.
            </p>

            <div className="mt-12 rounded-2xl border border-neutral-900 bg-neutral-950 p-5">
              <p className="mb-4 text-xs uppercase tracking-[0.2em] text-neutral-600">
                Current buyer request
              </p>

              <div className="space-y-2 text-sm">
                <PreviewRow
                  label="Product"
                  value={
                    product.trim() ||
                    "Not selected"
                  }
                />

                <PreviewRow
                  label="Hard budget"
                  value={
                    budget
                      ? `₹${Number(
                          budget,
                        ).toLocaleString("en-IN")}`
                      : "Not selected"
                  }
                />

                <PreviewRow
                  label="Delivery limit"
                  value={`${maxDeliveryDays} days`}
                />
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-neutral-800 bg-neutral-900/60 p-7">
            <div className="space-y-6">
              <div>
                <label className="mb-2 block text-sm text-neutral-400">
                  Product
                </label>

                <input
                  type="text"
                  value={product}
                  onChange={(event) =>
                    setProduct(event.target.value)
                  }
                  placeholder="Sony WH-1000XM5"
                  className="w-full rounded-xl border border-neutral-700 bg-neutral-950 px-4 py-3 outline-none transition focus:border-neutral-500"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm text-neutral-400">
                  Hard budget
                </label>

                <div className="flex items-center rounded-xl border border-neutral-700 bg-neutral-950 px-4 focus-within:border-neutral-500">
                  <span className="text-neutral-500">
                    ₹
                  </span>

                  <input
                    type="number"
                    min="1"
                    value={budget}
                    onChange={(event) =>
                      setBudget(event.target.value)
                    }
                    placeholder="24000"
                    className="w-full bg-transparent px-2 py-3 outline-none"
                  />
                </div>

                <p className="mt-2 text-xs text-neutral-600">
                  UNDERBID will never accept a deal
                  above this amount.
                </p>
              </div>

              <div>
                <label className="mb-2 block text-sm text-neutral-400">
                  Maximum delivery time
                </label>

                <select
                  value={maxDeliveryDays}
                  onChange={(event) =>
                    setMaxDeliveryDays(
                      Number(event.target.value),
                    )
                  }
                  className="w-full rounded-xl border border-neutral-700 bg-neutral-950 px-4 py-3 outline-none"
                >
                  <option value={1}>1 day</option>
                  <option value={2}>2 days</option>
                  <option value={3}>3 days</option>
                  <option value={4}>4 days</option>
                  <option value={5}>5 days</option>
                  <option value={7}>7 days</option>
                </select>
              </div>

              <div className="border-t border-neutral-800 pt-6">
                <div className="mb-5 flex items-center justify-between">
                  <div>
                    <p className="text-sm text-neutral-300">
                      Buyer priorities
                    </p>

                    <p className="mt-1 text-xs text-neutral-600">
                      Moving one priority automatically
                      balances the others.
                    </p>
                  </div>

                  <span className="rounded-full border border-neutral-800 px-3 py-1 font-mono text-xs text-neutral-500">
                    TOTAL{" "}
                    {weights.price +
                      weights.delivery +
                      weights.warranty}
                    %
                  </span>
                </div>

                <div className="space-y-6">
                  <PreferenceControl
                    label="Price"
                    value={weights.price}
                    onChange={(value) =>
                      updateWeight("price", value)
                    }
                  />

                  <PreferenceControl
                    label="Delivery"
                    value={weights.delivery}
                    onChange={(value) =>
                      updateWeight(
                        "delivery",
                        value,
                      )
                    }
                  />

                  <PreferenceControl
                    label="Warranty"
                    value={weights.warranty}
                    onChange={(value) =>
                      updateWeight(
                        "warranty",
                        value,
                      )
                    }
                  />
                </div>
              </div>

              <button
  type="button"
  disabled={!formValid || isCreating}
  onClick={handleCreateNegotiation}
  className="mt-3 w-full rounded-xl bg-white px-4 py-4 font-medium text-black transition enabled:hover:bg-neutral-200 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500"
>
  {isCreating
    ? "Creating market..."
    : "Start negotiation"}
</button>

{negotiationId !== null && (
  <div className="space-y-2 rounded-xl border border-neutral-800 bg-neutral-950 px-4 py-4">
    <div className="flex items-center justify-between">
      <span className="text-sm text-neutral-300">
        Market #{negotiationId}
      </span>

      <span className="font-mono text-xs text-neutral-600">
  {negotiationStatus}
</span>
    </div>

    <div className="flex items-center gap-2">
      <span
        className={`h-2 w-2 rounded-full ${
          socketStatus === "CONNECTED"
            ? "bg-emerald-400"
            : socketStatus === "CONNECTING"
              ? "bg-yellow-400"
              : socketStatus === "ERROR"
                ? "bg-red-400"
                : "bg-neutral-600"
        }`}
      />

      <span className="text-xs text-neutral-500">
        {socketStatus === "CONNECTED" &&
          "Live connection established"}

        {socketStatus === "CONNECTING" &&
          "Connecting to negotiation stream..."}

        {socketStatus === "DISCONNECTED" &&
          "Live connection disconnected"}

        {socketStatus === "ERROR" &&
          "Live connection failed"}
      </span>
    </div>
  </div>
)}
{createError && (
  <div className="rounded-xl border border-red-900/50 bg-red-950/20 px-4 py-3 text-sm text-red-400">
    {createError}
  </div>
)}
{startError && (
  <div className="rounded-xl border border-red-900/50 bg-red-950/20 px-4 py-3 text-sm text-red-400">
    {startError}
  </div>
)}

              {!formValid && (
                <p className="text-center text-xs text-neutral-600">
                  Enter a product and valid budget to
                  continue.
                </p>
              )}
            </div>
          </div>
        </section>
        {negotiationId !== null && (
  <section className="mt-20">
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="text-xs uppercase tracking-[0.25em] text-neutral-600">
          Live negotiation
        </p>

        <h2 className="mt-2 text-3xl font-medium tracking-tight">
          Seller arena
        </h2>
      </div>

      <div className="flex items-center gap-3">
        <div className="rounded-full border border-neutral-800 px-4 py-2 font-mono text-xs text-neutral-400">
          ROUND {currentRound || "—"} / 5
        </div>

        <div className="flex items-center gap-2 rounded-full border border-neutral-800 px-4 py-2">
          <span
            className={`h-2 w-2 rounded-full ${
              negotiationStatus === "RUNNING"
                ? "bg-emerald-400"
                : negotiationStatus === "DEAL_FOUND"
                  ? "bg-emerald-400"
                  : negotiationStatus === "NO_DEAL"
                    ? "bg-red-400"
                    : "bg-neutral-600"
            }`}
          />

          <span className="font-mono text-xs text-neutral-400">
            {negotiationStatus}
          </span>
        </div>
      </div>
    </div>

    <div className="grid gap-4 lg:grid-cols-3">
      {sellerHistories.map(
        ({ sellerName, offers }) => (
          <SellerCard
            key={sellerName}
            sellerName={sellerName}
            offers={offers}
          />
        ),
      )}
    </div>
  </section>
)}
        {negotiationId !== null && (
  <section className="mt-16 border-t border-neutral-900 pt-10">
    <div className="mb-6 flex items-end justify-between">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-neutral-600">
          Negotiation telemetry
        </p>

        <h2 className="mt-2 text-2xl font-medium">
          Live event stream
        </h2>
      </div>

      <span className="font-mono text-xs text-neutral-500">
        {receivedEvents.length} EVENTS
      </span>
    </div>

    {receivedEvents.length === 0 ? (
      <div className="rounded-2xl border border-neutral-900 bg-neutral-950 p-6 text-sm text-neutral-600">
        Waiting for negotiation events...
      </div>
    ) : (
      <div className="space-y-3">
        {receivedEvents.map(
          (event, index) => (
            <div
              key={index}
              className="rounded-2xl border border-neutral-900 bg-neutral-950 p-5"
            >
              <div className="mb-3 flex items-center justify-between">
                <span className="font-mono text-sm text-neutral-300">
                  {event.event_type}
                </span>

                <span className="font-mono text-xs text-neutral-700">
                  #{index + 1}
                </span>
              </div>

              <pre className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-xs leading-6 text-neutral-500">
                {JSON.stringify(
                  event,
                  null,
                  2,
                )}
              </pre>
            </div>
          ),
        )}
      </div>
    )}
  </section>
)}
        <section className="mt-24 grid gap-5 border-t border-neutral-900 pt-8 md:grid-cols-3">
          <InfoBlock
            number="01"
            title="Private economics"
            text="Each seller has its own hidden floor, cost and concession strategy."
          />

          <InfoBlock
            number="02"
            title="Hard constraints"
            text="Offers outside your budget or delivery limit are automatically rejected."
          />

          <InfoBlock
            number="03"
            title="Utility driven"
            text="Valid offers compete across price, delivery and warranty — not price alone."
          />
        </section>
      </div>
    </main>
  );
}
function SellerCard({
  sellerName,
  offers,
}: {
  sellerName: string;
  offers: OfferCreatedEvent[];
}) {
  const latestOffer =
    offers.length > 0
      ? offers[offers.length - 1]
      : null;

  const isAccepted =
    latestOffer?.status === "ACCEPTED";

  return (
    <div
      className={`rounded-3xl border p-6 transition ${
        isAccepted
          ? "border-emerald-800 bg-emerald-950/10"
          : "border-neutral-800 bg-neutral-900/40"
      }`}
    >
      <div className="mb-8 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-neutral-600">
            Competing seller
          </p>

          <h3 className="mt-2 text-xl font-medium">
            {sellerName}
          </h3>
        </div>

        <span
          className={`rounded-full px-3 py-1 font-mono text-xs ${
            isAccepted
              ? "bg-emerald-950 text-emerald-400"
              : latestOffer
                ? "bg-neutral-800 text-neutral-400"
                : "bg-neutral-900 text-neutral-600"
          }`}
        >
          {latestOffer?.status ?? "WAITING"}
        </span>
      </div>

      {latestOffer ? (
        <>
          <div className="mb-8">
            <p className="text-sm text-neutral-600">
              Current offer
            </p>

            <p className="mt-2 text-4xl font-medium tracking-tight">
              {formatCurrency(
                latestOffer.price,
              )}
            </p>

            <p className="mt-2 font-mono text-xs text-neutral-600">
              ROUND{" "}
              {latestOffer.round_number}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Metric
              label="Delivery"
              value={`${latestOffer.delivery_days} days`}
            />

            <Metric
              label="Warranty"
              value={`${latestOffer.warranty_months} mo`}
            />
          </div>

          <div className="mt-6 border-t border-neutral-800 pt-5">
            <p className="mb-3 text-xs uppercase tracking-[0.15em] text-neutral-600">
              Offer history
            </p>

            <div className="space-y-2">
              {offers.map((offer) => (
                <div
                  key={`${sellerName}-${offer.round_number}`}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="font-mono text-xs text-neutral-600">
                    R{offer.round_number}
                  </span>

                  <span className="font-mono text-neutral-400">
                    {formatCurrency(
                      offer.price,
                    )}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6 border-t border-neutral-800 pt-5">
            <p className="mb-3 text-xs uppercase tracking-[0.15em] text-neutral-600">
              Add-ons
            </p>

            {latestOffer.addons.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {latestOffer.addons.map(
                  (addon) => (
                    <span
                      key={addon}
                      className="rounded-full border border-neutral-800 px-3 py-1 text-xs text-neutral-400"
                    >
                      {formatAddon(addon)}
                    </span>
                  ),
                )}
              </div>
            ) : (
              <p className="text-sm text-neutral-700">
                No add-ons
              </p>
            )}
          </div>

          {latestOffer.utility_score !==
            null && (
            <div className="mt-6 border-t border-neutral-800 pt-5">
              <div className="flex items-center justify-between">
                <span className="text-xs uppercase tracking-[0.15em] text-neutral-600">
                  Buyer utility
                </span>

                <span className="font-mono text-sm text-neutral-300">
                  {(
                    latestOffer.utility_score *
                    100
                  ).toFixed(1)}
                </span>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="flex h-56 items-center justify-center rounded-2xl border border-dashed border-neutral-800">
          <p className="font-mono text-xs text-neutral-700">
            WAITING FOR OFFER
          </p>
        </div>
      )}
    </div>
  );
}
function Metric({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-950 p-4">
      <p className="text-xs text-neutral-600">
        {label}
      </p>

      <p className="mt-1 text-sm text-neutral-300">
        {value}
      </p>
    </div>
  );
}

function formatCurrency(
  value: string,
) {
  const amount = Number(value);

  return new Intl.NumberFormat(
    "en-IN",
    {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    },
  ).format(amount);
}

function formatAddon(addon: string) {
  return addon
    .split("_")
    .map(
      (word) =>
        word.charAt(0).toUpperCase() +
        word.slice(1),
    )
    .join(" ");
}
function PreferenceControl({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <label className="text-sm">
          {label}
        </label>

        <span className="font-mono text-sm text-neutral-400">
          {value}%
        </span>
      </div>

      <input
        type="range"
        min="0"
        max="100"
        step="1"
        value={value}
        onChange={(event) =>
          onChange(Number(event.target.value))
        }
        className="w-full cursor-pointer accent-white"
      />
    </div>
  );
}

function PreviewRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="flex justify-between gap-8">
      <span className="text-neutral-600">
        {label}
      </span>

      <span className="max-w-[60%] truncate text-right text-neutral-300">
        {value}
      </span>
    </div>
  );
}

function InfoBlock({
  number,
  title,
  text,
}: {
  number: string;
  title: string;
  text: string;
}) {
  return (
    <div className="pr-8">
      <p className="mb-5 font-mono text-xs text-neutral-600">
        {number}
      </p>

      <h3 className="mb-2 font-medium">
        {title}
      </h3>

      <p className="text-sm leading-6 text-neutral-500">
        {text}
      </p>
    </div>
  );
}