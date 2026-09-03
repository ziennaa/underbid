"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type ChartPoint = {
  round: number;
  sellerA: number | null;
  sellerB: number | null;
  sellerC: number | null;
};

export default function PriceConvergenceChart({
  data,
  budget,
}: {
  data: ChartPoint[];
  budget: number;
}) {
  return (
    <div className="rounded-3xl border border-neutral-800 bg-neutral-900/40 p-6">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-neutral-600">
            Market movement
          </p>

          <h3 className="mt-2 text-xl font-medium">
            Price convergence
          </h3>

          <p className="mt-2 text-sm text-neutral-600">
          Seller offers moving toward your hard budget.
          </p>
        </div>

        <div className="rounded-full border border-neutral-800 px-4 py-2">
          <span className="mr-2 text-xs text-neutral-600">
            YOUR LIMIT
          </span>

          <span className="font-mono text-xs text-neutral-300">
            {formatCurrency(budget)}
          </span>
        </div>
      </div>

      {data.length === 0 ? (
        <div className="flex h-80 items-center justify-center rounded-2xl border border-dashed border-neutral-800">
          <p className="font-mono text-xs text-neutral-700">
            WAITING FOR MARKET DATA
          </p>
        </div>
      ) : (
        <>
          <div className="h-80 w-full">
            <ResponsiveContainer
              width="100%"
              height="100%"
            >
              <LineChart
                data={data}
                margin={{
                  top: 10,
                  right: 20,
                  bottom: 10,
                  left: 5,
                }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#262626"
                  vertical={false}
                />

                <XAxis
                  dataKey="round"
                  tickFormatter={(round) =>
                    `R${round}`
                  }
                  stroke="#525252"
                  tick={{
                    fill: "#737373",
                    fontSize: 12,
                  }}
                  tickLine={false}
                  axisLine={false}
                />

                <YAxis
                  width={70}
                  stroke="#525252"
                  tickFormatter={(value) =>
                    `₹${Math.round(
                      value / 1000,
                    )}k`
                  }
                  tick={{
                    fill: "#737373",
                    fontSize: 12,
                  }}
                  tickLine={false}
                  axisLine={false}
                  domain={["auto", "auto"]}
                />

                <Tooltip
                  content={<MarketTooltip />}
                />

                <ReferenceLine
                  y={budget}
                  stroke="#a3a3a3"
                  strokeDasharray="6 6"
                  label={{
                    value: "BUYER LIMIT",
                    fill: "#737373",
                    fontSize: 10,
                    position: "insideTopRight",
                  }}
                />

                <Line
                  type="monotone"
                  dataKey="sellerA"
                  name="SELLER A"
                  stroke="#fafafa"
                  strokeWidth={2}
                  dot={{
                    r: 4,
                    fill: "#fafafa",
                  }}
                  activeDot={{ r: 6 }}
                  connectNulls
                  isAnimationActive
                />

                <Line
                  type="monotone"
                  dataKey="sellerB"
                  name="SELLER B"
                  stroke="#a3a3a3"
                  strokeWidth={2}
                  dot={{
                    r: 4,
                    fill: "#a3a3a3",
                  }}
                  activeDot={{ r: 6 }}
                  connectNulls
                  isAnimationActive
                />

                <Line
                  type="monotone"
                  dataKey="sellerC"
                  name="SELLER C"
                  stroke="#525252"
                  strokeWidth={2}
                  dot={{
                    r: 4,
                    fill: "#525252",
                  }}
                  activeDot={{ r: 6 }}
                  connectNulls
                  isAnimationActive
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-5 flex flex-wrap gap-5 border-t border-neutral-800 pt-5">
            <LegendItem
              label="SELLER A"
              tone="bg-white"
            />

            <LegendItem
              label="SELLER B"
              tone="bg-neutral-400"
            />

            <LegendItem
              label="SELLER C"
              tone="bg-neutral-600"
            />

            <LegendItem
              label="BUYER LIMIT"
              tone="border border-neutral-500"
            />
          </div>
        </>
      )}
    </div>
  );
}

function MarketTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{
    name?: string;
    value?: number | null;
  }>;
  label?: number;
}) {
  if (!active || !payload) {
    return null;
  }

  return (
    <div className="rounded-xl border border-neutral-700 bg-neutral-950 px-4 py-3 shadow-xl">
      <p className="mb-3 font-mono text-xs text-neutral-500">
        ROUND {label}
      </p>

      <div className="space-y-2">
        {payload.map((entry) => (
          <div
            key={entry.name}
            className="flex min-w-40 items-center justify-between gap-6 text-xs"
          >
            <span className="text-neutral-500">
              {entry.name}
            </span>

            <span className="font-mono text-neutral-200">
              {typeof entry.value === "number"
                ? formatCurrency(entry.value)
                : "—"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function LegendItem({
  label,
  tone,
}: {
  label: string;
  tone: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={`h-2 w-2 rounded-full ${tone}`}
      />

      <span className="font-mono text-xs text-neutral-600">
        {label}
      </span>
    </div>
  );
}

function formatCurrency(
  value: number,
) {
  return new Intl.NumberFormat(
    "en-IN",
    {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    },
  ).format(value);
}