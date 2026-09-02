export default function Home() {
  return (
    <main className="min-h-screen bg-neutral-950 text-white">
      <div className="mx-auto max-w-6xl px-6 py-10">
        {/* Header */}
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

        {/* Main content */}
        <section className="grid gap-16 lg:grid-cols-[1fr_0.8fr]">
          {/* Left */}
          <div>
            <p className="mb-4 text-sm font-medium uppercase tracking-[0.25em] text-neutral-500">
              New negotiation
            </p>

            <h2 className="max-w-2xl text-5xl font-medium leading-tight tracking-tight">
              Tell us the deal you want.
            </h2>

            <p className="mt-6 max-w-xl text-lg leading-8 text-neutral-400">
              Three sellers will independently compete on price,
              delivery and warranty while respecting their private
              economic limits.
            </p>
          </div>

          {/* Form card */}
          <div className="rounded-3xl border border-neutral-800 bg-neutral-900/60 p-7">
            <div className="space-y-6">
              {/* Product */}
              <div>
                <label className="mb-2 block text-sm text-neutral-400">
                  Product
                </label>

                <input
                  type="text"
                  placeholder="Sony WH-1000XM5"
                  className="w-full rounded-xl border border-neutral-700 bg-neutral-950 px-4 py-3 outline-none transition focus:border-neutral-500"
                />
              </div>

              {/* Budget */}
              <div>
                <label className="mb-2 block text-sm text-neutral-400">
                  Hard budget
                </label>

                <div className="flex items-center rounded-xl border border-neutral-700 bg-neutral-950 px-4 focus-within:border-neutral-500">
                  <span className="text-neutral-500">₹</span>

                  <input
                    type="number"
                    placeholder="24000"
                    className="w-full bg-transparent px-2 py-3 outline-none"
                  />
                </div>

                <p className="mt-2 text-xs text-neutral-600">
                  UNDERBID will never accept a deal above this amount.
                </p>
              </div>

              {/* Delivery */}
              <div>
                <label className="mb-2 block text-sm text-neutral-400">
                  Maximum delivery time
                </label>

                <select
                  defaultValue="4"
                  className="w-full rounded-xl border border-neutral-700 bg-neutral-950 px-4 py-3 outline-none"
                >
                  <option value="1">1 day</option>
                  <option value="2">2 days</option>
                  <option value="3">3 days</option>
                  <option value="4">4 days</option>
                  <option value="5">5 days</option>
                  <option value="7">7 days</option>
                </select>
              </div>

              {/* Preference preview */}
              <div>
                <div className="mb-4 flex items-center justify-between">
                  <span className="text-sm text-neutral-400">
                    Buyer priorities
                  </span>

                  <span className="text-xs text-neutral-600">
                    TOTAL 100%
                  </span>
                </div>

                <div className="space-y-4">
                  <PreferenceRow
                    label="Price"
                    value="60%"
                    width="60%"
                  />

                  <PreferenceRow
                    label="Delivery"
                    value="25%"
                    width="25%"
                  />

                  <PreferenceRow
                    label="Warranty"
                    value="15%"
                    width="15%"
                  />
                </div>
              </div>

              <button
                type="button"
                className="mt-3 w-full rounded-xl bg-white px-4 py-4 font-medium text-black transition hover:bg-neutral-200"
              >
                Start negotiation
              </button>
            </div>
          </div>
        </section>

        {/* Bottom explanation */}
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

function PreferenceRow({
  label,
  value,
  width,
}: {
  label: string;
  value: string;
  width: string;
}) {
  return (
    <div>
      <div className="mb-2 flex justify-between text-sm">
        <span>{label}</span>
        <span className="text-neutral-500">{value}</span>
      </div>

      <div className="h-1.5 overflow-hidden rounded-full bg-neutral-800">
        <div
          className="h-full rounded-full bg-white"
          style={{ width }}
        />
      </div>
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